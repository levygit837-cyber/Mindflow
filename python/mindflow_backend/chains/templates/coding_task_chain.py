"""Coding Task Chain - Analyst/Deep → Coder → Code Review.

This chain is designed to turn a coding request into a structured workflow:
1) Analyst (optionally with Deep Analysis protocol) gathers code context.
2) Coder performs the implementation.
3) Analyst-as-Critic performs a focused code review.

The chain executes real agent calls (LLM + tools) and returns a final response
that the Orchestrator can stream back to the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.prompts.core.analyst import compose_analyst_prompt
from mindflow_backend.agents.prompts.specialized.deep_analysis import DEEP_ANALYSIS
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
class CodingTaskChainConfig:
    chain_id: str = "coding_task"
    use_deep_analysis: bool = False
    max_context_chars_for_coder: int = 6_000


class CodingTaskChain:
    """Agent-driven coding workflow chain."""

    def __init__(self, config: CodingTaskChainConfig | None = None) -> None:
        self.config = config or CodingTaskChainConfig()
        self.settings = get_settings()

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the chain and return a context dict with `response`."""

        message: str = context.get("message") or ""
        if not message.strip():
            return {"response": "", "error": "CodingTaskChain requires non-empty `message`."}

        session_id: str = str(context.get("session_id") or "")
        provider: str = context.get("provider") or self.settings.default_provider
        model: str = context.get("model") or self.settings.default_model

        # Step 1: Analyst reads and builds structured context
        analyst_prompt = compose_analyst_prompt("core", "read")
        if self.config.use_deep_analysis:
            analyst_prompt = f"{analyst_prompt}\n\n{DEEP_ANALYSIS}"

        analyst_objective = (
            "Leia e analise o codebase para reunir contexto suficiente para implementar a solicitação do usuário. "
            "Você deve identificar os arquivos mais relevantes (incluindo os explicitamente citados pelo usuário, "
            "quando houver), mapear o fluxo/dependências afetadas, e retornar um resumo estruturado para orientar "
            "a implementação. Não cole conteúdo bruto de arquivos; cite caminhos e trechos mínimos quando necessário."
        )

        analyst_result = await self._run_agent(
            agent_type=AgentType.ANALYST,
            system_prompt_override=analyst_prompt,
            user_message=message,
            objective=analyst_objective,
            provider=provider,
            model=model,
            session_id=session_id,
            priority=Priority.HIGH,
            context_from_previous="",
        )

        if analyst_result.get("error"):
            return analyst_result

        analyst_summary: str = analyst_result.get("key_findings", "") or analyst_result.get("full_output", "")

        # Step 2: Coder implements using Analyst summary
        coder_objective = (
            "Implemente as alterações necessárias no codebase para atender a solicitação do usuário. "
            "Use o contexto do Analyst. Quando houver ambiguidades, faça suposições explícitas e mínimas. "
            "Produza uma resposta final com o que foi alterado e como validar."
        )

        coder_context = analyst_summary[: self.config.max_context_chars_for_coder]
        coder_result = await self._run_agent(
            agent_type=AgentType.CODER,
            system_prompt_override=None,
            user_message=message,
            objective=coder_objective,
            provider=provider,
            model=model,
            session_id=session_id,
            priority=Priority.HIGH,
            context_from_previous=coder_context,
        )

        if coder_result.get("error"):
            return coder_result

        coder_output: str = coder_result.get("full_output", "")

        # Step 3: Code review specialist (Analyst as Critic)
        critic_prompt = compose_analyst_prompt("core", "critic")
        review_objective = (
            "Faça code review das alterações propostas/realizadas pelo Coder. "
            "Verifique bugs lógicos, edge cases, segurança, consistência com padrões do projeto e possíveis regressões. "
            "Retorne (1) achados críticos, (2) achados importantes, (3) sugestões opcionais, e (4) um 'LGTM?' final."
        )

        review_context = (
            "Resumo do Analyst (contexto do codebase):\n"
            f"{analyst_summary}\n\n"
            "Saída do Coder (implementação):\n"
            f"{coder_output}"
        )

        review_result = await self._run_agent(
            agent_type=AgentType.ANALYST,
            system_prompt_override=critic_prompt,
            user_message=message,
            objective=review_objective,
            provider=provider,
            model=model,
            session_id=session_id,
            priority=Priority.NORMAL,
            context_from_previous=review_context,
        )

        if review_result.get("error"):
            # Still return coder output if review fails
            return {
                "response": coder_output,
                "error": f"Code review failed: {review_result['error']}",
                "chain": {
                    "analyst": analyst_result,
                    "coder": coder_result,
                    "review": review_result,
                },
            }

        review_output: str = review_result.get("full_output", "")

        final = (
            "## Implementação\n\n"
            f"{coder_output}\n\n"
            "## Code Review\n\n"
            f"{review_output}\n"
        )

        return {
            "response": final,
            "error": None,
            "chain": {
                "analyst": analyst_result,
                "coder": coder_result,
                "review": review_result,
            },
        }

    async def _run_agent(
        self,
        *,
        agent_type: AgentType,
        system_prompt_override: str | None,
        user_message: str,
        objective: str,
        provider: str,
        model: str,
        session_id: str,
        priority: Priority,
        context_from_previous: str,
    ) -> dict[str, Any]:
        """Run an agent with optional system prompt override and return a structured dict."""

        try:
            agent = get_agent(agent_type)
        except Exception as exc:
            return {"response": "", "error": f"Agent not registered: {agent_type.value} ({exc})"}

        system_prompt = system_prompt_override or agent.system_prompt

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if context_from_previous.strip():
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Relevant context from previous chain steps:\n"
                        f"{context_from_previous}"
                    ),
                }
            )

        messages.append(
            {
                "role": "user",
                "content": (
                    f"OBJECTIVE: {objective}\n\n"
                    f"PRIORITY: {priority.value}\n\n"
                    f"SESSION_ID: {session_id or 'unknown'}\n\n"
                    f"USER_REQUEST:\n{user_message}"
                ),
            }
        )

        # Sandbox + tools selection follow the same policy as DelegationEngine.
        sandbox_root = self.settings.working_path if hasattr(self.settings, "working_path") else None
        sandbox = MindFlowSandbox(
            root_dir=sandbox_root,
            read_only=(agent.sandbox == SandboxMode.READ_ONLY),
        )
        tool_registry = create_default_registry(sandbox)
        tools = [] if agent.sandbox == SandboxMode.NONE else tool_registry.get_tools_for_agent(agent.agent_type)

        llm = get_model_for_provider(provider, model)
        if tools:
            llm = llm.bind_tools(tools)

        try:
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            _logger.error("coding_task_chain_agent_failed", agent=agent_type.value, error=str(exc))
            return {"response": "", "error": str(exc)}

        # For now, keep result structure compatible with DelegationResult fields used elsewhere.
        key_findings = response_text[:500] + "... [truncated]" if len(response_text) > 1000 else response_text
        return {
            "agent": agent_type.value,
            "status": "completed",
            "key_findings": key_findings,
            "full_output": response_text,
            "error": None,
        }

