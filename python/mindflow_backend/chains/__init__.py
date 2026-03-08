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

__all__ = [
    "CHAIN_CATALOG",
    "get_chain",
    "CodingTaskChain",
    "CodingTaskChainConfig",
]
