"""Enhanced circuit breaker components.

Provides configuration, metrics, and adaptive threshold logic
for the enhanced circuit breaker.
"""

# Import GrpcCircuitBreaker from the parent module's circuit_breaker.py file
import sys
from pathlib import Path

# Temporarily add parent to path to import from circuit_breaker.py (not this package)
_parent = Path(__file__).parent.parent
_cb_py = _parent / "circuit_breaker.py"

if _cb_py.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_cb_module", _cb_py)
    _cb_module = importlib.util.module_from_spec(spec)
    sys.modules["_cb_module"] = _cb_module
    spec.loader.exec_module(_cb_module)
    GrpcCircuitBreaker = _cb_module.GrpcCircuitBreaker
    CircuitBreakerConfig = _cb_module.CircuitBreakerConfig
    CircuitState = _cb_module.CircuitState
    CircuitBreakerOpenError = _cb_module.CircuitBreakerOpenError
    CallResult = _cb_module.CallResult
else:
    raise ImportError("circuit_breaker.py not found")

from .config import AdaptiveThresholdType, EnhancedCircuitBreakerConfig
from .metrics import CircuitBreakerMetrics

__all__ = [
    "GrpcCircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitBreakerOpenError",
    "CallResult",
    "AdaptiveThresholdType",
    "EnhancedCircuitBreakerConfig",
    "CircuitBreakerMetrics",
]