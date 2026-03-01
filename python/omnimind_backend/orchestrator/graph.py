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

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from omnimind_backend.agents._registry import get_agent
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.orchestrator.router import route_message
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.orchestrator import OrchestratorDecision

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


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def route_node(state: OrchestratorState) -> dict[str, Any]:
    """Analyze the message, produce a routing decision and complexity assessment."""
    from omnimind_backend.orchestrator.complexity import ComplexityScorer
    from omnimind_backend.schemas.orchestrator import ThinkingMode
    
    message = state["message"]
    decision = route_message(message)
    
    scorer = ComplexityScorer()
    score = await scorer.get_complexity_score(
        message, 
        provider=state.get("provider"), 
        model=state.get("model")
    )

    if scorer.should_decompose(score):
        decision.thinking_mode = ThinkingMode.DECOMPOSITION
        _logger.info("route_node_triggering_dt", score=score)
    
    _logger.info("route_node_completed", agent=decision.agent.value, score=score)
    return {"decision": decision, "complexity_score": score}


async def execute_node(state: OrchestratorState) -> dict[str, Any]:
    """Invoke the LLM using the selected agent's personality and tools, or run DT pipeline."""
    decision = state["decision"]
    settings = get_settings()
    provider = state.get("provider") or settings.default_provider
    model = decision.model or state.get("model") or settings.default_model

    from omnimind_backend.schemas.orchestrator import ThinkingMode
    
    # 1. Check for Decomposition Thinking Mode
    if decision.thinking_mode == ThinkingMode.DECOMPOSITION:
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
                model=model
            )
            
            # Step B: Schedule
            scheduler = Scheduler()
            ordered_tasks = scheduler.get_execution_order(dt_session)
            
            # Step C: Resolve
            resolver = Resolver()
            for task in ordered_tasks:
                _logger.info("dt_task_resolving", task=task.title)
                await resolver.resolve_task(task, dt_session, provider=provider, model=model)
                
            # Step D: Synthesize
            synthesizer = Synthesizer()
            final_response = await synthesizer.synthesize(dt_session, provider=provider, model=model)
            
            return {"response": final_response, "dt_session": dt_session, "error": None}
            
        except Exception as exc:
            _logger.error("dt_pipeline_error", error=str(exc))
            return {"response": "", "error": f"Decomposition Thinking failed: {str(exc)}"}

    # 2. Standard Execution Mode
    agent = get_agent(decision.agent)
    messages = [
        SystemMessage(content=agent.system_prompt),
        HumanMessage(content=state["message"]),
    ]

    try:
        from omnimind_backend.agents.tools import create_default_registry
        from omnimind_backend.agents.tools.sandbox import OmniMindSandbox
        
        # Initialize registry with a secure sandbox backend
        sandbox = OmniMindSandbox(root_dir=settings.working_path if hasattr(settings, "working_path") else None)
        registry = create_default_registry(sandbox)
        
        # Get authorized tools for this agent
        tools = registry.get_tools_for_agent(agent.agent_type)
        
        llm = get_model_for_provider(provider, model)
        
        # Bind tools if available
        if tools:
            llm_with_tools = llm.bind_tools(tools)
            ai_message = await llm_with_tools.ainvoke(messages)
        else:
            ai_message = await llm.ainvoke(messages)
            
        content = ai_message.content

        # Phase 3: Add tool execution loop if needed (LangGraph tools pattern)
        # For now, we return the direct output (LLM may request tools)
        if isinstance(content, str):
            response_text = content
        elif isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(str(item.get("text", "")))
                elif isinstance(item, dict) and item.get("type") == "tool_use":
                    # Tool use metadata is captured in LangGraph trace
                    chunks.append(f"[Tool Use: {item.get('name')}]")
                else:
                    chunks.append(str(item))
            response_text = "".join(chunks)
        else:
            response_text = str(content)

        if not response_text.strip():
            response_text = "No response generated."

        return {"response": response_text, "error": None}

    except Exception as exc:
        _logger.error("execute_node_error", error=str(exc))
        return {"response": "", "error": str(exc)}


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
