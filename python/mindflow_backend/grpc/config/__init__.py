"""gRPC configuration package."""

from .config import GrpcConfig, GrpcClientConfig

# Dynamic configuration imports
try:
    from .dynamic import get_config_manager
    from .dynamic.storage import create_config_storage
    from .dynamic.validator import ConfigValidator
    __all__ = [
        'GrpcConfig',
        'GrpcClientConfig', 
        'get_config_manager',
        'create_config_storage',
        'ConfigValidator'
    ]
except ImportError:
    # Fallback if dynamic components are not available
    __all__ = ['GrpcConfig', 'GrpcClientConfig']

# Environment profiles imports
try:
    from .profiles import get_environment_loader
    __all__.append('get_environment_loader')
except ImportError:
    pass

# Feature flags imports
try:
    from .features import get_feature_toggles
    __all__.append('get_feature_toggles')
except ImportError:
    pass
