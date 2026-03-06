"""Delegation Engine — Handles agent task execution and result collection.

Manages the actual delegation of tasks to agents, tracks execution,
and returns structured results that the Orchestrator can integrate.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, DelegationTask
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

_logger = get_logger(__name__)


class DelegationEngine:
    """Handles execution of delegated tasks to specialized agents."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def delegate_task(
        self,
        task: DelegationTask,
        session: Any,  # OrchestratorSession
    ) -> DelegationResult:
        """Execute a delegated task and return structured results."""
        
        _logger.info(
            "delegation_started",
            agent=task.agent.value,
            task_id=str(task.task_id),
            objective=task.objective,
        )
        
        try:
            # Get the target agent
            agent = get_agent(task.agent)
            
            # Prepare messages for the agent
            messages = [
                {"role": "system", "content": agent.system_prompt}
            ]
            
            # Add context if provided
            if task.context_from_session:
                messages.append(
                    {"role": "system", "content": f"Relevant context from previous delegations:\n{task.context_from_session}"}
                )
            
            # Add the main task
            task_prompt = self._format_task_for_agent(task)
            messages.append({"role": "user", "content": task_prompt})
            
            # Set up sandbox and tools
            sandbox = self._create_sandbox_for_agent(agent)
            tool_registry = create_default_registry(sandbox)
            
            # Get authorized tools (none for sandbox NONE agents)
            if agent.sandbox == SandboxMode.NONE:
                tools = []
            else:
                tools = tool_registry.get_tools_for_agent(agent.agent_type)
            
            # Get LLM instance
            llm = get_model_for_provider(
                self.settings.default_provider,
                task.model or self.settings.default_model
            )
            
            # Bind tools if available
            if tools:
                llm = llm.bind_tools(tools)
            
            # Execute the task
            full_response = []
            tokens_consumed = 0
            
            # Simple streaming implementation without langchain events for now
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Estimate token consumption (rough approximation)
            tokens_consumed = len(response_text.split()) + len(messages) * 10  # Rough estimate
            
            # Create structured result
            result = DelegationResult(
                task_id=task.task_id,
                agent=task.agent,
                status="completed",
                key_findings=self._extract_key_findings(response_text, task.expected_output),
                full_output=response_text,
                files_analyzed=self._extract_files_mentioned(response_text),
                symbols_found=self._extract_symbols_mentioned(response_text),
                confidence=0.8,  # Agent's self-assessed confidence
                tokens_consumed=tokens_consumed,
            )
            
            _logger.info(
                "delegation_completed",
                agent=task.agent.value,
                task_id=str(task.task_id),
                tokens=tokens_consumed,
                confidence=result.confidence,
            )
            
            return result
            
        except Exception as exc:
            _logger.error(
                "delegation_failed",
                agent=task.agent.value,
                task_id=str(task.task_id),
                error=str(exc),
            )
            
            return DelegationResult(
                task_id=task.task_id,
                agent=task.agent,
                status="failed",
                key_findings="",
                full_output="",
                confidence=0.0,
                tokens_consumed=0,
                error_message=str(exc),
            )
    
    def _format_task_for_agent(self, task: DelegationTask) -> str:
        """Format the delegation task for the specific agent."""
        
        task_prompt = f"""You are a {task.agent.value} agent. 

OBJECTIVE: {task.objective}

SCOPE: {', '.join(task.scope) if task.scope else 'Determine appropriate scope based on objective'}

EXCLUSIONS: {', '.join(task.exclusions) if task.exclusions else 'None'}

EXPECTED OUTPUT FORMAT: {task.expected_output or 'Provide a complete solution following your agent\'s best practices'}

PRIORITY: {task.priority.value}

MAX ITERATIONS: {task.max_iterations}

"""
        
        if task.context_from_session:
            task_prompt += f"""
PREVIOUS CONTEXT:
{task.context_from_session}

Use this context to inform your work, but focus on the current objective.
"""
        
        return task_prompt
    
    def _create_sandbox_for_agent(self, agent):
        """Create appropriate sandbox for the agent."""
        sandbox_root = (
            self.settings.working_path 
            if hasattr(self.settings, "working_path") 
            else None
        )
        
        return MindFlowSandbox(
            root_dir=sandbox_root,
            read_only=(agent.sandbox == SandboxMode.READ_ONLY),
        )
    
    def _extract_key_findings(self, response: str, expected_output: str) -> str:
        """Extract key findings from agent response."""
        # For now, return the full response but compressed
        # TODO: Implement smarter extraction based on expected_output
        if len(response) > 1000:
            # Compress long responses
            return response[:500] + "... [truncated for context efficiency]"
        return response
    
    def _extract_files_mentioned(self, response: str) -> list[str]:
        """Extract file paths mentioned in response."""
        import re
        # Simple regex to find file-like patterns
        file_pattern = r'\b[\w\-_\/\.]+\.(py|js|ts|json|yaml|yml|md|txt|sql)\b'
        matches = re.findall(file_pattern, response, re.IGNORECASE)
        return list(set(matches))
    
    def _extract_symbols_mentioned(self, response: str) -> list[str]:
        """Extract function/class/symbol names mentioned in response."""
        import re
        # Simple regex to find code symbols
        symbol_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*\('
        matches = re.findall(symbol_pattern, response)
        return list(set(matches))


# Global delegation engine instance
_delegation_engine: DelegationEngine | None = None


def get_delegation_engine() -> DelegationEngine:
    """Get or create the global delegation engine instance."""
    global _delegation_engine
    if _delegation_engine is None:
        _delegation_engine = DelegationEngine()
    return _delegation_engine
