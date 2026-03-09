"""Orchestrator graph — LangGraph StateGraph for agent execution.

Defines a compiled graph with three nodes:
1. **route** — analyze user message and select agent personality
2. **execute** — invoke the LLM with the selected agent's prompt
3. **respond** — format the output into stream events

Phase 2 uses a simple linear flow: route → execute → respond.
Multi-agent chaining and conditional branching are Phase 3 scope.

This module now provides backward compatibility while using the new graph architecture.
"""

from __future__ import annotations

from typing import Any, TypedDict

# New architecture imports
# NOTE: keep imports here lightweight; graph factory functions are imported lazily
# in the compatibility helpers at the bottom of this module.

# Legacy imports for backward compatibility
from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
# Avoid importing memory subsystem at module import time (it can pull DB deps).
from typing import Any as _Any
from mindflow_backend.orchestrator.router import route_message
from mindflow_backend.runtime import get_model_for_provider, extract_ai_message_content
from mindflow_backend.schemas.orchestration.orchestrator import OrchestratorDecision, SandboxMode

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Legacy State (for backward compatibility)
# ---------------------------------------------------------------------------


class OrchestratorState(TypedDict, total=False):
    """State flowing through the orchestrator graph (legacy)."""

    message: str
    provider: str
    model: str
    decision: OrchestratorDecision
    response: str
    error: str | None
    complexity_score: float
    task_session: Any  # TaskSession
    session_id: str
    memory_context: str


# ---------------------------------------------------------------------------
# New Architecture Integration
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def route_node(state: OrchestratorState) -> dict[str, Any]:
    """Analyze the message using intelligent LLM routing and produce a decision."""
    from mindflow_backend.orchestrator.intelligent_router import route_message_intelligently
    from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession
    
    # Create orchestrator session if not exists
    session = OrchestratorSession(
        user_intent=state["message"],
    )
    
    # Use intelligent routing instead of keyword matching
    decision = await route_message_intelligently(state["message"], session)
    
    # Calculate complexity score (keeping existing logic)
    from mindflow_backend.orchestrator.complexity import ComplexityScorer
    from mindflow_backend.schemas.orchestration.orchestrator import ThinkingMode
    settings = get_settings()
    
    scorer = ComplexityScorer()
    score = await scorer.get_complexity_score(
        state["message"], 
        provider=state.get("provider"), 
        model=state.get("model")
    )

    if settings.enable_decomposition_thinking and scorer.should_decompose(score):
        decision.thinking_mode = ThinkingMode.DECOMPOSITION
        _logger.info("route_node_triggering_task", score=score)
    elif scorer.should_decompose(score):
        _logger.info("route_node_task_disabled", score=score)
    
    _logger.info("route_node_completed", agent=decision.agent.value, score=score)
    return {"decision": decision, "complexity_score": score}


async def execute_node(state: OrchestratorState) -> dict[str, Any]:
    """Invoke the LLM using the selected agent's personality and tools, or run Task pipeline."""
    decision = state["decision"]
    settings = get_settings()
    provider = state.get("provider") or settings.default_provider
    model = decision.model or state.get("model") or settings.default_model
    session_id = str(state.get("session_id", ""))
    from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy, ThinkingMode

    # 0. Chain Execution Mode (explicit orchestrator strategy)
    if getattr(decision, "execution_strategy", ExecutionStrategy.SINGLE_AGENT) == ExecutionStrategy.CHAIN:
        memory_context = ""
        chain_id = getattr(decision, "chain_id", None) or "coding_task"
        try:
            from mindflow_backend.chains.catalog import get_chain
            chain = get_chain(chain_id)
            chain_result = await chain.execute(
                {
                    "message": state["message"],
                    "session_id": session_id,
                    "provider": provider,
                    "model": model,
                    "memory_context": memory_context,
                    "decision": decision.model_dump() if hasattr(decision, "model_dump") else {},
                }
            )
            return {
                "response": chain_result.get("response", ""),
                "error": chain_result.get("error"),
                "chain_result": chain_result,
            }
        except Exception as exc:
            _logger.error("chain_execution_failed", chain_id=chain_id, error=str(exc))
            return {"response": "", "error": f"Chain execution failed ({chain_id}): {exc}"}

    memory_result = _retrieve_memory_context(
        query=state["message"],
        session_id=session_id,
        agent_id=decision.agent.value,
    )
    if isinstance(memory_result, dict):
        memory_context = memory_result.get("context", "")
    else:
        memory_context = getattr(memory_result, "context", "")

    # 1. Check for Decomposition Thinking Mode
    if decision.thinking_mode == ThinkingMode.DECOMPOSITION and settings.enable_decomposition_thinking:
        return await _run_task_pipeline(state, provider, model, memory_context)

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
        from mindflow_backend.schemas.orchestration.orchestrator import ThinkingMode
    except ImportError:
        ThinkingMode = None
    
    try:
        # Enforce sandbox mode based on agent personality
        sandbox_root = settings.working_path if hasattr(settings, "working_path") else None
        sandbox = MindFlowSandbox(
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
        
        # Extract thinking and text content separately
        content = extract_ai_message_content(response, include_thinking=True)
        response_text = content["text"]
        thinking = content["thinking"]
        
        # Capture thoughts for debugging/analysis
        if thinking:
            _logger.debug("agent_thinking", thinking=thinking[:200])  # Log first 200 chars
            # TODO: Emit thinking as custom event when event system is ready
            # await adispatch_custom_event("agent_thought", {"thought": thinking})

        if response_text:
            # response_text is now a clean string from extract_ai_message_content
            full_response.append(response_text)
            # TODO: Emit response as custom event when event system is ready
            # await adispatch_custom_event("agent_response", {"chunk": response_text})
        
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


async def _orchestrator_reflect(
    *,
    session_id: str,
    next_task_intent: str,
    context_manager: Any,
    limit: int = 3,
) -> str:
    """Retrieve semantically relevant Task/SubTask context for the upcoming resolution.

    Uses the Task/SubTask embedding store and the task registry — never scans the
    full session linearly. Combines two signals:
    1. Task registry summary: structured list of all MainTasks done in the session
       with their SubTask titles and statuses (via get_tasks()).
    2. Semantic similarity search: top-N SubTask embeddings most similar to the
       next task's intent (via find_relevant_context()).

    Args:
        session_id: Current session identifier.
        next_task_intent: Title + scope of the upcoming sub-task (used as query).
        context_manager: Initialized SemanticContextManager instance.
        limit: Maximum number of semantic matches to include.

    Returns:
        Formatted string with task registry + matched subtask context,
        or empty string if nothing relevant is found.
    """
    parts: list[str] = []

    try:
        # 1. Task registry summary — gives the Orchestrator a structural view of
        #    all MainTasks in the session without scanning conversation history.
        all_tasks = await context_manager.get_tasks(session_id)
        if all_tasks:
            registry_lines: list[str] = ["### Session MainTasks"]
            for mt in all_tasks:
                status_marker = "✓" if mt.status == "completed" else "⏳"
                subtask_titles = ", ".join(f'"{st.title}"' for st in mt.subtasks[:4])
                suffix = "..." if len(mt.subtasks) > 4 else ""
                registry_lines.append(
                    f"{status_marker} [{mt.main_task_id}] {mt.goal}\n"
                    f"   SubTasks: {subtask_titles}{suffix}"
                )
            parts.append("\n".join(registry_lines))
    except Exception as exc:
        _logger.warning("orchestrator_reflect_registry_failed", error=str(exc))

    try:
        # 2. Semantic search — find SubTask embeddings most similar to the intent
        #    of the next task to be resolved.
        matches = await context_manager.find_relevant_context(
            task_id="orchestrator_reflection",
            query=next_task_intent,
            session_id=session_id,
            limit=limit,
        )
        if matches:
            semantic_lines: list[str] = ["### Semantically Relevant SubTasks"]
            for m in matches:
                label = f"{m.agent_type} / {m.task_id}" if m.task_id else "prior task"
                semantic_lines.append(
                    f"[{label} | similarity={m.similarity:.2f}]\n{m.content[:600]}"
                )
            parts.append("\n\n".join(semantic_lines))
    except Exception as exc:
        _logger.warning("orchestrator_reflect_semantic_failed", error=str(exc))

    return "\n\n".join(parts)


def _retrieve_memory_context(*, query: str, session_id: str, agent_id: str) -> _Any:
    """Retrieve memory context using the new simple memory service."""
    try:
        # Use the new memory integration
        from mindflow_backend.orchestrator.memory_integration import get_context_for_agent
        
        # Get context for the agent
        context = asyncio.run(get_context_for_agent(
            session_id=session_id,
            query=query,
            limit=5
        ))
        
        return {"context": context, "references": []}
        
    except Exception as exc:
        _logger.warning("memory_retrieval_failed", error=str(exc), session_id=session_id, agent=agent_id)
        return {"context": "", "references": []}


async def _run_task_pipeline(
    state: OrchestratorState,
    provider: str,
    model: str,
    memory_context: str,
) -> dict[str, Any]:
    """Execute the Decomposition Thinking pipeline with semantic context."""
    from uuid import UUID as _UUID

    from mindflow_backend.decomposition.pipeline.tasker import EnhancedTasker as TaskerV2
    from mindflow_backend.decomposition.pipeline.resolver import ContextAwareResolver
    from mindflow_backend.decomposition.pipeline.scheduler import SemanticScheduler as SchedulerV2
    from mindflow_backend.decomposition.pipeline.synthesizer import TaskSynthesizer as SynthesizerV2
    from mindflow_backend.decomposition.scoring import TaskScorer
    from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import ValidatedTask

    try:
        session_id_str = str(state.get("session_id", "unknown"))
        _logger.info("enhanced_task_pipeline_started", session_id=session_id_str)

        # Step A: Enhanced Decomposition with semantic analysis
        tasker = TaskerV2()
        main, components = await tasker.decompose(
            state["message"],
            session_id=session_id_str,
            complexity_score=state.get("complexity_score", 1.0),
            provider=provider,
            model=model,
            memory_context=memory_context,
        )
        _logger.info("task_decomposed_with_semantics", goal=main.goal, tasks=len(components))

        # Step B: Schedule
        scheduler = SchedulerV2()
        ordered = scheduler.get_execution_order(components)

        # Step C: Context-Aware Resolution + Score
        resolver = ContextAwareResolver()
        scorer = TaskScorer()
        prior_results: dict[str, str] = {}
        validated: list[ValidatedTask] = []
        context_summary = {
            "total_context_matches": 0,
            "dependencies_resolved": 0,
            "semantic_searches": 0,
        }

        # Obtain the context manager once for use during reflection
        from mindflow_backend.orchestrator.semantic_context_manager import get_semantic_context_manager
        _sem_ctx_mgr = await get_semantic_context_manager()

        for contract in ordered:
            _logger.info("task_resolving_with_context", task=contract.title)

            # Orchestrator Reflection — retrieve semantically relevant Task/SubTask
            # context before this resolution starts. This replaces the need to scan
            # the full session: old or sibling task context is fetched via embeddings.
            reflection_ctx = await _orchestrator_reflect(
                session_id=session_id_str,
                next_task_intent=f"{contract.title} {contract.scope}",
                context_manager=_sem_ctx_mgr,
            )
            if reflection_ctx:
                _logger.info(
                    "orchestrator_reflection_ready",
                    task=contract.title,
                    context_chars=len(reflection_ctx),
                )

            # Use context-aware resolver with orchestrator reflection context
            resolution_result = await resolver.resolve(
                contract,
                prior_results,
                provider=provider,
                model=model,
                memory_context=memory_context,
                session_id=session_id_str,
                reflection_context=reflection_ctx,
            )
            
            # Extract the actual task result
            task_result = resolution_result.get("result", "")
            
            # Update context statistics
            context_info = resolution_result.get("context_used", {})
            context_summary["total_context_matches"] += context_info.get("dependency_contexts", 0)
            context_summary["total_context_matches"] += context_info.get("semantic_matches", 0)
            if resolution_result.get("dependencies_resolved", False):
                context_summary["dependencies_resolved"] += 1
            context_summary["semantic_searches"] += 1
            
            # Create component state for scoring (compatibility with existing scorer)
            comp_state = type('ComponentState', (), {
                'evidence': type('Evidence', (), {
                    'agent_notes': task_result,
                    'confidence': 0.8,
                    'context_used': context_info,
                })(),
                'contract': contract,
                'result': task_result,
            })()
            
            score = scorer.score(comp_state, consistency=1.0, agent_confidence=0.8)
            _logger.info(
                "task_scored_with_context", 
                task=contract.title, 
                score=score,
                context_matches=context_info.get("dependency_contexts", 0) + context_info.get("semantic_matches", 0)
            )

            if scorer.is_validated(score):
                notes = comp_state.evidence.agent_notes if comp_state.evidence else ""
                validated.append(
                    ValidatedTask(
                        task_id=contract.task_id,
                        title=contract.title,
                        summary=notes,
                        artifacts=contract.expected_artifacts,
                        score=score,
                    )
                )
                prior_results[str(contract.task_id)] = notes

        # Step D: Enhanced Synthesis with context awareness
        # Parse session_id as UUID, fall back to main_component_id
        try:
            sid = _UUID(session_id_str)
        except ValueError:
            sid = main.main_task_id

        synthesizer = SynthesizerV2()
        synthesis = await synthesizer.synthesize(
            session_id=sid,
            main_contract=main,
            validated_components=validated,
            provider=provider,
            model=model,
        )

        # Step E: Mark MainTask as completed in the task registry
        await _sem_ctx_mgr.complete_main_task(
            main_task_id=str(main.main_task_id),
            session_id=session_id_str,
            final_answer=synthesis.final_answer,
        )

        # Log context usage summary
        _logger.info(
            "enhanced_task_pipeline_completed",
            session_id=session_id_str,
            total_tasks=len(components),
            validated_tasks=len(validated),
            context_summary=context_summary,
        )

        return {
            "response": synthesis.final_answer,
            "task_session": None,
            "error": None,
            "context_summary": context_summary,
        }

    except Exception as exc:
        _logger.error("task_pipeline_error", error=str(exc))
        return {"response": "", "error": f"Task failed: {exc}"}


def respond_node(state: OrchestratorState) -> dict[str, Any]:
    """Finalize the response (no-op in Phase 2 — pass-through)."""
    return state


# ---------------------------------------------------------------------------
# Graph builder (New Architecture)
# ---------------------------------------------------------------------------


def build_simple_orchestrator_flow() -> Any:
    """Build a simple orchestrator flow using the new graph architecture.
    
    Returns a function that can be invoked with::
    
        result = await simple_orchestrate({"message": "...", "provider": "...", "model": "..."})
    
    This function now uses the new graph architecture while maintaining backward compatibility.
    """
    # Use the new architecture from the graphs module
    from mindflow_backend.graphs.orchestrator.simple_flow import build_simple_orchestrator_flow as _build_flow
    return _build_flow()


def create_orchestrator_graph(graph_id: str = "orchestrator"):
    """Create an orchestrator graph using the new architecture."""
    from mindflow_backend.graphs import create_orchestrator_graph as _create_graph
    return _create_graph(graph_id)


# ---------------------------------------------------------------------------
# Legacy Functions (for backward compatibility)
# ---------------------------------------------------------------------------


def build_legacy_orchestrator_flow() -> Any:
    """Build a simple orchestrator flow without langgraph dependency (legacy).
    
    DEPRECATED: Use build_simple_orchestrator_flow() instead.
    """
    async def simple_orchestrate(state: dict[str, Any]) -> dict[str, Any]:
        """Simple orchestration without langgraph (legacy implementation)."""
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
