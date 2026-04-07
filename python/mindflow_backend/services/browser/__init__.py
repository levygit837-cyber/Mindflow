"""Browser service for LightPanda integration.

This module provides centralized browser lifecycle management for MindFlow,
including Docker container management, snapshot handling with PostgreSQL persistence,
session persistence, multi-tab support, intelligent browser pool, error recovery,
network interception, advanced automation, performance optimization, observability,
sandbox and isolation, and metrics collection.
"""

from __future__ import annotations

from mindflow_backend.services.browser.docker_manager import (
    BrowserInstance,
    BrowserInstanceConfig,
    ContainerCreationError,
    ContainerNotFoundError,
    DockerManagerError,
    InstanceStatus,
    LightPandaDockerManager,
    MaxInstancesError,
    RateLimitError,
)
from mindflow_backend.services.browser.lifecycle_service import (
    BrowserHandle,
    BrowserLifecycleService,
    BrowserRequirements,
)
from mindflow_backend.services.browser.metrics_collector import (
    BrowserMetricsCollector,
)
from mindflow_backend.services.browser.snapshot_manager import (
    BrowserSnapshotManager,
)
from mindflow_backend.services.browser.snapshot_models import (
    Snapshot,
    SnapshotData,
)
from mindflow_backend.services.browser.snapshot_storage import (
    SnapshotStorage,
    SnapshotStorageError,
)
from mindflow_backend.services.browser.session_manager import (
    BrowserSession,
    SessionManager,
)
from mindflow_backend.services.browser.tab_manager import (
    TabInfo,
    TabManager,
)
from mindflow_backend.services.browser.pool_manager import (
    PoolConfig,
    PoolState,
    PooledBrowser,
    BrowserPoolManager,
)
from mindflow_backend.services.browser.resilience_manager import (
    ErrorType,
    RecoveryStrategy,
    BrowserResilienceManager,
)
from mindflow_backend.services.browser.network_manager import (
    NetworkConfig,
    NetworkRequest,
    NetworkResponse,
    NetworkManager,
)
from mindflow_backend.services.browser.automation_helper import AutomationHelper
from mindflow_backend.services.browser.performance_optimizer import (
    PerformanceOptimizer,
)
from mindflow_backend.services.browser.debugger import (
    BrowserDebugger,
    BrowserDebugInfo,
)
from mindflow_backend.services.browser.security_manager import (
    SecurityConfig,
    SecurityManager,
)

__all__ = [
    "BrowserInstance",
    "BrowserInstanceConfig",
    "ContainerCreationError",
    "ContainerNotFoundError",
    "DockerManagerError",
    "InstanceStatus",
    "LightPandaDockerManager",
    "MaxInstancesError",
    "RateLimitError",
    "BrowserHandle",
    "BrowserLifecycleService",
    "BrowserRequirements",
    "BrowserMetricsCollector",
    "BrowserSnapshotManager",
    "Snapshot",
    "SnapshotData",
    "SnapshotStorage",
    "SnapshotStorageError",
    "BrowserSession",
    "SessionManager",
    "TabInfo",
    "TabManager",
    "PoolConfig",
    "PoolState",
    "PooledBrowser",
    "BrowserPoolManager",
    "ErrorType",
    "RecoveryStrategy",
    "BrowserResilienceManager",
    "NetworkConfig",
    "NetworkRequest",
    "NetworkResponse",
    "NetworkManager",
    "AutomationHelper",
    "PerformanceOptimizer",
    "BrowserDebugger",
    "BrowserDebugInfo",
    "SecurityConfig",
    "SecurityManager",
]
