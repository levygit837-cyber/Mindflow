"""Canonical orchestration runtime: route -> execute -> respond.

This module is the runtime source of truth used by
``runtime/streaming/stream.py``. Compatibility adapters may import helpers from
here, but they must not define alternative execution paths.
"""

from __future__ import annotations

from typing import Any, TypedDict

from mindflow_backend.graphs.base.graph import SimpleGraph
from mindflow_backend.graphs.base.types import GraphConfig, GraphType
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.nodes.implementations.orchestrator.route_node import RouteNode
from mindflow_backend.nodes.implementations.orchestrator.execute_node import ExecuteNode
from mindflow_backend.nodes.implementations.orchestrator.respond_node import RespondNode

# Legacy imports for backward compatibility
from mindflow_backend.agents._registry import get_agent
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.indexing import is_continuation_prompt
from mindflow_backend.runtime import get_model_for_provider, extract_ai_message_content
from mindflow_backend.schemas.orchestration.orchestrator import (
    ExecutionStrategy,
    OrchestratorDecision,
)

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Legacy State (for backward compatibility)
# ---------------------------------------------------------------------------

class OrchestratorState(TypedDict, total=False):
    """State flowing through orchestrator graph (legacy)."""

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
    retry_count: int
    force_specialist: str | None


class SimpleOrchestratorGraph(SimpleGraph):
    """Simple orchestrator graph with linear flow: route → execute → respond.
    
    Enhanced with full orchestrator functionality including:
    - Intelligent routing with complexity scoring
    - Multi-modal execution (single agent, chain, decomposition)
    - Memory integration and context awareness
    - Tool-aware execution with sandbox support
    - Semantic reflection and task pipeline
    """
    
    def __init__(self, graph_id: str = "simple_orchestrator", config: GraphConfig | None = None) -> None:
        graph_config = config or GraphConfig(
            graph_type=GraphType.SIMPLE,
            enable_streaming=True,
            timeout_per_node=30.0,
        )

        super().__init__(graph_id, graph_config)
        
        # Create nodes
        self.route_node = RouteNode("route")
        self.execute_node = ExecuteNode("execute")
        self.respond_node = RespondNode("respond")
        
        # Add nodes to graph
        self.add_node("route", self.route_node)
        self.add_node("execute", self.execute_node)
        self.add_node("respond", self.respond_node)
        
        # Set up connections
        self._setup_connections()
        
        # Set entry point
        self.set_entry_point("route")
    
    def _setup_connections(self) -> None:
        """Set up linear connections between nodes."""
        from mindflow_backend.graphs.base.types import NodeConnection
        
        self.add_connection(NodeConnection(
            source_node="route",
            target_node="execute"
        ))
        
        self.add_connection(NodeConnection(
            source_node="execute", 
            target_node="respond"
        ))
    
    @property
    def graph_type(self) -> GraphType:
        return GraphType.SIMPLE
    
    async def execute(self, state: GraphState) -> GraphState:
        """Execute simple orchestrator flow with full orchestrator functionality."""
        # Convert to legacy state format for compatibility
        legacy_state = self._to_legacy_state(state)
        
        # Initialize nodes
        await self.route_node.initialize()
        await self.execute_node.initialize()
        await self.respond_node.initialize()
        
        # Execute route node
        route_result = await self._route_node_legacy(legacy_state)
        legacy_state["decision"] = route_result["decision"]
        legacy_state["workflow_plan"] = route_result.get("workflow_plan")
        legacy_state["complexity_score"] = route_result.get("complexity_score", 0.0)
        
        # Execute the selected node based on decision
        execute_result = await self._execute_node_legacy(legacy_state)
        legacy_state.update(execute_result)
        
        # Execute respond node (pass-through)
        respond_result = await self._respond_node_legacy(legacy_state)
        legacy_state.update(respond_result)
        
        # Convert back to GraphState
        return self._from_legacy_state(legacy_state)
    
    def _to_legacy_state(self, state: GraphState) -> dict[str, Any]:
        """Convert GraphState to legacy OrchestratorState format."""
        return {
            "message": state.get("message", ""),
            "provider": state.get("provider", ""),
            "model": state.get("model", ""),
            "execution_id": state.get("execution_id"),
            "decision": state.get("decision"),
            "workflow_plan": state.get("workflow_plan"),
            "response": state.get("response", ""),
            "error": state.get("error"),
            "complexity_score": state.get("complexity_score", 0.0),
            "task_session": state.get("task_session"),
            "session_id": state.get("session_id", ""),
            "memory_context": state.get("memory_context", ""),
            "agent_type": state.get("agent_type"),
            "folder_path": state.get("folder_path"),
            "conversation_history": state.get("conversation_history", []),
        }
    
    def _from_legacy_state(self, legacy_state: dict[str, Any]) -> GraphState:
        """Convert legacy OrchestratorState back to GraphState format."""
        return self.create_state(
            session_id=legacy_state.get("session_id"),
            initial_data=legacy_state
        )
    
    async def _route_node_legacy(self, state: dict[str, Any]) -> dict[str, Any]:
        """Route all requests directly to the Orchestrator.

        The Orchestrator is the sole entry point — it converses with the user
        and decides when to delegate via the delegate_to_agent tool.  No
        IntelligentRouter LLM call is needed here.
        """
        from mindflow_backend.schemas.orchestration.orchestrator import AgentType

        decision = OrchestratorDecision(
            agent=AgentType.ORCHESTRATOR,
            execution_strategy=ExecutionStrategy.DIRECT_RESPONSE,
            rationale="Orchestrator handles all requests directly.",
        )
        _logger.info("route_node_completed", agent="orchestrator", strategy="direct_response")
        return {"decision": decision, "workflow_plan": None, "complexity_score": 0.0}
    
    async def _execute_node_legacy(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute node implementation with full orchestrator functionality."""
        decision = state["decision"]
        workflow_plan = state.get("workflow_plan")
        settings = get_settings()
        provider = state.get("provider") or settings.default_provider
        model = decision.model or state.get("model") or settings.default_model
        session_id = str(state.get("session_id", ""))
        from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy, ThinkingMode
        from langchain_core.callbacks.manager import adispatch_custom_event
        from mindflow_backend.orchestrator.step_runner import run_workflow_step

        plan_steps = list(getattr(workflow_plan, "steps", []) or [])
        primary_step = plan_steps[0] if plan_steps else None
        recall_config = getattr(decision, "memory_recall", None)
        memory_result: dict[str, Any] = {"context": "", "references": [], "grounding_recommended": False}
        memory_context = ""
        memory_grounded = False

        if getattr(recall_config, "enabled", True):
            await adispatch_custom_event(
                "agent_thought",
                {"thought": "Recuperando contexto de memória..."},
            )
            memory_result = await self._retrieve_memory_context(
                query=state["message"],
                session_id=session_id,
                agent_id=primary_step.agent_id if primary_step else decision.agent_id,
                recall_config=recall_config,
            )
            memory_context = memory_result.get("context", "") if isinstance(memory_result, dict) else getattr(memory_result, "context", "")
            memory_grounded = self._should_memory_ground_turn(
                query=state["message"],
                memory_result=memory_result,
            )

        # -1. DIRECT_RESPONSE: Orchestrator is the entity — it answers the user directly.
        if getattr(decision, "execution_strategy", ExecutionStrategy.SINGLE_AGENT) == ExecutionStrategy.DIRECT_RESPONSE:
            return await self._orchestrator_direct_response(
                state,
                provider,
                model,
                memory_context=memory_context,
                memory_grounded=memory_grounded,
            )

        # -0.5. GRAPH: Delegate to Plan-and-Execute multi-step graph
        if getattr(decision, "execution_strategy", ExecutionStrategy.SINGLE_AGENT) == ExecutionStrategy.GRAPH:
            from mindflow_backend.graphs.implementations.orchestrator.plan_execute import build_plan_execute_flow
            plan_graph = build_plan_execute_flow()
            result = await plan_graph.ainvoke({
                "message": state["message"],
                "provider": provider,
                "model": model,
                "session_id": session_id,
                "task_id": "",
                "folder_path": state.get("folder_path"),
                "plan": [],
                "full_plan": [],
                "past_steps": [],
                "response": None,
                "retry_count": 0,
                "memory_context": memory_context,
                "workflow_plan": workflow_plan.model_dump() if hasattr(workflow_plan, "model_dump") else workflow_plan,
            })
            return {"response": result.get("response", ""), "error": None}

        # 0. Decomposition Thinking Mode takes priority over chain execution
        if decision.thinking_mode == ThinkingMode.DECOMPOSITION and settings.enable_decomposition_thinking:
            return await self._run_task_pipeline(state, provider, model, memory_context)

        # Orchestrator announces the delegation — visible to user as a thought
        from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy as _ES
        if getattr(decision, "execution_strategy", None) == _ES.CHAIN:
            chain_label = getattr(decision, "chain_id", "pipeline")
            delegation_msg = f"Iniciando pipeline **{chain_label}**. {decision.rationale}"
        else:
            delegated_agent = primary_step.agent_id if primary_step else decision.agent_id
            delegation_msg = f"Delegando para **{delegated_agent}**. {decision.rationale}"
        await adispatch_custom_event("agent_thought", {"thought": delegation_msg})

        # 1. Chain Execution Mode (explicit orchestrator strategy)
        if getattr(decision, "execution_strategy", ExecutionStrategy.SINGLE_AGENT) == ExecutionStrategy.CHAIN:
            chain_id = getattr(decision, "chain_id", None)

            # Use enhanced chain integration if available
            try:
                from mindflow_backend.orchestrator.chain_integration import execute_chain_with_intelligence

                # The Orchestrator creates the LLM and passes it to the chain so chains
                # never instantiate their own models — they use whichever specialist was
                # selected here.
                chain_agent = get_agent(agent_id=primary_step.agent_id if primary_step else decision.agent_id)
                chain_llm = get_model_for_provider(provider, model)

                result = await execute_chain_with_intelligence(
                    message=state["message"],
                    complexity_score=state.get("complexity_score", 0.5),
                    context={
                        "message": state["message"],
                        "session_id": session_id,
                        "provider": provider,
                        "model": model,
                        "memory_context": memory_context,
                        "decision": decision.model_dump() if hasattr(decision, "model_dump") else {},
                        "workflow_plan": workflow_plan.model_dump() if hasattr(workflow_plan, "model_dump") else {},
                        # Specialist injected by the Orchestrator — chains must use this
                        "llm": chain_llm,
                        "agent": chain_agent,
                        "folder_path": state.get("folder_path"),
                    },
                    session_id=session_id,
                    chain_id=getattr(decision, "chain_id", None),
                )
                
                return {
                    "response": result.get("response", ""),
                    "error": result.get("error"),
                    "chain_result": result,
                    "chain_metadata": result.get("execution_metadata"),
                }
                
            except (ImportError, ValueError):
                # No suitable chain found or not available — fall through to single-agent execution
                _logger.warning("chain_not_available_falling_through", chain_id=chain_id)

        if primary_step is None:
            return {"response": "", "error": "Workflow plan missing executable step."}

        async def _chunk_dispatch(text: str) -> None:
            await adispatch_custom_event("agent_response", {"chunk": text})

        async def _event_dispatch(event_name: str, payload: dict) -> None:
            await adispatch_custom_event(event_name, payload)

        result = await run_workflow_step(
            step=primary_step,
            user_message=state["message"],
            provider=provider,
            model=model,
            session_id=session_id,
            folder_path=state.get("folder_path"),
            memory_context=memory_context,
            memory_grounded=memory_grounded,
            conversation_history=state.get("conversation_history") or [],
            chunk_dispatcher=_chunk_dispatch,
            event_dispatcher=_event_dispatch,
        )
        if result.get("error"):
            return {"response": "", "error": result["error"]}

        response_text = result.get("full_output", "")
        if not response_text.strip():
            response_text = "No response generated."
        await self._orchestrator_reflect_on_result(decision, response_text, provider, model)
        return {"response": response_text, "error": None}
    
    async def _orchestrator_direct_response(
        self,
        state: dict[str, Any],
        provider: str,
        model: str,
        *,
        memory_context: str = "",
        memory_grounded: bool = False,
    ) -> dict[str, Any]:
        """Orchestrator acts as central agent with delegate_to_agent tool.

        This is the primary execution path.  The Orchestrator LLM decides whether
        to answer directly or call delegate_to_agent to invoke a specialist.
        """
        from langchain_core.callbacks.manager import adispatch_custom_event
        from mindflow_backend.agents.tools.orchestration.delegate_to_agent import DelegateToAgentTool
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.agents.tools.base.tool_invocation import stream_with_tools

        agent = get_agent(agent_id="orchestrator")
        session_id = str(state.get("session_id", ""))
        execution_id = state.get("execution_id")

        # Build the delegate tool with runtime context
        delegate_tool = DelegateToAgentTool()
        if state.get("folder_path"):
            delegate_tool.root_dir = state["folder_path"]
        if session_id:
            delegate_tool.session_id = session_id
        if execution_id:
            delegate_tool.execution_id = str(execution_id)

        lc_tools = to_langchain_tools([delegate_tool])

        messages: list[dict] = [
            {"role": "system", "content": agent.system_prompt},
        ]
        if memory_context.strip():
            messages.append(
                {
                    "role": "system",
                    "content": f"Memory Context (RAG from agent history):\n{memory_context}",
                }
            )
        if memory_grounded and memory_context.strip():
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "MEMORY-GROUNDED TURN: responda primeiro usando o Memory Context. "
                        "Só diga que precisa investigar mais se a memória for insuficiente."
                    ),
                }
            )
        # Inject conversation history for continuity
        for _h in (state.get("conversation_history") or []):
            messages.append({"role": _h["role"], "content": _h["content"]})
        messages.append({"role": "user", "content": state["message"]})

        try:
            llm = get_model_for_provider(provider, model)
            llm_with_tools = llm.bind_tools(lc_tools)

            async def _chunk_dispatch(text: str) -> None:
                await adispatch_custom_event("agent_response", {"chunk": text})

            async def _event_dispatch(name: str, payload: dict) -> None:
                await adispatch_custom_event(name, payload)

            response_text = await stream_with_tools(
                llm=llm_with_tools,
                messages=messages,
                lc_tools=lc_tools,
                chunk_dispatcher=_chunk_dispatch,
                event_dispatcher=_event_dispatch,
            )

            if not response_text.strip():
                response_text = "Como posso ajudar?"
            return {"response": response_text, "error": None}

        except Exception as exc:
            _logger.error("orchestrator_direct_response_error", error=str(exc))
            return {"response": "", "error": str(exc)}

    async def _orchestrator_reflect_on_result(
        self,
        decision: Any,
        response_text: str,
        provider: str = "",
        model: str = "",
    ) -> None:
        """Orchestrator reflects on the completed delegation.

        For code agents (coder, arch_tech) with substantial responses, runs an
        automatic critic review and emits it as a thought.  For all other agents,
        emits a standard quality reflection.
        """
        from langchain_core.callbacks.manager import adispatch_custom_event

        agent_name = decision.agent_id if getattr(decision, "agent_id", None) else (
            decision.agent.value if hasattr(decision.agent, "value") else str(decision.agent)
        )

        # Auto-critic for code agents with substantial responses
        code_agents = {"coder", "coder:arch_tech"}
        if agent_name in code_agents and len(response_text.strip()) > 200 and provider and model:
            try:
                from mindflow_backend.agents._registry import get_agent as _get_agent
                critic = _get_agent(agent_id="analyst:critic")
                llm = get_model_for_provider(provider, model)
                critique_messages = [
                    {"role": "system", "content": critic.system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Quick review (max 3 bullet points — critical issues only):\n\n"
                            f"{response_text[:2000]}"
                        ),
                    },
                ]
                critique_response = await llm.ainvoke(critique_messages)
                critique_text = (
                    critique_response.content
                    if hasattr(critique_response, "content")
                    else str(critique_response)
                )
                if critique_text.strip():
                    await adispatch_custom_event(
                        "agent_thought",
                        {"thought": f"**Critic review:** {critique_text[:400]}"},
                    )
            except Exception as exc:
                _logger.warning("auto_critic_failed", error=str(exc))
            return

        # Standard reflection for non-code agents
        response_len = len(response_text.strip())
        if response_len == 0:
            quality = "sem resposta gerada — pode ser necessário revisar a delegação"
        elif response_len < 100:
            quality = "resposta curta — verificando se atende ao objetivo"
        else:
            quality = "resposta completa"

        reflection = (
            f"Agente **{agent_name}** concluiu. "
            f"Avaliação: {quality}. "
            f"Delegação com confiança baseada em: {decision.rationale}"
        )

        await adispatch_custom_event("agent_thought", {"thought": reflection})

    async def _respond_node_legacy(self, state: dict[str, Any]) -> dict[str, Any]:
        """Respond node implementation - final pass-through in Phase 2."""
        return state
    
    async def _retrieve_memory_context(
        self,
        *,
        query: str,
        session_id: str,
        agent_id: str,
        recall_config: Any | None = None,
    ) -> Any:
        """Retrieve memory context using canonical PostgreSQL/pgvector façade.

        Implements adaptive recall (Phase 4):
        - Tries current session first via SessionMemoryService.
        - Falls back to cross-session if hits < 2 or best_score < 0.55.
        - Returns empty context string when no hits — never injects an empty block.
        """
        try:
            from mindflow_backend.orchestrator.memory_integration import (
                MemoryRecallRequest,
                get_memory_integration,
            )

            mi = get_memory_integration()
            response = await mi.recall(
                MemoryRecallRequest(
                    session_id=session_id,
                    query=query,
                    agent_id=agent_id,
                    top_k=getattr(recall_config, "top_k", 4),
                    top_k_messages=getattr(recall_config, "top_k", 4),
                    top_k_blocks=min(getattr(recall_config, "top_k", 4), 2),
                    min_score=getattr(recall_config, "min_score", 0.35),
                    policy=getattr(recall_config, "policy", "adaptive"),
                    scope=getattr(recall_config, "scope", "current_then_cross"),
                    cross_session_fallback=getattr(recall_config, "cross_session_fallback", True),
                    cross_session_min_hits=getattr(recall_config, "cross_session_min_hits", 2),
                    fallback_score_threshold=getattr(recall_config, "fallback_score_threshold", 0.55),
                    category_filters=mi.infer_categories(query),
                )
            )
            context = mi.format_context(response)
            return {
                "context": context,
                "references": response.references,
                "grounding_recommended": response.grounding_recommended,
                "best_score": response.best_score,
                "hits": response.hits,
            }
        except Exception as exc:
            _logger.warning("memory_retrieval_failed", error=str(exc), session_id=session_id, agent=agent_id)
            return {"context": "", "references": [], "grounding_recommended": False, "best_score": 0.0, "hits": []}

    def _should_memory_ground_turn(self, *, query: str, memory_result: Any) -> bool:
        if not is_continuation_prompt(query):
            return False
        if isinstance(memory_result, dict):
            if memory_result.get("grounding_recommended"):
                return True
            return float(memory_result.get("best_score", 0.0)) >= 0.72
        return bool(getattr(memory_result, "grounding_recommended", False))
    
    async def _run_task_pipeline(
        self,
        state: dict[str, Any],
        provider: str,
        model: str,
        memory_context: str,
    ) -> dict[str, Any]:
        """Execute Decomposition Thinking pipeline with semantic context."""
        from uuid import UUID as _UUID

        from mindflow_backend.decomposition.pipeline.tasker import EnhancedTasker as TaskerV2
        from mindflow_backend.decomposition.pipeline.resolver import ContextAwareResolver
        from mindflow_backend.decomposition.pipeline.scheduler import SemanticScheduler as SchedulerV2
        from mindflow_backend.decomposition.pipeline.synthesizer import TaskSynthesizer as SynthesizerV2
        from mindflow_backend.decomposition.scoring import TaskScorer
        from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import ValidatedTask
        from mindflow_backend.services import get_todo_planning_service
        from mindflow_backend.services.orchestration.todo_planning_service import build_todo_items_from_subtasks

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
            todo_service = get_todo_planning_service()
            await todo_service.replace_list(
                session_id=session_id_str,
                task_id=str(main.main_task_id),
                goal=main.goal,
                items=build_todo_items_from_subtasks(
                    components,
                    overall_complexity=state.get("complexity_score", 1.0),
                ),
                source="decomposition_pipeline",
            )

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

            # Obtain context manager once for use during reflection
            from mindflow_backend.orchestrator.semantic_context_manager import get_semantic_context_manager
            _sem_ctx_mgr = await get_semantic_context_manager()

            for contract in ordered:
                _logger.info("task_resolving_with_context", task=contract.title)

                # Orchestrator Reflection — retrieve semantically relevant Task/SubTask
                # context before this resolution starts. This replaces the need to scan
                # the full session: old or sibling task context is fetched via embeddings.
                reflection_ctx = await self._orchestrator_reflect(
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

                focused_items = await todo_service.focus_complex_items(
                    session_id=session_id_str,
                    task_id=str(main.main_task_id),
                    limit=3,
                )
                focus_lines = [
                    "### Todo Focus",
                    *[
                        f"- [{item.item_id}] {item.title} "
                        f"(complexity={item.complexity_score}, status={item.status})"
                        for item in focused_items.items
                    ],
                ] if focused_items.items else []
                if focus_lines:
                    focus_context = "\n".join(focus_lines)
                    reflection_ctx = f"{focus_context}\n\n{reflection_ctx}" if reflection_ctx else focus_context

                await todo_service.update_item_status(
                    session_id=session_id_str,
                    task_id=str(main.main_task_id),
                    item_id=str(contract.task_id),
                    status="in_progress",
                    notes=f"Resolving {contract.title}",
                )

                # Use context-aware resolver with orchestrator reflection context
                try:
                    resolution_result = await resolver.resolve(
                        contract,
                        prior_results,
                        provider=provider,
                        model=model,
                        memory_context=memory_context,
                        session_id=session_id_str,
                        reflection_context=reflection_ctx,
                    )
                except Exception as exc:
                    await todo_service.update_item_status(
                        session_id=session_id_str,
                        task_id=str(main.main_task_id),
                        item_id=str(contract.task_id),
                        status="failed",
                        notes=str(exc),
                    )
                    raise
                
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

                notes = comp_state.evidence.agent_notes if comp_state.evidence else task_result
                if scorer.is_validated(score):
                    validated.append(
                        ValidatedTask(
                            task_id=contract.task_id,
                            title=contract.title,
                            summary=notes,
                            artifacts=contract.expected_artifacts,
                            score=score,
                        )
                    )
                    await todo_service.update_item_status(
                        session_id=session_id_str,
                        task_id=str(main.main_task_id),
                        item_id=str(contract.task_id),
                        status="completed",
                        notes=notes[:400],
                    )
                else:
                    await todo_service.update_item_status(
                        session_id=session_id_str,
                        task_id=str(main.main_task_id),
                        item_id=str(contract.task_id),
                        status="blocked",
                        notes=f"Validation score below threshold: {score:.2f}",
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
            await todo_service.close_list(
                session_id=session_id_str,
                task_id=str(main.main_task_id),
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
    
    async def _orchestrator_reflect(
        self,
        *,
        session_id: str,
        next_task_intent: str,
        context_manager: Any,
        limit: int = 3,
    ) -> str:
        """Retrieve semantically relevant Task/SubTask context for the upcoming resolution.

        Uses Task/SubTask embedding store and task registry — never scans the
        full session linearly. Combines two signals:
        1. Task registry summary: structured list of all MainTasks done in the session
           with their SubTask titles and statuses (via get_tasks()).
        2. Semantic similarity search: top-N SubTask embeddings most similar to the
           next task's intent (via find_relevant_context()).

        Args:
            session_id: Current session identifier.
            next_task_intent: Title + scope of upcoming sub-task (used as query).
            context_manager: Initialized SemanticContextManager instance.
            limit: Maximum number of semantic matches to include.

        Returns:
            Formatted string with task registry + matched subtask context,
            or empty string if nothing relevant is found.
        """
        parts: list[str] = []

        try:
            # 1. Task registry summary — gives the Orchestrator a structural view of
            #    all MainTasks in session without scanning conversation history.
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
    
    def validate(self) -> list[str]:
        """Validate simple orchestrator graph."""
        issues = super().validate()
        
        # Check that all required nodes are present
        required_nodes = ["route", "execute", "respond"]
        for node_id in required_nodes:
            if node_id not in self._nodes:
                issues.append(f"Missing required node: {node_id}")
        
        # Validate flow is linear
        if len(self._connections) != 2:
            issues.append("Simple orchestrator should have exactly 2 connections")
        
        return issues


# ---------------------------------------------------------------------------
# Backward compatibility function
# ---------------------------------------------------------------------------

def build_simple_orchestrator_flow(
    *,
    checkpointer: Any | None = None,
    store: Any | None = None,
    interrupt_before: list[str] | None = None,
    interrupt_after: list[str] | None = None,
) -> Any:
    """Build a proper LangGraph StateGraph for the orchestrator.

    Returns a compiled LangGraph graph that exposes ``astream_events()`` so
    that ``AgentRuntime._stream_chat_orchestrated`` can stream custom events
    dispatched inside node functions (agent_response, agent_thought, tool_call, …).

    The flow includes a supervisor node with conditional retry:
        route → execute → supervisor → (accept) → respond
                              ↑            ↓ (retry, max 2x)
                              └────────────┘
    """
    from langgraph.graph import StateGraph, END  # type: ignore[import]
    from mindflow_backend.nodes.implementations.orchestrator.supervisor_node import SupervisorNode

    graph_instance = SimpleOrchestratorGraph()
    supervisor = SupervisorNode()

    async def route_node(state: dict[str, Any]) -> dict[str, Any]:
        result = await graph_instance._route_node_legacy(state)
        return {**state, **result}

    async def execute_node(state: dict[str, Any]) -> dict[str, Any]:
        # Apply force_specialist override from supervisor retry
        force_spec = state.get("force_specialist")
        if force_spec and state.get("decision"):
            decision = state["decision"]
            try:
                from mindflow_backend.schemas.orchestration.specialists import SpecialistType
                from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
                workflow_plan = state.get("workflow_plan")
                if workflow_plan and getattr(workflow_plan, "steps", None):
                    forced_spec = SpecialistType(force_spec)
                    primary = workflow_plan.steps[0]
                    forced_policy = get_agent_runtime_policy(primary.agent_role, specialist=forced_spec)
                    decision = decision.model_copy(
                        update={
                            "agent": forced_policy.agent_role,
                            "agent_role": forced_policy.agent_role,
                            "agent_id": forced_policy.agent_id,
                            "specialist": forced_spec,
                            "tools": list(forced_policy.tools),
                            "sandbox": forced_policy.sandbox,
                            "thinking": forced_policy.thinking_level,
                        }
                    )
                    workflow_plan = workflow_plan.model_copy(
                        update={
                            "route": workflow_plan.route.model_copy(update={"specialist": forced_spec}),
                            "steps": [
                                primary.model_copy(
                                    update={
                                        "agent_id": forced_policy.agent_id,
                                        "specialist": forced_spec,
                                        "tools": list(forced_policy.tools),
                                        "sandbox": forced_policy.sandbox.value,
                                        "thinking": forced_policy.thinking_level,
                                    }
                                ),
                                *workflow_plan.steps[1:],
                            ],
                        }
                    )
                state = {**state, "decision": decision, "workflow_plan": workflow_plan}
            except Exception:
                pass  # If override fails, use original decision

        result = await graph_instance._execute_node_legacy(state)
        return {**state, **result}

    async def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
        verdict = await supervisor.evaluate(state)
        if verdict == "retry":
            retry_count = state.get("retry_count", 0) + 1
            return {**state, "retry_count": retry_count, "force_specialist": "deep_iteration"}
        return state

    def quality_router(state: dict[str, Any]) -> str:
        response: str = state.get("response") or ""
        error = state.get("error")
        retry_count: int = state.get("retry_count", 0)

        if (error or len(response.strip()) < 80) and retry_count < 2:
            return "retry"
        return "accept"

    async def respond_node(state: dict[str, Any]) -> dict[str, Any]:
        return state

    workflow: Any = StateGraph(dict)
    workflow.add_node("route", route_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("route")
    workflow.add_edge("route", "execute")
    workflow.add_edge("execute", "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        quality_router,
        {
            "accept": "respond",
            "retry": "execute",
        },
    )
    workflow.add_edge("respond", END)

    return workflow.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
    )
