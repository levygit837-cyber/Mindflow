"""Orchestrator graph — LangGraph StateGraph for agent execution.

Defines a compiled graph with three nodes:
1. **route** — analyze user message and select agent personality
2. **execute** — invoke the LLM with the selected agent's prompt
3. **respond** — format the output into stream events

Phase 2 uses a simple linear flow: route → execute → respond.
Multi-agent chaining and conditional branching are Phase 3 scope.
"""

from __future__ import annotations

from typing import Any, TypedDict

from omnimind_backend.agents._registry import get_agent
from omnimind_backend.agents.tools import create_default_registry
from omnimind_backend.agents.tools.sandbox import OmniMindSandbox
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.memory.service import MemoryRetrievalResult, get_memory_service
from omnimind_backend.orchestrator.router import route_message
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.orchestration.orchestrator import OrchestratorDecision, SandboxMode
from omnimind_backend.storage.db import db_session

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class OrchestratorState(TypedDict, total=False):
    """State flowing through the orchestrator graph."""

    message: str
    provider: str
    model: str
    decision: OrchestratorDecision
    response: str
    error: str | None
    complexity_score: float
    dt_session: Any  # DTSession
    session_id: str
    memory_context: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def route_node(state: OrchestratorState) -> dict[str, Any]:
    """Analyze the message using intelligent LLM routing and produce a decision."""
    from omnimind_backend.orchestrator.intelligent_router import route_message_intelligently
    from omnimind_backend.schemas.orchestration.delegation import OrchestratorSession
    
    # Create orchestrator session if not exists
    session = OrchestratorSession(
        user_intent=state["message"],
    )
    
    # Use intelligent routing instead of keyword matching
    decision = await route_message_intelligently(state["message"], session)
    
    # Calculate complexity score (keeping existing logic)
    from omnimind_backend.orchestrator.complexity import ComplexityScorer
    from omnimind_backend.schemas.orchestration.orchestrator import ThinkingMode
    settings = get_settings()
    
    scorer = ComplexityScorer()
    score = await scorer.get_complexity_score(
        state["message"], 
        provider=state.get("provider"), 
        model=state.get("model")
    )

    if settings.enable_decomposition_thinking and scorer.should_decompose(score):
        decision.thinking_mode = ThinkingMode.DECOMPOSITION
        _logger.info("route_node_triggering_dt", score=score)
    elif scorer.should_decompose(score):
        _logger.info("route_node_dt_disabled", score=score)
    
    _logger.info("route_node_completed", agent=decision.agent.value, score=score)
    return {"decision": decision, "complexity_score": score}


async def execute_node(state: OrchestratorState) -> dict[str, Any]:
    """Invoke the LLM using the selected agent's personality and tools, or run DT pipeline."""
    decision = state["decision"]
    settings = get_settings()
    provider = state.get("provider") or settings.default_provider
    model = decision.model or state.get("model") or settings.default_model
    session_id = str(state.get("session_id", ""))
    memory_result = _retrieve_memory_context(
        query=state["message"],
        session_id=session_id,
        agent_id=decision.agent.value,
    )
    memory_context = memory_result.context

    from omnimind_backend.schemas.orchestration.orchestrator import ThinkingMode

    # 1. Check for Decomposition Thinking Mode
    if decision.thinking_mode == ThinkingMode.DECOMPOSITION and settings.enable_decomposition_thinking:
        if settings.enable_dt_v2:
            return await _run_dt_v2(state, provider, model, memory_context)
        return await _run_dt_v1(state, provider, model, memory_context)

    # 2. Standard Execution Mode
    agent = get_agent(decision.agent)
    messages = [{"role": "system", "content": agent.system_prompt}]

    if memory_context.strip():
        messages.append(
            {
                "role": "system", 
                "content": (
                    "Memory Context (RAG from agent history):\n"
                    f"{memory_context}"
                )
            }
        )
    
    messages.append({"role": "user", "content": state["message"]})
    
    try:
        from omnimind_backend.schemas.orchestration.orchestrator import ThinkingMode
    except ImportError:
        ThinkingMode = None
    
    try:
        # Enforce sandbox mode based on agent personality
        sandbox_root = settings.working_path if hasattr(settings, "working_path") else None
        sandbox = OmniMindSandbox(
            root_dir=sandbox_root,
            read_only=(agent.sandbox == SandboxMode.READ_ONLY),
        )
        registry = create_default_registry(sandbox)

        # Get authorized tools for this agent (no tools for NONE sandbox agents)
        if agent.sandbox == SandboxMode.NONE:
            tools = []
        else:
            tools = registry.get_tools_for_agent(agent.agent_type)
        
        llm = get_model_for_provider(provider, model)
        
        # Bind tools if available
        if tools:
            llm = llm.bind_tools(tools)
            
        # Use streaming even if returning a full response at the end
        full_response = []
        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Capture thoughts (Gemini)
        thought = ""
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if "thought" in metadata:
                thought = metadata["thought"]
        elif hasattr(response, "additional_kwargs"):
            thought = response.additional_kwargs.get("thought", "")

        # Note: Skipping custom events for now to avoid langchain_core dependency
        # if thought:
        #     await adispatch_custom_event("agent_thought", {"thought": thought})

        if response_text:
            if isinstance(response_text, str):
                full_response.append(response_text)
                # await adispatch_custom_event("agent_response", {"chunk": response_text})
            elif isinstance(response_text, list):
                for item in response_text:
                    if isinstance(item, dict) and item.get("type") == "text":
                        txt = item.get("text", "")
                        full_response.append(txt)
                        # await adispatch_custom_event("agent_response", {"chunk": txt})
        
        # Note: Skipping tool call events for now
        # # Capture tool calls
        # if hasattr(response, "tool_call_chunks") and response.tool_call_chunks:
        #     for tc in response.tool_call_chunks:
        #         await adispatch_custom_event("agent_tool_call", {"chunk": tc})

        response_text = "".join(full_response)
        if not response_text.strip():
            response_text = "No response generated."

        return {"response": response_text, "error": None}

    except Exception as exc:
        _logger.error("execute_node_error", error=str(exc))
        return {"response": "", "error": str(exc)}


def _retrieve_memory_context(*, query: str, session_id: str, agent_id: str) -> MemoryRetrievalResult:
    settings = get_settings()
    if not settings.memory_enabled:
        return MemoryRetrievalResult(context="", references=[])
    if not session_id:
        return MemoryRetrievalResult(context="", references=[])

    try:
        with db_session() as db:
            return get_memory_service().retrieve_context_for_query(
                db=db,
                session_id=session_id,
                agent_id=agent_id,
                query=query,
            )
    except Exception as exc:
        _logger.warning("memory_retrieval_failed", error=str(exc), session_id=session_id, agent=agent_id)
        return MemoryRetrievalResult(context="", references=[])


async def _run_dt_v1(
    state: OrchestratorState,
    provider: str,
    model: str,
    memory_context: str,
) -> dict[str, Any]:
    """Execute the v1 Decomposition Thinking pipeline."""
    try:
        from omnimind_backend.orchestrator.decomposition.decomposer import Decomposer
        from omnimind_backend.orchestrator.decomposition.resolver import Resolver
        from omnimind_backend.orchestrator.decomposition.scheduler import Scheduler
        from omnimind_backend.orchestrator.decomposition.synthesizer import Synthesizer

        _logger.info("dt_v1_pipeline_started", session_id=state.get("session_id"))

        decomposer = Decomposer()
        dt_session = await decomposer.decompose(
            state["message"],
            session_id=str(state.get("session_id", "unknown")),
            complexity_score=state.get("complexity_score", 1.0),
            provider=provider,
            model=model,
            memory_context=memory_context,
        )

        scheduler = Scheduler()
        ordered_tasks = scheduler.get_execution_order(dt_session)

        resolver = Resolver()
        for task in ordered_tasks:
            _logger.info("dt_v1_task_resolving", task=task.title)
            await resolver.resolve_task(
                task, dt_session, provider=provider, model=model, memory_context=memory_context,
            )

        synthesizer = Synthesizer()
        final_response = await synthesizer.synthesize(dt_session, provider=provider, model=model)

        return {"response": final_response, "dt_session": dt_session, "error": None}

    except Exception as exc:
        _logger.error("dt_v1_pipeline_error", error=str(exc))
        return {"response": "", "error": f"DT v1 failed: {exc}"}


async def _run_dt_v2(
    state: OrchestratorState,
    provider: str,
    model: str,
    memory_context: str,
) -> dict[str, Any]:
    """Execute the v2 Decomposition Thinking pipeline."""
    from uuid import UUID as _UUID

    from omnimind_backend.orchestrator.decomposition.decomposer_v2 import DecomposerV2
    from omnimind_backend.orchestrator.decomposition.resolver_v2 import ResolverV2
    from omnimind_backend.orchestrator.decomposition.scheduler_v2 import SchedulerV2
    from omnimind_backend.orchestrator.decomposition.scorer_adapter import ComponentScorer
    from omnimind_backend.orchestrator.decomposition.synthesizer_v2 import SynthesizerV2
    from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import ValidatedComponent

    try:
        session_id_str = str(state.get("session_id", "unknown"))
        _logger.info("dt_v2_pipeline_started", session_id=session_id_str)

        # Step A: Decompose
        decomposer = DecomposerV2()
        main, components = await decomposer.decompose(
            state["message"],
            session_id=session_id_str,
            complexity_score=state.get("complexity_score", 1.0),
            provider=provider,
            model=model,
            memory_context=memory_context,
        )
        _logger.info("dt_v2_decomposed", goal=main.goal, components=len(components))

        # Step B: Schedule
        scheduler = SchedulerV2()
        ordered = scheduler.get_execution_order(components)

        # Step C: Resolve + Score
        resolver = ResolverV2()
        scorer = ComponentScorer()
        prior_results: dict[str, str] = {}
        validated: list[ValidatedComponent] = []

        for contract in ordered:
            _logger.info("dt_v2_resolving", component=contract.title)
            comp_state = await resolver.resolve(
                contract, prior_results, provider=provider, model=model, memory_context=memory_context,
            )
            score = scorer.score(comp_state, consistency=1.0, agent_confidence=0.8)
            _logger.info("dt_v2_scored", component=contract.title, score=score)

            if scorer.is_validated(score):
                notes = comp_state.evidence.agent_notes if comp_state.evidence else ""
                validated.append(
                    ValidatedComponent(
                        component_id=contract.component_id,
                        title=contract.title,
                        summary=notes,
                        artifacts=contract.expected_artifacts,
                        score=score,
                    )
                )
                prior_results[str(contract.component_id)] = notes

        # Step D: Synthesize
        # Parse session_id as UUID, fall back to main_component_id
        try:
            sid = _UUID(session_id_str)
        except ValueError:
            sid = main.main_component_id

        synthesizer = SynthesizerV2()
        synthesis = await synthesizer.synthesize(
            session_id=sid,
            main_contract=main,
            validated_components=validated,
            provider=provider,
            model=model,
        )

        return {"response": synthesis.final_answer, "dt_session": None, "error": None}

    except Exception as exc:
        _logger.error("dt_v2_pipeline_error", error=str(exc))
        return {"response": "", "error": f"DT v2 failed: {exc}"}


def respond_node(state: OrchestratorState) -> dict[str, Any]:
    """Finalize the response (no-op in Phase 2 — pass-through)."""
    return state


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_simple_orchestrator_flow() -> Any:
    """Build a simple orchestrator flow without langgraph dependency.
    
    Returns a simple function that can be invoked with::
    
        result = await simple_orchestrate({"message": "...", "provider": "...", "model": "..."})
    """
    async def simple_orchestrate(state: dict[str, Any]) -> dict[str, Any]:
        """Simple orchestration without langgraph."""
        # Route the message
        route_result = await route_node(state)
        decision = route_result["decision"]
        
        # Execute the decision (for now, just return the decision)
        # In a full implementation, this would call execute_node
        
        return {
            "decision": decision,
            "response": f"Orchestrator selected {decision.agent.value} to handle: {decision.task}",
        }
    
    return simple_orchestrate
