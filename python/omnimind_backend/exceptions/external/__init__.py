"""External service exceptions.

All exceptions related to network connectivity, third-party APIs, and integration failures.
"""

from .network import NetworkError
from .third_party import ThirdPartyAPIError
from .integration import IntegrationError

__all__ = [
    "NetworkError",
    "ThirdPartyAPIError",
    "IntegrationError",
]
