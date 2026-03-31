"""External service exceptions.

All exceptions related to network connectivity, third-party APIs, and integration failures.
"""

from .integration import IntegrationError
from .network import NetworkError
from .third_party import ThirdPartyAPIError

__all__ = [
    "NetworkError",
    "ThirdPartyAPIError",
    "IntegrationError",
]
