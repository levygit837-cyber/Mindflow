"""Chain orchestration package.

This package supports multiple chain styles. To keep import-time dependencies
low (and avoid pulling optional components), we expose only the stable public
surface needed by the Orchestrator.
"""

from mindflow_backend.chains.catalog import CHAIN_CATALOG, get_chain
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

__all__ = [
    "CHAIN_CATALOG",
    "get_chain",
    "CodingTaskChain",
    "CodingTaskChainConfig",
    "FileAnalysisChain",
    "FileAnalysisChainConfig",
    "create_file_analysis_chain",
    "ConditionalFileChain",
    "ConditionalFileChainConfig",
    "create_conditional_file_chain",
    "ParallelFileChain",
    "ParallelFileChainConfig",
    "create_parallel_file_chain",
]
