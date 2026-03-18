"""Analysis Chain - Multi-step analysis workflow.

This chain demonstrates a pattern for analytical tasks:
1) Context gathering and initial analysis
2) Deep dive investigation 
3) Synthesis and recommendations

The chain shows how to structure multi-agent workflows with proper
context passing and error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    Priority,
    SandboxMode,
)

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AnalysisChainConfig:
    chain_id: str = "analysis_task"
    max_context_chars: int = 8_000
    enable_deep_analysis: bool = True
    confidence_threshold: float = 0.7


class AnalysisChain:
    """Multi-step analysis workflow chain."""

    def __init__(self, config: AnalysisChainConfig | None = None) -> None:
        self.config = config or AnalysisChainConfig()
        self.settings = get_settings()

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the analysis chain and return results."""

        message: str = context.get("message") or ""
        if not message.strip():
            return {"response": "", "error": "AnalysisChain requires non-empty `message`."}

        session_id: str = str(context.get("session_id") or "")
        provider: str = context.get("provider") or self.settings.default_provider
        model: str = context.get("model") or self.settings.default_model

        # Step 1: Initial Context Analysis
        _logger.info("analysis_chain_step1_started", session_id=session_id)
        context_result = await self._run_context_analysis(
            message=message,
            provider=provider,
            model=model,
            session_id=session_id,
        )

        if context_result.get("error"):
            return context_result

        context_summary = context_result.get("full_output", "")

        # Step 2: Deep Investigation (if enabled)
        investigation_summary = ""
        if self.config.enable_deep_analysis:
            _logger.info("analysis_chain_step2_started", session_id=session_id)
            investigation_result = await self._run_deep_investigation(
                message=message,
                context_summary=context_summary,
                provider=provider,
                model=model,
                session_id=session_id,
            )

            if investigation_result.get("error"):
                # Continue with context analysis if investigation fails
                _logger.warning("analysis_chain_step2_failed", error=investigation_result.get("error"))
            else:
                investigation_summary = investigation_result.get("full_output", "")

        # Step 3: Synthesis and Recommendations
        _logger.info("analysis_chain_step3_started", session_id=session_id)
        synthesis_result = await self._run_synthesis(
            message=message,
            context_summary=context_summary,
            investigation_summary=investigation_summary,
            provider=provider,
            model=model,
            session_id=session_id,
        )

        if synthesis_result.get("error"):
            return synthesis_result

        synthesis_output = synthesis_result.get("full_output", "")

        # Compile final response
        final_response = self._compile_final_response(
            context_summary=context_summary,
            investigation_summary=investigation_summary,
            synthesis_output=synthesis_output,
        )

        return {
            "response": final_response,
            "error": None,
            "chain": {
                "context_analysis": context_result,
                "deep_investigation": investigation_result if self.config.enable_deep_analysis else None,
                "synthesis": synthesis_result,
            },
        }

    async def _run_context_analysis(
        self,
        *,
        message: str,
        provider: str,
        model: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Run initial context analysis step."""
        
        objective = (
            "Analise o contexto e identifique os elementos chave da solicitação. "
            "Extraia informações relevantes, identifique stakeholders, recursos necessários, "
            "e possíveis dependências. Forneça um resumo estruturado que servirá de base "
            "para análises mais profundas."
        )

        return await self._execute_agent_step(
            agent_type=AgentType.ANALYST,
            message=message,
            objective=objective,
            provider=provider,
            model=model,
            session_id=session_id,
            priority=Priority.HIGH,
            step_name="context_analysis",
        )

    async def _run_deep_investigation(
        self,
        *,
        message: str,
        context_summary: str,
        provider: str,
        model: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Run deep investigation step."""
        
        # Limit context to prevent token overflow
        limited_context = context_summary[: self.config.max_context_chars]
        
        objective = (
            "Com base no contexto inicial, realize uma investigação aprofundada. "
            "Pesque informações adicionais, explore alternativas, identifique riscos "
            "e oportunidades. Use ferramentas disponíveis para gather dados relevantes "
            "e fornecer insights detalhados."
        )

        return await self._execute_agent_step(
            agent_type=AgentType.RESEARCHER,
            message=message,
            objective=objective,
            provider=provider,
            model=model,
            session_id=session_id,
            priority=Priority.HIGH,
            step_name="deep_investigation",
            context_from_previous=limited_context,
        )

    async def _run_synthesis(
        self,
        *,
        message: str,
        context_summary: str,
        investigation_summary: str,
        provider: str,
        model: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Run synthesis and recommendations step."""
        
        # Combine and limit context
        combined_context = f"Context Analysis:\n{context_summary}\n\n"
        if investigation_summary:
            combined_context += f"Deep Investigation:\n{investigation_summary}\n\n"
        
        limited_context = combined_context[: self.config.max_context_chars]
        
        objective = (
            "Sintetize todas as análises anteriores e forneca recomendações acionáveis. "
            "Estruture sua resposta em: (1) Resumo executivo, (2) Principais findings, "
            "(3) Recomendações priorizadas, (4) Próximos passos. Seja objetivo e focado "
            "em valor prático."
        )

        return await self._execute_agent_step(
            agent_type=AgentType.ANALYST,
            message=message,
            objective=objective,
            provider=provider,
            model=model,
            session_id=session_id,
            priority=Priority.NORMAL,
            step_name="synthesis",
            context_from_previous=limited_context,
        )

    async def _execute_agent_step(
        self,
        *,
        agent_type: AgentType,
        message: str,
        objective: str,
        provider: str,
        model: str,
        session_id: str,
        priority: Priority,
        step_name: str,
        context_from_previous: str = "",
    ) -> dict[str, Any]:
        """Execute a single agent step with proper error handling."""
        
        try:
            agent = get_agent(agent_type)
        except Exception as exc:
            error_msg = f"Agent not registered: {agent_type.value} ({exc})"
            _logger.error("analysis_chain_agent_error", step=step_name, error=error_msg)
            return {"response": "", "error": error_msg}

        # Build message structure
        messages = [{"role": "system", "content": agent.system_prompt}]
        
        if context_from_previous.strip():
            messages.append({
                "role": "system",
                "content": f"Contexto de passos anteriores:\n{context_from_previous}",
            })

        user_content = (
            f"OBJECTIVE: {objective}\n\n"
            f"PRIORITY: {priority.value}\n\n"
            f"SESSION_ID: {session_id or 'unknown'}\n\n"
            f"USER_REQUEST:\n{message}"
        )
        
        messages.append({"role": "user", "content": user_content})

        # Setup sandbox and tools
        sandbox_root = getattr(self.settings, "working_path", None)
        sandbox = MindFlowSandbox(
            root_dir=sandbox_root,
            read_only=(agent.sandbox == SandboxMode.READ_ONLY),
        )
        
        tool_registry = create_default_registry(sandbox)
        tools = [] if agent.sandbox == SandboxMode.NONE else tool_registry.get_tools_for_agent(agent)

        # Execute LLM call
        try:
            llm = get_model_for_provider(provider, model)
            if tools:
                llm = llm.bind_tools(tools)

            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            
            _logger.info("analysis_chain_step_completed", step=step_name, agent=agent_type.value)
            
        except Exception as exc:
            error_msg = f"LLM execution failed: {exc}"
            _logger.error("analysis_chain_step_failed", step=step_name, error=error_msg)
            return {"response": "", "error": error_msg}

        # Return structured result
        return {
            "agent": agent_type.value,
            "step": step_name,
            "status": "completed",
            "full_output": response_text,
            "error": None,
        }

    def _compile_final_response(
        self,
        *,
        context_summary: str,
        investigation_summary: str,
        synthesis_output: str,
    ) -> str:
        """Compile the final response from all steps."""
        
        sections = ["# Análise Completa\n"]
        
        sections.append("## 📋 Análise de Contexto\n")
        sections.append(context_summary)
        
        if investigation_summary:
            sections.append("\n\n## 🔍 Investigação Aprofundada\n")
            sections.append(investigation_summary)
        
        sections.append("\n\n## 📊 Síntese e Recomendações\n")
        sections.append(synthesis_output)
        
        return "\n".join(sections)


# Factory function for catalog registration
def create_analysis_chain(config: AnalysisChainConfig | None = None) -> AnalysisChain:
    """Create an AnalysisChain instance."""
    return AnalysisChain(config)
