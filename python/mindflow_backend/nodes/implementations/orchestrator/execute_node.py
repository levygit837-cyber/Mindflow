"""Execute node - invokes the LLM with the selected agent's prompt and tools."""

from __future__ import annotations

from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.streamable import StreamableNode
from mindflow_backend.schemas.orchestration.orchestrator import (
    OrchestratorDecision,
    SandboxMode,
)


class ExecuteNode(StreamableNode, BaseNode):
    """Node that executes agent logic with tools and LLM calls."""
    
    def __init__(self, node_id: str = "execute") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.EXECUTOR,
            category=NodeCategory.LLM_INVOKE,
            description="Invoke the LLM using the selected agent's personality and tools"
        )
        
        # Required inputs for execution
        self.config.required_inputs = {"decision", "message"}
        self.config.outputs = {"response", "error"}
        self.config.enable_streaming = True
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent logic using AgentBridge with Deep Work continuation support."""
        from mindflow_backend.nodes.implementations.integration.agent_bridge import AgentBridge
        from mindflow_backend.orchestrator.deep_work import (
            build_continuation_context,
            should_continue_investigation,
        )

        _logger = get_logger(__name__)

        decision = state["decision"]
        settings = get_settings()
        session_id = str(state.get("session_id", ""))

        # Deep Work state
        investigation_history: list[str] = []
        current_depth = 0
        max_depth = 1000  # Practically unlimited
        accumulated_response = ""

        try:
            # Create AgentBridge for the specified agent
            agent_bridge = AgentBridge(
                node_id=f"{self.node_id}_bridge",
                agent_type=decision.agent.value,
                sandbox_mode=SandboxMode.FULL
            )

            # Initialize the bridge
            await agent_bridge.initialize()

            # Initial message
            current_message = state["message"]

            # Deep Work Loop
            while current_depth < max_depth:
                # Prepare agent execution context
                agent_context = {
                    "message": current_message,
                    "session_id": session_id,
                    "provider": state.get("provider") or settings.default_provider,
                    "model": decision.model or state.get("model") or settings.default_model
                }

                # Execute agent through bridge
                bridge_result = await agent_bridge.execute(agent_context)

                # Extract response from bridge result
                response = bridge_result.get("agent_response", "")
                error = bridge_result.get("error")

                if error:
                    _logger.error("execute_node_bridge_error", error=error, depth=current_depth)
                    self.set_node_state("error_count", self.get_node_state("error_count", 0) + 1)
                    return {"response": accumulated_response or "", "error": error}

                # Accumulate response
                if accumulated_response:
                    accumulated_response += f"\n\n--- CONTINUATION TURN {current_depth + 1} ---\n\n{response}"
                else:
                    accumulated_response = response

                # Update node state
                self.set_node_state("execution_count", self.get_node_state("execution_count", 0) + 1)
                self.set_node_state("last_agent", decision.agent.value)
                self.set_node_state("tokens_used", self.get_node_state("tokens_used", 0) + bridge_result.get("tokens_used", 0))

                # Capture thoughts if available
                thought = bridge_result.get("agent_thoughts")
                if thought:
                    self.set_node_state("last_thought", thought)

                # Check if agent wants to continue investigating
                should_continue, reason = should_continue_investigation(response, current_depth, max_depth)

                if not should_continue:
                    _logger.info("deep_work_completed", depth=current_depth, reason=reason)
                    break

                # Agent wants to continue - prepare next turn
                _logger.info("deep_work_continuing", depth=current_depth, reason=reason)
                investigation_history.append(response[:200])  # Store summary
                current_depth += 1

                # Build continuation context for next turn
                current_message = build_continuation_context(
                    previous_response=response,
                    investigation_history=investigation_history,
                    current_depth=current_depth
                )

            # Update deep work metrics
            if current_depth > 0:
                self.set_node_state("deep_work_sessions", self.get_node_state("deep_work_sessions", 0) + 1)
                self.set_node_state("max_depth_reached", max(self.get_node_state("max_depth_reached", 0), current_depth))
                _logger.info("deep_work_session_completed", total_turns=current_depth + 1)

            return {"response": accumulated_response, "error": None}

        except Exception as exc:
            _logger.error("execute_node_error", error=str(exc), depth=current_depth)
            self.set_node_state("error_count", self.get_node_state("error_count", 0) + 1)
            return {"response": accumulated_response or "", "error": str(exc)}
    
    async def _stream_execution(self, state: dict[str, Any]) -> Any:
        """Stream execution for LLM responses."""
        
        # For now, fall back to non-streaming
        # In a full implementation, this would use LLM streaming capabilities
        result = await self.execute(state)
        
        # Emit chunks for compatibility
        yield await self._emit_chunk("Executing agent...", {"status": "starting"})
        yield await self._emit_chunk("Processing request...", {"status": "processing"})
        yield await self._emit_chunk("Generating response...", {"status": "generating"})
        
        # Final result
        final_result = {
            "response": result.get("response", ""),
            "error": result.get("error"),
            "node_id": self.node_id,
        }
        yield await self._emit_final_chunk(final_result)
    
    def _build_messages(self, agent: Any, message: str, memory_context: str) -> list[dict]:
        """Build the message list for LLM."""
        messages = [{"role": "system", "content": agent.system_prompt}]
        
        if memory_context.strip():
            messages.append({
                "role": "system",
                "content": f"Memory Context (RAG from agent history):\n{memory_context}"
            })
        
        messages.append({"role": "user", "content": message})
        return messages
    
    def _setup_sandbox(self, agent: Any, settings: Any) -> MindFlowSandbox:
        """Set up the sandbox for tool execution."""
        sandbox_root = getattr(settings, "working_path", None)
        return MindFlowSandbox(
            root_dir=sandbox_root,
            read_only=(agent.sandbox == SandboxMode.READ_ONLY),
        )
    
    def _get_tools_for_agent(self, agent: Any, registry: Any) -> list:
        """Get authorized tools for the agent."""
        if agent.sandbox == SandboxMode.NONE:
            return []
        return registry.get_tools_for_agent(agent)
    
    def _extract_response_text(self, response: Any) -> str:
        """Extract text content from LLM response."""
        if hasattr(response, 'content'):
            return str(response.content)
        elif isinstance(response, str):
            return response
        elif isinstance(response, list):
            text_parts = []
            for item in response:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
        return str(response)
    
    def _extract_thoughts(self, response: Any) -> str:
        """Extract thoughts from response metadata."""
        if hasattr(response, "response_metadata") and "thought" in response.response_metadata:
            return response.response_metadata["thought"]
        elif hasattr(response, "additional_kwargs"):
            return response.additional_kwargs.get("thought", "")
        return ""
    
    def _count_tokens(self, text: str) -> int:
        """Simple token counting (placeholder implementation)."""
        # In a real implementation, this would use proper tokenization
        return len(text.split())
    
    def _retrieve_memory_context(self, *, query: str, session_id: str, agent_id: str) -> str:
        """Retrieve memory context for the query."""
        from mindflow_backend.infra.config import get_settings
        from mindflow_backend.memory import get_memory_service
        
        settings = get_settings()
        if not settings.memory_enabled or not session_id:
            return ""
        
        try:
            from mindflow_backend.storage import db_session
            with db_session() as db:
                result = get_memory_service().retrieve_context_for_query(
                    db=db,
                    session_id=session_id,
                    agent_id=agent_id,
                    query=query,
                )
                return result.context
        except Exception:
            return ""
    
    async def _run_dt_pipeline(
        self,
        state: dict[str, Any],
        provider: str,
        model: str,
        memory_context: str,
    ) -> dict[str, Any]:
        """Execute the Decomposition Thinking pipeline."""
        from uuid import UUID as _UUID

        from mindflow_backend.infra.logging import get_logger
        from mindflow_backend.orchestrator.decomposition.decomposer_v2 import DecomposerV2
        from mindflow_backend.orchestrator.decomposition.resolver_v2 import ResolverV2
        from mindflow_backend.orchestrator.decomposition.scheduler_v2 import SchedulerV2
        from mindflow_backend.orchestrator.decomposition.scorer_adapter import ComponentScorer
        from mindflow_backend.orchestrator.decomposition.synthesizer_v2 import SynthesizerV2
        from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
            ValidatedComponent,
        )
        
        _logger = get_logger(__name__)
        
        try:
            session_id_str = str(state.get("session_id", "unknown"))
            _logger.info("dt_pipeline_started", session_id=session_id_str)
            
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
            _logger.info("dt_decomposed", goal=main.goal, components=len(components))
            
            # Step B: Schedule
            scheduler = SchedulerV2()
            ordered = scheduler.get_execution_order(components)
            
            # Step C: Resolve + Score
            resolver = ResolverV2()
            scorer = ComponentScorer()
            prior_results: dict[str, str] = {}
            validated: list[ValidatedComponent] = []
            
            for contract in ordered:
                _logger.info("dt_resolving", component=contract.title)

                # Enrich memory_context with cross-task context from previously completed components
                enriched_memory = memory_context
                if prior_results:
                    try:
                        from mindflow_backend.memory.task_memory.api import get_cross_task_api
                        from mindflow_backend.storage import db_session
                        cross_task_api = get_cross_task_api()
                        with db_session() as db:
                            ctx = await cross_task_api.get_context_for_subtask(
                                db=db,
                                requesting_task_id=str(contract.component_id),
                                query=contract.title,
                                sibling_task_ids=list(prior_results.keys()),
                            )
                        if ctx.has_content:
                            enriched_memory = (
                                f"{memory_context}\n\n{ctx.formatted_context}"
                                if memory_context
                                else ctx.formatted_context
                            )
                    except Exception as _cross_exc:
                        _logger.debug("cross_task_context_skip", error=str(_cross_exc))

                comp_state = await resolver.resolve(
                    contract, prior_results, provider=provider, model=model, memory_context=enriched_memory,
                )
                score = scorer.score(comp_state, consistency=1.0, agent_confidence=0.8)
                _logger.info("dt_scored", component=contract.title, score=score)

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
                    # Store result in task memory for future sibling retrieval (best-effort)
                    try:
                        from mindflow_backend.memory.task_memory.api import get_cross_task_api
                        from mindflow_backend.storage import db_session
                        with db_session() as db:
                            await get_cross_task_api().store_subtask_result(
                                db=db,
                                task_id=str(contract.component_id),
                                result_content=notes,
                            )
                            db.commit()
                    except Exception as _store_exc:
                        _logger.debug("cross_task_store_skip", error=str(_store_exc))
            
            # Step D: Synthesize
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
            
            # Update node state
            self.set_node_state("dt_executions", self.get_node_state("dt_executions", 0) + 1)
            self.set_node_state("dt_components_processed", len(components))
            
            return {"response": synthesis.final_answer, "dt_session": None, "error": None}
            
        except Exception as exc:
            _logger.error("dt_pipeline_error", error=str(exc))
            return {"response": "", "error": f"DT failed: {exc}"}
    
    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate execution inputs."""
        errors = []
        
        if "decision" not in state:
            errors.append("Missing required input: decision")
        elif not isinstance(state["decision"], OrchestratorDecision):
            errors.append("decision must be an OrchestratorDecision instance")
        
        if "message" not in state:
            errors.append("Missing required input: message")
        
        return errors
    
    async def _on_initialize(self) -> None:
        """Initialize the execute node."""
        self.set_node_state("execution_count", 0)
        self.set_node_state("dt_executions", 0)
        self.set_node_state("tokens_used", 0)
        self.set_node_state("error_count", 0)
        self.set_node_state("deep_work_sessions", 0)
        self.set_node_state("max_depth_reached", 0)
