"""Canonical orchestration runtime: route -> execute -> respond.

This module is the runtime source of truth used by
``runtime/streaming/stream.py``. Compatibility adapters may import helpers from
here, but they must not define alternative execution paths.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, TypedDict
from uuid import UUID

from mindflow_backend.graphs.base.graph import SimpleGraph
from mindflow_backend.graphs.base.types import GraphConfig, GraphType
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.nodes.implementations.orchestrator.route_node import RouteNode
from mindflow_backend.nodes.implementations.orchestrator.execute_node import ExecuteNode
from mindflow_backend.nodes.implementations.orchestrator.respond_node import RespondNode

# Legacy imports for backward compatibility
from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime import get_model_for_provider, extract_ai_message_content
from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ChainType,
    ExecutionStrategy,
    OrchestratorDecision,
    Priority,
    SandboxMode,
    ThinkingLevel,
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
            "decision": state.get("decision"),
            "response": state.get("response", ""),
            "error": state.get("error"),
            "complexity_score": state.get("complexity_score", 0.0),
            "task_session": state.get("task_session"),
            "session_id": state.get("session_id", ""),
            "memory_context": state.get("memory_context", ""),
            "agent_type": state.get("agent_type"),
            "folder_path": state.get("folder_path"),
        }
    
    def _from_legacy_state(self, legacy_state: dict[str, Any]) -> GraphState:
        """Convert legacy OrchestratorState back to GraphState format."""
        return self.create_state(
            session_id=legacy_state.get("session_id"),
            initial_data=legacy_state
        )
    
    async def _route_node_legacy(self, state: dict[str, Any]) -> dict[str, Any]:
        """Route using the canonical router + planner, plus complexity scoring."""
        from langchain_core.callbacks.manager import adispatch_custom_event
        from mindflow_backend.orchestrator.routing.intelligent_router import route_message_intelligently
        from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession
        from mindflow_backend.orchestrator.complexity import ComplexityScorer
        from mindflow_backend.schemas.orchestration.orchestrator import ThinkingMode
        settings = get_settings()

        # Emit immediately so the frontend shows a meaningful thought instead of
        # a blank spinner while the two LLM calls run.
        await adispatch_custom_event(
            "agent_thought",
            {"thought": "Analisando sua solicitação e selecionando o agente mais adequado..."},
        )

        session = OrchestratorSession(user_intent=state["message"])
        scorer = ComplexityScorer()

        # Run routing + complexity scoring in PARALLEL — halves the routing latency.
        decision, score = await asyncio.gather(
            route_message_intelligently(
                state["message"],
                session,
                folder_path=state.get("folder_path"),
            ),
            scorer.get_complexity_score(
                state["message"],
                provider=state.get("provider"),
                model=state.get("model"),
            ),
        )

        await adispatch_custom_event(
            "agent_thought",
            {"thought": f"Decisão: agente '{decision.agent.value}' selecionado."},
        )

        if settings.enable_decomposition_thinking and scorer.should_decompose(score):
            decision.thinking_mode = ThinkingMode.DECOMPOSITION
            _logger.info("route_node_triggering_task", score=score)
        elif scorer.should_decompose(score):
            _logger.info("route_node_task_disabled", score=score)

        _logger.info("route_node_completed", agent=decision.agent.value, score=score)
        return {"decision": decision, "complexity_score": score}
    
    async def _execute_node_legacy(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute node implementation with full orchestrator functionality."""
        decision = state["decision"]
        settings = get_settings()
        provider = state.get("provider") or settings.default_provider
        model = decision.model or state.get("model") or settings.default_model
        session_id = str(state.get("session_id", ""))
        from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy, ThinkingMode
        from langchain_core.callbacks.manager import adispatch_custom_event

        # -1. DIRECT_RESPONSE: Orchestrator is the entity — it answers the user directly.
        if getattr(decision, "execution_strategy", ExecutionStrategy.SINGLE_AGENT) == ExecutionStrategy.DIRECT_RESPONSE:
            return await self._orchestrator_direct_response(state, provider, model)

        # 0. Decomposition Thinking Mode takes priority over chain execution
        if decision.thinking_mode == ThinkingMode.DECOMPOSITION and settings.enable_decomposition_thinking:
            memory_result = await self._retrieve_memory_context(
                query=state["message"],
                session_id=session_id,
                agent_id=decision.agent.value,
            )
            if isinstance(memory_result, dict):
                memory_context = memory_result.get("context", "")
            else:
                memory_context = getattr(memory_result, "context", "")
            return await self._run_task_pipeline(state, provider, model, memory_context)

        # Orchestrator announces the delegation — visible to user as a thought
        from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy as _ES
        if getattr(decision, "execution_strategy", None) == _ES.CHAIN:
            chain_label = getattr(decision, "chain_id", "pipeline")
            delegation_msg = f"Iniciando pipeline **{chain_label}**. {decision.rationale}"
        else:
            delegation_msg = f"Delegando para **{decision.agent.value}**. {decision.rationale}"
        await adispatch_custom_event("agent_thought", {"thought": delegation_msg})

        # 1. Chain Execution Mode (explicit orchestrator strategy)
        if getattr(decision, "execution_strategy", ExecutionStrategy.SINGLE_AGENT) == ExecutionStrategy.CHAIN:
            memory_context = ""
            chain_id = getattr(decision, "chain_id", None)

            # Use enhanced chain integration if available
            try:
                from mindflow_backend.orchestrator.chain_integration import execute_chain_with_intelligence

                # The Orchestrator creates the LLM and passes it to the chain so chains
                # never instantiate their own models — they use whichever specialist was
                # selected here.
                chain_agent = get_agent(
                    decision.agent_role or decision.agent,
                    specialist=decision.specialist,
                    agent_id=decision.agent_id,
                )
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

        from langchain_core.callbacks.manager import adispatch_custom_event
        await adispatch_custom_event(
            "agent_thought",
            {"thought": "Recuperando contexto de memória..."},
        )
        memory_result = await self._retrieve_memory_context(
            query=state["message"],
            session_id=session_id,
            agent_id=decision.agent.value,
        )
        if isinstance(memory_result, dict):
            memory_context = memory_result.get("context", "")
        else:
            memory_context = getattr(memory_result, "context", "")

        # 2. Standard Execution Mode
        agent = get_agent(
            decision.agent_role or decision.agent,
            specialist=decision.specialist,
            agent_id=decision.agent_id,
        )
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
        
        # Use the orchestrator's formulated objective when available — it is far
        # more precise than the raw user message and tells the agent exactly what
        # to do.  Fall back to the raw message only if no task was formulated.
        formulated_task = getattr(decision, "task", None) or getattr(decision, "formulated_objective", None)
        if formulated_task and formulated_task.strip():
            messages.append({
                "role": "user",
                "content": (
                    f"{formulated_task}\n\n"
                    f"---\nOriginal user request: {state['message']}"
                ),
            })
        else:
            messages.append({"role": "user", "content": state["message"]})
        
        try:
            from mindflow_backend.schemas.orchestration.orchestrator import ThinkingMode
        except ImportError:
            ThinkingMode = None
        
        try:
            # Enforce sandbox mode based on agent personality.
            # Priority: folder_path from request > agent.root_dir > settings.working_path
            sandbox_root = (
                state.get("folder_path")
                or agent.root_dir
                or (settings.working_path if hasattr(settings, "working_path") else None)
            )
            sandbox = MindFlowSandbox(
                root_dir=sandbox_root,
                read_only=(agent.sandbox == SandboxMode.READ_ONLY),
            )
            registry = create_default_registry(sandbox, session_id=session_id)

            # Get authorized tools for this agent (none for NONE sandbox agents)
            if agent.sandbox == SandboxMode.NONE:
                tools = []
            else:
                tools = registry.get_tools_for_agent(agent.agent_type)

            # Inject root_dir context into system prompt so the LLM knows
            # where its working directory is (root_dir feature).
            if sandbox_root and tools:
                messages = list(messages)
                messages.insert(
                    1,  # after system prompt
                    {
                        "role": "system",
                        "content": (
                            f"Your working directory (root_dir) is: {sandbox_root}\n"
                            "Use this path as the base for all filesystem operations "
                            "unless the user specifies an absolute path."
                        ),
                    },
                )

            llm = get_model_for_provider(provider, model)

            from langchain_core.callbacks.manager import adispatch_custom_event

            # --- Tool-aware execution path ---
            if tools:
                from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
                from mindflow_backend.agents.tools.base.tool_invocation import stream_with_tools

                lc_tools = to_langchain_tools(tools)

                if lc_tools:
                    llm_with_tools = llm.bind_tools(lc_tools)

                    async def _chunk_dispatch(text: str) -> None:
                        await adispatch_custom_event("agent_response", {"chunk": text})

                    async def _event_dispatch(event_name: str, payload: dict) -> None:
                        await adispatch_custom_event(event_name, payload)

                    response_text = await stream_with_tools(
                        llm=llm_with_tools,
                        messages=messages,
                        lc_tools=lc_tools,
                        chunk_dispatcher=_chunk_dispatch,
                        event_dispatcher=_event_dispatch,
                    )
                    _logger.info(
                        f"Tool-aware response length: {len(response_text)}, "
                        f"preview: {response_text[:200] if response_text else 'EMPTY'}"
                    )
                    if not response_text.strip():
                        response_text = "No response generated."
                        _logger.warning("LLM returned empty response after tool loop, using fallback")
                    await self._orchestrator_reflect_on_result(decision, response_text)
                    return {"response": response_text, "error": None}

            # --- Fallback: no tools (or no lc_tools after conversion) ---
            full_response = []
            async for chunk in llm.astream(messages):
                _logger.debug(f"Received chunk: {chunk}")
                thought, texts = extract_chunk_parts(chunk)
                if thought:
                    _logger.debug("agent_thinking", thinking=thought[:200])
                    await adispatch_custom_event("agent_thought", {"thought": thought})
                for text in texts:
                    full_response.append(text)
                    await adispatch_custom_event("agent_response", {"chunk": text})

            response_text = "".join(full_response)
            _logger.info(
                f"Final response length: {len(response_text)}, "
                f"content preview: {response_text[:200] if response_text else 'EMPTY'}"
            )
            if not response_text.strip():
                response_text = "No response generated."
                _logger.warning("LLM returned empty response, using fallback")

            await self._orchestrator_reflect_on_result(decision, response_text)
            return {"response": response_text, "error": None}

        except Exception as exc:
            _logger.error("execute_node_error", error=str(exc))
            return {"response": "", "error": str(exc)}
    
    async def _orchestrator_direct_response(
        self,
        state: dict[str, Any],
        provider: str,
        model: str,
    ) -> dict[str, Any]:
        """Orchestrator answers the user directly — no delegation.

        This is the DIRECT_RESPONSE execution path where the Orchestrator
        acts as a first-class participant in the conversation.
        """
        from langchain_core.callbacks.manager import adispatch_custom_event
        from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
        from mindflow_backend.schemas.orchestration.orchestrator import AgentType

        agent = get_agent(AgentType.ORCHESTRATOR)

        messages = [
            {"role": "system", "content": agent.system_prompt},
            {
                "role": "system",
                "content": (
                    "DIRECT RESPONSE MODE: You are answering this question yourself — no specialist "
                    "agent will be invoked. Do NOT say 'I will send this to the Analyst/Coder/Researcher' "
                    "or any variation of that. Do NOT pretend to delegate. "
                    "Answer the user's question directly, concisely, and helpfully. "
                    "If the question requires reading the codebase or investigating implementation details, "
                    "say you can route this to the Analyst agent and ask the user to confirm."
                ),
            },
            {"role": "user", "content": state["message"]},
        ]

        try:
            llm = get_model_for_provider(provider, model)
            full_response: list[str] = []

            async for chunk in llm.astream(messages):
                thought, texts = extract_chunk_parts(chunk)
                if thought:
                    await adispatch_custom_event("agent_thought", {"thought": thought})
                for text in texts:
                    full_response.append(text)
                    await adispatch_custom_event("agent_response", {"chunk": text})

            response_text = "".join(full_response)
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
    ) -> None:
        """Orchestrator reflects on the completed delegation.

        Emits reflection thoughts visible to the user, showing the Orchestrator
        in its reflection state after the delegated agent completes.
        """
        from langchain_core.callbacks.manager import adispatch_custom_event

        agent_name = decision.agent.value if hasattr(decision.agent, "value") else str(decision.agent)
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
    
    async def _retrieve_memory_context(self, *, query: str, session_id: str, agent_id: str) -> Any:
        """Retrieve memory context using new simple memory service."""
        try:
            from mindflow_backend.orchestrator.memory_integration import get_context_for_agent
            context = await get_context_for_agent(
                session_id=session_id,
                query=query,
                limit=5,
            )
            return {"context": context, "references": []}
        except Exception as exc:
            _logger.warning("memory_retrieval_failed", error=str(exc), session_id=session_id, agent=agent_id)
            return {"context": "", "references": []}
    
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

def build_simple_orchestrator_flow() -> Any:
    """Build a proper LangGraph StateGraph for the orchestrator.

    Returns a compiled LangGraph graph that exposes ``astream_events()`` so
    that ``AgentRuntime._stream_chat_orchestrated`` can stream custom events
    dispatched inside node functions (agent_response, agent_thought, tool_call, …).

    The previous implementation returned a plain coroutine function which does
    not have ``astream_events`` → AttributeError at runtime → stream ended
    immediately with no output.
    """
    from langgraph.graph import StateGraph, END  # type: ignore[import]

    graph_instance = SimpleOrchestratorGraph()

    async def route_node(state: dict[str, Any]) -> dict[str, Any]:
        result = await graph_instance._route_node_legacy(state)
        return {**state, **result}

    async def execute_node(state: dict[str, Any]) -> dict[str, Any]:
        result = await graph_instance._execute_node_legacy(state)
        return {**state, **result}

    async def respond_node(state: dict[str, Any]) -> dict[str, Any]:
        return state

    workflow: Any = StateGraph(dict)
    workflow.add_node("route", route_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("route")
    workflow.add_edge("route", "execute")
    workflow.add_edge("execute", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()
