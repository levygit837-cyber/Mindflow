"""Chain catalog for Orchestrator execution.

DEPRECATED: This module is maintained for backward compatibility.
New code should use mindflow_backend.chains.factory instead.

The orchestrator needs a stable way to resolve `chain_id` → executable chain.
This module intentionally returns concrete chain instances with an async
`execute(context)` method.
"""

from __future__ import annotations

from typing import Any, Callable

# Import the new factory system
from mindflow_backend.chains.factory import (
    get_chain_factory,
    ChainRequest,
    create_and_execute_chain,
)

# Legacy imports for backward compatibility
from mindflow_backend.chains.templates.conditional_workflow_chain import (
    ConditionalWorkflowChain,
    ConditionalWorkflowConfig,
    create_conditional_workflow_chain,
)
from mindflow_backend.chains.templates.analysis_chain import (
    AnalysisChain,
    AnalysisChainConfig,
    create_analysis_chain,
)
from mindflow_backend.chains.templates.coding_task_chain import (
    CodingTaskChain,
    CodingTaskChainConfig,
)
from mindflow_backend.chains.templates.file_analysis_chain import (
    FileAnalysisChain,
    FileAnalysisChainConfig,
    create_file_analysis_chain,
)
from mindflow_backend.chains.templates.conditional_file_chain import (
    ConditionalFileChain,
    ConditionalFileChainConfig,
    create_conditional_file_chain,
)
from mindflow_backend.chains.templates.parallel_file_chain import (
    ParallelFileChain,
    ParallelFileChainConfig,
    create_parallel_file_chain,
)


ChainFactory = Callable[[], Any]


def _coding_task_chain_factory() -> CodingTaskChain:
    return CodingTaskChain(CodingTaskChainConfig(chain_id="coding_task"))


def _analysis_chain_factory() -> AnalysisChain:
    return create_analysis_chain(AnalysisChainConfig(chain_id="analysis_task"))


def _conditional_workflow_factory() -> ConditionalWorkflowChain:
    return create_conditional_workflow_chain(ConditionalWorkflowConfig(chain_id="conditional_workflow"))


def _file_analysis_factory() -> FileAnalysisChain:
    return create_file_analysis_chain(FileAnalysisChainConfig())


def _conditional_file_analysis_factory() -> ConditionalFileChain:
    return create_conditional_file_chain(ConditionalFileChainConfig())


def _parallel_file_analysis_factory() -> ParallelFileChain:
    return create_parallel_file_chain(ParallelFileChainConfig())


# Legacy catalog for backward compatibility
CHAIN_CATALOG: dict[str, ChainFactory] = {
    "coding_task": _coding_task_chain_factory,
    "analysis_task": _analysis_chain_factory,
    "conditional_workflow": _conditional_workflow_factory,
    "file_analysis": _file_analysis_factory,
    "conditional_file_analysis": _conditional_file_analysis_factory,
    "parallel_file_analysis": _parallel_file_analysis_factory,
}


def get_chain(chain_id: str) -> Any:
    """Return a new chain instance for `chain_id`.
    
    DEPRECATED: Use get_chain_factory().create_chain() instead.
    """
    try:
        factory = CHAIN_CATALOG[chain_id]
    except KeyError as exc:
        raise KeyError(f"Unknown chain_id={chain_id!r}. Available: {sorted(CHAIN_CATALOG)}") from exc
    return factory()


# New recommended interface
async def execute_chain(
    chain_id: str,
    context: dict[str, Any],
    config: dict[str, Any] | None = None,
    **kwargs
) -> dict[str, Any]:
    """Execute a chain using the new factory system."""
    
    request = ChainRequest(
        chain_id=chain_id,
        config=config,
        **kwargs
    )
    
    factory = get_chain_factory()
    return await factory.execute_chain(request, context)


def get_chain_info(chain_id: str) -> dict[str, Any]:
    """Get information about a chain."""
    
    factory = get_chain_factory()
    metadata = factory.registry.get_metadata(chain_id)
    
    if not metadata:
        raise KeyError(f"Unknown chain_id={chain_id!r}")
    
    return {
        "chain_id": metadata.chain_id,
        "name": metadata.name,
        "description": metadata.description,
        "capabilities": [cap.value for cap in metadata.capabilities],
        "complexity": metadata.complexity.value,
        "estimated_execution_time": metadata.estimated_execution_time,
        "required_agents": [agent.value for agent in metadata.required_agents],
        "default_config": metadata.default_config,
    }


def list_available_chains() -> list[dict[str, Any]]:
    """List all available chains with their metadata."""
    
    factory = get_chain_factory()
    chains = factory.registry.list_chains()
    
    return [
        {
            "chain_id": metadata.chain_id,
            "name": metadata.name,
            "description": metadata.description,
            "capabilities": [cap.value for cap in metadata.capabilities],
            "complexity": metadata.complexity.value,
            "estimated_execution_time": metadata.estimated_execution_time,
        }
        for metadata in chains
    ]


def find_chains_for_task(task_type: str, complexity: str | None = None) -> list[dict[str, Any]]:
    """Find chains suitable for a specific task."""
    
    from mindflow_backend.chains.factory import ChainComplexity
    
    factory = get_chain_factory()
    complexity_enum = ChainComplexity(complexity) if complexity else None
    
    chains = factory.registry.find_chains_for_task(task_type, complexity_enum)
    
    return [
        {
            "chain_id": metadata.chain_id,
            "name": metadata.name,
            "description": metadata.description,
            "capabilities": [cap.value for cap in metadata.capabilities],
            "complexity": metadata.complexity.value,
            "estimated_execution_time": metadata.estimated_execution_time,
        }
        for metadata in chains
    ]

