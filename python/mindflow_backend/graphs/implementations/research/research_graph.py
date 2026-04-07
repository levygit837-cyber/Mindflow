"""ResearchGraph — Multi-source research with deduplication.

Fluxo: initialize → (search → collect)* → deduplicate → synthesize → cite → report
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

DEFAULT_MAX_SEARCHES = 10
DEFAULT_NODE_TIMEOUT = 60  # seconds
CONFIDENCE_THRESHOLD = 0.85
MIN_FINDINGS_THRESHOLD = 15


class ResearchGraph(BaseGraph):
    """Grafo de pesquisa multi-fonte com deduplicação."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.WEB_RESEARCH

    def __init__(self, graph_id: str = "research", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        from mindflow_backend.nodes.implementations.research import (
            CiteNode,
            CollectNode,
            DeduplicateNode,
            ResearchInitializeNode,
            ResearchReportNode,
            ResearchSynthesizeNode,
            SearchNode,
        )

        self.add_node("initialize", ResearchInitializeNode("initialize"))
        self.add_node("search", SearchNode("search"))
        self.add_node("collect", CollectNode("collect"))
        self.add_node("deduplicate", DeduplicateNode("deduplicate"))
        self.add_node("synthesize", ResearchSynthesizeNode("synthesize"))
        self.add_node("cite", CiteNode("cite"))
        self.add_node("report", ResearchReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="search"))
        self.add_connection(NodeConnection(source_node="search", target_node="collect"))
        self.add_connection(NodeConnection(source_node="collect", target_node="deduplicate"))
        self.add_connection(NodeConnection(source_node="deduplicate", target_node="synthesize"))
        self.add_connection(NodeConnection(source_node="synthesize", target_node="cite"))
        self.add_connection(NodeConnection(source_node="cite", target_node="report"))

    @staticmethod
    def _should_continue_search(state: dict[str, Any]) -> str:
        """Determine if search should continue or proceed to deduplication.
        
        Stops if:
        - Max iterations reached
        - Minimum findings threshold met
        - High confidence score achieved
        """
        iteration = state.get("iteration", 0)
        max_searches = state.get("max_searches", DEFAULT_MAX_SEARCHES)
        findings = state.get("findings", [])
        synthesis = state.get("synthesis", {})
        
        # Check max iterations
        if iteration >= max_searches:
            _logger.info(
                "search_max_iterations_reached",
                iteration=iteration,
                max_searches=max_searches,
            )
            return "deduplicate"
        
        # Check minimum findings threshold
        if len(findings) >= MIN_FINDINGS_THRESHOLD:
            _logger.info(
                "search_min_findings_reached",
                findings_count=len(findings),
                threshold=MIN_FINDINGS_THRESHOLD,
            )
            return "deduplicate"
        
        # Check confidence score
        confidence = synthesis.get("confidence_score", 0.0)
        if confidence >= CONFIDENCE_THRESHOLD and synthesis:
            _logger.info(
                "search_confidence_threshold_reached",
                confidence=confidence,
                threshold=CONFIDENCE_THRESHOLD,
            )
            return "deduplicate"
        
        # Continue searching with refined query
        return "search"

    @staticmethod
    def _refine_query(original_query: str, iteration: int) -> str:
        """Refine query for subsequent iterations.
        
        Adds context modifiers to improve search results.
        """
        modifiers = [
            "tutorial",
            "guide",
            "examples",
            "best practices",
            "documentation",
            "implementation",
        ]
        
        if iteration == 1:
            return original_query
        elif iteration < len(modifiers) + 1:
            modifier = modifiers[iteration - 2]
            return f"{original_query} {modifier}"
        else:
            return original_query

    async def execute(self, state: GraphState) -> GraphState:
        """Executa fluxo de pesquisa multi-fonte com timeout e refinamento de query."""
        current_node = self._entry_point
        nodes_executed = 0
        node_timeouts = 0
        
        # Record start time for duration calculation
        state["start_time"] = time.time()
        original_query = state.get("query", "")

        while current_node:
            state["current_node"] = current_node
            
            # Refine query before search node (after first iteration)
            if current_node == "search" and nodes_executed > 0:
                iteration = state.get("iteration", 0)
                refined_query = self._refine_query(original_query, iteration)
                state["query"] = refined_query
                _logger.info(
                    "query_refined",
                    original_query=original_query,
                    refined_query=refined_query,
                    iteration=iteration,
                )

            try:
                node = self._nodes[current_node]
                
                # Execute node with timeout
                try:
                    result = await asyncio.wait_for(
                        node.execute(state),
                        timeout=DEFAULT_NODE_TIMEOUT,
                    )
                    if isinstance(result, dict):
                        state.update(result)
                    nodes_executed += 1
                except asyncio.TimeoutError:
                    _logger.error(
                        "node_timeout",
                        node=current_node,
                        timeout=DEFAULT_NODE_TIMEOUT,
                    )
                    node_timeouts += 1
                    state["error"] = f"Node {current_node} timed out after {DEFAULT_NODE_TIMEOUT}s"
                    break

            except Exception as e:
                state["error"] = str(e)
                _logger.error("research_error", node=current_node, error=str(e), exc_info=True)
                break

            if current_node == "collect":
                next_node = self._should_continue_search(dict(state))
            elif current_node == "search":
                next_node = "collect"
            else:
                next_nodes = self.get_next_nodes(current_node)
                next_node = next_nodes[0] if next_nodes else None

            current_node = next_node

        # Calculate final metrics
        duration_seconds = time.time() - state.get("start_time", time.time())
        
        state["metrics"] = {
            "nodes_executed": nodes_executed,
            "nodes_failed": 1 if state.get("error") else 0,
            "node_timeouts": node_timeouts,
            "duration_seconds": round(duration_seconds, 2),
            "total_tokens_used": 0,
            "error_details": [state["error"]] if state.get("error") else [],
        }

        _logger.info(
            "research_graph_completed",
            nodes_executed=nodes_executed,
            node_timeouts=node_timeouts,
            duration_seconds=duration_seconds,
            has_error=bool(state.get("error")),
        )

        return state

    def validate(self) -> list[str]:
        return self.validate_structure()