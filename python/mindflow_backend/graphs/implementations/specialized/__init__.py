"""Specialized LangGraph graph implementations.

This module will contain graph implementations tailored for specific
orchestration workflows beyond the general-purpose graph, including:
- Planning graph: Structured multi-step planning with user confirmation loops
- Research graph: Deep-search workflow with source validation and synthesis
- Code generation graph: Iterative code → test → fix cycle
- Analysis graph: Multi-source data gathering and cross-referencing

Each graph will extend the base graph from ``graphs/base/`` and register
itself via the graph registry in ``graphs/registry/``.

Status: Planned — depends on Phase 3 AgentRuntime decomposition completion.
"""

__all__: list[str] = []

# Specialized graphs will be implemented here
# Examples: ResearchWorkflowGraph, CodingWorkflowGraph, AnalysisWorkflowGraph

__all__ = []
