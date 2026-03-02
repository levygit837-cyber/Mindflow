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

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from omnimind_backend.agents._registry import get_agent
from omnimind_backend.agents.tools import create_default_registry
from omnimind_backend.agents.tools.sandbox import OmniMindSandbox
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.memory.service import MemoryRetrievalResult, get_memory_service
from omnimind_backend.orchestrator.router import route_message
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.orchestrator import OrchestratorDecision
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
    """Analyze the message, produce a routing decision and complexity assessment."""
    from omnimind_backend.orchestrator.complexity import ComplexityScorer
    from omnimind_backend.schemas.orchestrator import ThinkingMode
    settings = get_settings()
    message = state["message"]
    decision = route_message(message)
    
    scorer = ComplexityScorer()
    score = await scorer.get_complexity_score(
        message, 
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

    from omnimind_backend.schemas.orchestrator import ThinkingMode
    
    # 1. Check for Decomposition Thinking Mode
    if decision.thinking_mode == ThinkingMode.DECOMPOSITION and settings.enable_decomposition_thinking:
        try:
            from omnimind_backend.orchestrator.decomposition.decomposer import Decomposer
            from omnimind_backend.orchestrator.decomposition.scheduler import Scheduler
            from omnimind_backend.orchestrator.decomposition.resolver import Resolver
            from omnimind_backend.orchestrator.decomposition.synthesizer import Synthesizer
            
            _logger.info("dt_pipeline_started", session_id=state.get("session_id"))
            
            # Step A: Decompose
            decomposer = Decomposer()
            dt_session = await decomposer.decompose(
                state["message"], 
                session_id=str(state.get("session_id", "unknown")),
                complexity_score=state.get("complexity_score", 1.0),
                provider=provider,
                model=model,
                memory_context=memory_context,
            )
            
            # Step B: Schedule
            scheduler = Scheduler()
            ordered_tasks = scheduler.get_execution_order(dt_session)
            
            # Step C: Resolve
            resolver = Resolver()
            for task in ordered_tasks:
                _logger.info("dt_task_resolving", task=task.title)
                # In DT mode, we also want to emit progress events for each task
                await adispatch_custom_event(
                    "dt_step", 
                    {"task": task.title, "status": "resolving", "session_id": dt_session.session_id}
                )
                await resolver.resolve_task(
                    task,
                    dt_session,
                    provider=provider,
                    model=model,
                    memory_context=memory_context,
                )
                await adispatch_custom_event(
                    "dt_step", 
                    {"task": task.title, "status": "done", "session_id": dt_session.session_id}
                )
                
            # Step D: Synthesize
            synthesizer = Synthesizer()
            final_response = await synthesizer.synthesize(dt_session, provider=provider, model=model)
            
            return {"response": final_response, "dt_session": dt_session, "error": None}
            
        except Exception as exc:
            _logger.error("dt_pipeline_error", error=str(exc))
            return {"response": "", "error": f"Decomposition Thinking failed: {str(exc)}"}

    # 2. Standard Execution Mode
    agent = get_agent(decision.agent)
    messages = [SystemMessage(content=agent.system_prompt)]

    if memory_context.strip():
        messages.append(
            SystemMessage(
                content=(
                    "Memory Context (RAG do histórico do agente):\n"
                    f"{memory_context}"
                )
            )
        )
        try:
            await adispatch_custom_event(
                "agent_memory_context",
                {
                    "agent": decision.agent.value,
                    "references": memory_result.references,
                },
            )
        except RuntimeError:
            # execute_node can be tested/invoked outside LangChain callback context.
            pass

    messages.append(HumanMessage(content=state["message"]))

    try:
        # Initialize registry with a secure sandbox backend
        sandbox = OmniMindSandbox(root_dir=settings.working_path if hasattr(settings, "working_path") else None)
        registry = create_default_registry(sandbox)
        
        # Get authorized tools for this agent
        tools = registry.get_tools_for_agent(agent.agent_type)
        
        llm = get_model_for_provider(provider, model)
        
        # Bind tools if available
        if tools:
            llm = llm.bind_tools(tools)
            
        # Use streaming even if returning a full response at the end
        full_response = []
        async for chunk in llm.astream(messages):
            # Capture content
            content = chunk.content
            
            # Capture thoughts (Gemini)
            thought = ""
            if hasattr(chunk, "response_metadata"):
                metadata = chunk.response_metadata
                if "thought" in metadata:
                    thought = metadata["thought"]
            elif hasattr(chunk, "additional_kwargs"):
                thought = chunk.additional_kwargs.get("thought", "")

            if thought:
                await adispatch_custom_event("agent_thought", {"thought": thought})

            if content:
                if isinstance(content, str):
                    full_response.append(content)
                    await adispatch_custom_event("agent_response", {"chunk": content})
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            txt = item.get("text", "")
                            full_response.append(txt)
                            await adispatch_custom_event("agent_response", {"chunk": txt})
            
            # Capture tool calls
            if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                for tc in chunk.tool_call_chunks:
                    await adispatch_custom_event("agent_tool_call", {"chunk": tc})

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


def respond_node(state: OrchestratorState) -> dict[str, Any]:
    """Finalize the response (no-op in Phase 2 — pass-through)."""
    return state


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_orchestrator_graph() -> Any:
    """Build and compile the orchestrator StateGraph.

    Returns a compiled graph that can be invoked with::

        result = await graph.ainvoke({"message": "...", "provider": "...", "model": "..."})
    """
    graph = StateGraph(OrchestratorState)

    graph.add_node("route", route_node)
    graph.add_node("execute", execute_node)
    graph.add_node("respond", respond_node)

    graph.set_entry_point("route")
    graph.add_edge("route", "execute")
    graph.add_edge("execute", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
