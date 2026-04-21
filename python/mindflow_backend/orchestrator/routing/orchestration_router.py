"""Canonical orchestration router façade used by the runtime graph."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field

from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.orchestrator.routing.hybrid_router import get_hybrid_router
from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
    Priority,
    WorkspacePolicy,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowRouteDecision


@dataclass(slots=True)
class RoutingContext:
    """Normalized request context for orchestration routing."""

    message: str
    session: OrchestratorSession | None = None
    folder_path: str | None = None
    session_id: str | None = None
    provider: str | None = None
    model: str | None = None
    agent_type: str | None = None
    orchestrate: bool = False
    workspace_policy: WorkspacePolicy = WorkspacePolicy.AUTO
    metadata: dict[str, object] = field(default_factory=dict)


class OrchestrationRouter:
    """Single façade for production routing decisions."""

    def __init__(self) -> None:
        self._hybrid = get_hybrid_router()

    async def route(self, context: RoutingContext) -> WorkflowRouteDecision:
        if context.agent_type:
            return self._route_forced_agent(context)

        session = context.session or OrchestratorSession(user_intent=context.message)
        session_id = context.session_id or str(session.session_id)
        decision = await self._hybrid.route_message(
            message=context.message,
            session=session,
            folder_path=context.folder_path,
        )
        return self._normalize_decision(decision, context=context, session_id=session_id)

    def _route_forced_agent(self, context: RoutingContext) -> WorkflowRouteDecision:
        session_id = context.session_id
        requested_agent_id = str(context.agent_type or "orchestrator").strip().lower()
        with suppress(KeyError):
            policy = get_agent_runtime_policy(agent_id=requested_agent_id, session_id=session_id)
            return WorkflowRouteDecision(
                rationale=f"Routing constrained by requested agent_type={requested_agent_id}.",
                execution_strategy=ExecutionStrategy.DELEGATE,
                agent_role=policy.agent_role,
                agent_id_override=policy.agent_id,
                specialist=policy.specialist,
                task=context.message,
                thinking=policy.thinking_level,
                priority=Priority.HIGH if context.orchestrate else Priority.NORMAL,
                tools=list(policy.tools),
                confidence=1.0,
                metadata={
                    "routing_mode": "forced_agent_type",
                    "requested_agent_id": requested_agent_id,
                    **context.metadata,
                },
            )

        policy = get_agent_runtime_policy(agent_id="orchestrator", session_id=session_id)
        return WorkflowRouteDecision(
            rationale=f"Requested agent_type={requested_agent_id} is unknown; falling back to orchestrator.",
            execution_strategy=ExecutionStrategy.DELEGATE,
            agent_role=policy.agent_role,
            agent_id_override=policy.agent_id,
            specialist=policy.specialist,
            task=context.message,
            thinking=policy.thinking_level,
            priority=Priority.NORMAL,
            tools=list(policy.tools),
            confidence=0.4,
            metadata={
                "routing_mode": "forced_agent_type_fallback",
                "requested_agent_id": requested_agent_id,
                **context.metadata,
            },
        )

    def _normalize_decision(
        self,
        decision: OrchestratorDecision,
        *,
        context: RoutingContext,
        session_id: str | None,
    ) -> WorkflowRouteDecision:
        agent_id = getattr(decision, "agent_id", None) or decision.agent.value
        legacy_strategy = getattr(decision, "execution_strategy", ExecutionStrategy.DELEGATE)

        if legacy_strategy == ExecutionStrategy.DIRECT_RESPONSE:
            orchestrator_policy = get_agent_runtime_policy(agent_id="orchestrator", session_id=session_id)
            return WorkflowRouteDecision(
                rationale=decision.rationale or "Compat: direct response normalized to orchestrator delegation.",
                execution_strategy=ExecutionStrategy.DELEGATE,
                agent_role=orchestrator_policy.agent_role,
                agent_id_override=orchestrator_policy.agent_id,
                specialist=orchestrator_policy.specialist,
                task=decision.task or context.message,
                thinking=orchestrator_policy.thinking_level,
                priority=getattr(decision, "priority", Priority.NORMAL),
                tools=list(orchestrator_policy.tools),
                confidence=getattr(decision, "confidence", 0.5),
                metadata={
                    "legacy_execution_strategy": "direct_response",
                    "routing_mode": "compat_direct_response",
                    **(decision.metadata or {}),
                    **context.metadata,
                },
            )

        policy = get_agent_runtime_policy(agent_id=agent_id, session_id=session_id)
        return WorkflowRouteDecision(
            rationale=decision.rationale,
            execution_strategy=legacy_strategy,
            agent_role=policy.agent_role,
            agent_id_override=policy.agent_id,
            specialist=policy.specialist,
            task=decision.task or context.message,
            thinking=getattr(decision, "thinking", policy.thinking_level),
            priority=getattr(decision, "priority", Priority.NORMAL),
            tools=list(decision.tools or policy.tools),
            confidence=getattr(decision, "confidence", 0.5),
            metadata={
                **(decision.metadata or {}),
                **context.metadata,
            },
        )


_orchestration_router: OrchestrationRouter | None = None


def get_orchestration_router() -> OrchestrationRouter:
    global _orchestration_router
    if _orchestration_router is None:
        _orchestration_router = OrchestrationRouter()
    return _orchestration_router


async def route_message(
    message: str,
    session: OrchestratorSession | None = None,
    folder_path: str | None = None,
) -> WorkflowRouteDecision:
    return await get_orchestration_router().route(
        RoutingContext(
            message=message,
            session=session,
            folder_path=folder_path,
            session_id=str(session.session_id) if session else None,
        )
    )
