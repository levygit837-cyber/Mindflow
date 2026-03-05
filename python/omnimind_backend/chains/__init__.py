"""Chain implementations for OmniMind orchestration."""

# Base classes
from omnimind_backend.chains.base import (
    BaseChain,
    ChainType,
    ChainStatus,
    ChainStep,
    StepType,
    StepResult,
    ChainExecutor,
    ExecutionContext,
    ChainConfig,
    ChainMetrics,
    StepStatus,
    StepContext,
    StepMetrics,
    COMMON_STEP_TEMPLATES,
)

# Chain builders (will be implemented)
# from omnimind_backend.chains.builders import (
#     SequentialChainBuilder,
#     ConditionalChainBuilder,
#     AdaptiveChainBuilder,
# )

# Chain templates (will be implemented)
# from omnimind_backend.chains.templates import (
#     ResearchChain,
#     CodingChain,
#     AnalysisChain,
# )

# Manager (will be implemented)
# from omnimind_backend.chains.manager import (
#     ChainManager,
#     get_chain_manager,
# )

__all__ = [
    # Base classes
    "BaseChain",
    "ChainType",
    "ChainStatus",
    "ChainStep",
    "StepType",
    "StepResult",
    "ChainExecutor",
    "ExecutionContext",
    "ChainConfig",
    "ChainMetrics",
    "StepStatus",
    "StepContext",
    "StepMetrics",
    "COMMON_STEP_TEMPLATES",
]
