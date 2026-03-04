"""DT v2 Resolver — executes sub-components through agents.

Implements ResolverProtocol. Maps ComponentOwner → AgentType,
invokes the agent via the registry, and returns an immutable
SubComponentState (no mutation, unlike v1).
"""

from __future__ import annotations

from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from omnimind_backend.agents._registry import get_agent
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    ComponentEvidence,
    ComponentOwner,
    ComponentStatus,
    SubComponentContract,
    SubComponentState,
)
from omnimind_backend.schemas.orchestration.orchestrator import AgentType

_logger = get_logger(__name__)

# Mapping from ComponentOwner → AgentType
_OWNER_TO_AGENT: dict[ComponentOwner, AgentType] = {
    ComponentOwner.CODER: AgentType.CODER,
    ComponentOwner.ANALYST: AgentType.ANALYST,
    ComponentOwner.RESEARCHER: AgentType.RESEARCHER,
    ComponentOwner.ARCH_TECH: AgentType.ARCH_TECH,
    ComponentOwner.CRITIC: AgentType.CRITIC,
}


class ResolverV2:
    """ResolverProtocol implementation for v2 contracts."""

    async def resolve(
        self,
        contract: SubComponentContract,
        prior_results: dict[str, str],
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> SubComponentState:
        """Execute a sub-component and return its runtime state.

        Returns a new SubComponentState (immutable — no side effects).
        """
        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model

        agent_type = _OWNER_TO_AGENT.get(contract.owner_agent, AgentType.CODER)
        agent = get_agent(agent_type)

        # Build context from prior results
        context_parts: list[str] = []
        if prior_results:
            context_parts.append("Context from previous components:")
            for comp_id, result_text in prior_results.items():
                context_parts.append(f"### Component {comp_id}\n{result_text}")

        user_prompt_parts: list[str] = []
        if memory_context.strip():
            user_prompt_parts.append(f"Memory Context (RAG):\n{memory_context}")
        if context_parts:
            user_prompt_parts.append("\n".join(context_parts))
        user_prompt_parts.append(
            f"Current Task: {contract.title}\n"
            f"Scope: {contract.scope}\n"
            f"Expected Artifacts: {', '.join(contract.expected_artifacts) or 'None specified'}"
        )

        user_prompt = "\n\n".join(user_prompt_parts)

        messages = [
            SystemMessage(content=agent.system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            llm = get_model_for_provider(p, m)
            response = await llm.ainvoke(messages)
            result_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            return SubComponentState(
                component_id=contract.component_id,
                state=ComponentStatus.DONE,
                progress=1.0,
                evidence=ComponentEvidence(agent_notes=result_text),
                last_checkpoint_at=datetime.now(UTC),
                iteration_count=1,
            )

        except Exception as e:
            _logger.error(
                "resolver_v2_error",
                component_id=str(contract.component_id),
                error=str(e),
            )
            return SubComponentState(
                component_id=contract.component_id,
                state=ComponentStatus.BLOCKED,
                progress=0.0,
                evidence=ComponentEvidence(agent_notes=f"Error: {e}"),
                last_checkpoint_at=datetime.now(UTC),
                iteration_count=1,
            )
