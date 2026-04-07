"""Network interception and monitoring for LightPanda."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from playwright.async_api import Page, Route

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class NetworkRequest:
    """Represents a network request."""

    request_id: str
    url: str
    method: str
    headers: dict[str, str]
    resource_type: str
    timestamp: datetime
    post_data: str | None = None


@dataclass
class NetworkResponse:
    """Represents a network response."""

    request_id: str
    status: int
    headers: dict[str, str]
    body: str | None
    timestamp: datetime
    duration_ms: float


@dataclass
class NetworkConfig:
    """Configuration for network interception."""

    block_images: bool = False
    block_fonts: bool = False
    block_trackers: bool = True
    custom_block_patterns: list[str] = field(default_factory=list)
    custom_headers: dict[str, str] = field(default_factory=dict)
    modify_user_agent: bool = False
    log_requests: bool = True
    log_responses: bool = False


class NetworkManager:
    """Manages network interception and monitoring."""

    # Common tracker domains
    TRACKER_DOMAINS = [
        "google-analytics.com",
        "googletagmanager.com",
        "doubleclick.net",
        "facebook.com/tr",
        "analytics.twitter.com",
    ]

    def __init__(self, config: NetworkConfig | None = None):
        """Initialize the network manager.

        Args:
            config: Network configuration
        """
        self.config = config or NetworkConfig()
        self._logger = get_logger(__name__)

        self._requests: dict[str, NetworkRequest] = {}
        self._responses: dict[str, NetworkResponse] = {}

    async def setup_interception(self, page: Page) -> None:
        """Configure network interception on the page.

        Args:
            page: Playwright page
        """

        async def route_handler(route: Route):
            """Handler for routing requests."""
            request = route.request
            url = request.url

            # Check if should block
            if self._should_block(url, request.resource_type):
                self._logger.debug(
                    "request_blocked", url=url, resource_type=request.resource_type
                )
                await route.abort()
                return

            # Modify headers if configured
            headers = {**request.headers}
            if self.config.custom_headers:
                headers.update(self.config.custom_headers)

            # Log request
            if self.config.log_requests:
                network_request = NetworkRequest(
                    request_id=request.guid,
                    url=url,
                    method=request.method,
                    headers=dict(request.headers),
                    resource_type=request.resource_type,
                    timestamp=datetime.utcnow(),
                    post_data=request.post_data,
                )
                self._requests[network_request.request_id] = network_request

            # Continue with potentially modified headers
            await route.continue_(headers=headers)

        # Enable routing
        await page.route("**/*", route_handler)

        # Setup response listener if logging enabled
        if self.config.log_responses:
            page.on("response", self._handle_response)

        from dataclasses import asdict
        self._logger.info("network_interception_setup", config=asdict(self.config))

    def _should_block(self, url: str, resource_type: str) -> bool:
        """Check if request should be blocked.

        Args:
            url: Request URL
            resource_type: Resource type

        Returns:
            bool: True if should block
        """
        # Block images
        if self.config.block_images and resource_type == "image":
            return True

        # Block fonts
        if self.config.block_fonts and resource_type == "font":
            return True

        # Block trackers
        if self.config.block_trackers:
            for tracker_domain in self.TRACKER_DOMAINS:
                if tracker_domain in url:
                    return True

        # Block custom patterns
        for pattern in self.config.custom_block_patterns:
            if pattern in url:
                return True

        return False

    async def _handle_response(self, response) -> None:
        """Handler for responses.

        Args:
            response: Playwright response
        """
        try:
            network_response = NetworkResponse(
                request_id=response.request.guid,
                status=response.status,
                headers=dict(response.headers),
                body=None,  # Don't capture body by default (memory)
                timestamp=datetime.utcnow(),
                duration_ms=None,  # Will be calculated
            )

            # Calculate duration
            if response.request.guid in self._requests:
                request = self._requests[response.request.guid]
                duration = (network_response.timestamp - request.timestamp).total_seconds() * 1000
                network_response.duration_ms = duration

            self._responses[network_response.request_id] = network_response

            self._logger.debug(
                "response_received",
                url=response.url,
                status=response.status,
                duration_ms=network_response.duration_ms,
            )
        except Exception as exc:
            self._logger.error("response_handler_failed", error=str(exc))

    async def get_request_metrics(self) -> dict[str, Any]:
        """Get request metrics.

        Returns:
            dict[str, Any]: Request metrics
        """
        total_requests = len(self._requests)
        total_responses = len(self._responses)

        # Calculate average duration
        durations = [r.duration_ms for r in self._responses.values() if r.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Count by resource type
        resource_types = {}
        for request in self._requests.values():
            resource_types[request.resource_type] = resource_types.get(request.resource_type, 0) + 1

        # Count blocked requests
        blocked_count = sum(
            1
            for r in self._requests.values()
            if self._should_block(r.url, r.resource_type)
        )

        return {
            "total_requests": total_requests,
            "total_responses": total_responses,
            "blocked_requests": blocked_count,
            "average_duration_ms": avg_duration,
            "resource_types": resource_types,
        }

    def clear_metrics(self) -> None:
        """Clear collected metrics."""
        self._requests.clear()
        self._responses.clear()
