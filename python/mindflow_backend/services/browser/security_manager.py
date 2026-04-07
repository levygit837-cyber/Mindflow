"""Sandbox and isolation for LightPanda browsers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from playwright.async_api import BrowserContext

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class SecurityConfig:
    """Configuration for browser security."""

    proxy_rotation: bool = False
    user_agent_rotation: bool = True
    anti_detection: bool = True
    cookie_isolation: bool = True
    storage_isolation: bool = True


class SecurityManager:
    """Manages browser sandbox and isolation."""

    # Common user agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self, config: SecurityConfig | None = None):
        """Initialize the security manager.

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()
        self._logger = get_logger(__name__)
        self._user_agent_index = 0
        self._proxy_index = 0

        # Proxies for rotation (example - would be configured in production)
        self._proxies = [
            # Add proxy servers here
        ]

    async def setup_isolated_context(
        self,
        context: BrowserContext,
        session_id: str,
    ) -> None:
        """Setup isolated browser context for session.

        Args:
            context: Playwright browser context
            session_id: Session ID

        Note:
            User agent and proxy rotation must be applied during context creation
            via get_context_options(). This method applies anti-detection measures
            that can be set after context creation.
        """
        # Anti-detection measures
        if self.config.anti_detection:
            await self._apply_anti_detection(context)

        self._logger.info("context_isolated", session_id=session_id)

    def _get_rotated_user_agent(self) -> str:
        """Get rotated user agent.

        Returns:
            str: User agent string
        """
        user_agent = self.USER_AGENTS[self._user_agent_index]
        self._user_agent_index = (self._user_agent_index + 1) % len(self.USER_AGENTS)
        return user_agent

    async def _apply_anti_detection(self, context: BrowserContext) -> None:
        """Apply anti-detection measures.

        Args:
            context: Playwright browser context
        """
        # Set realistic viewport
        await context.set_viewport_size(width=1920, height=1080)

        # Set timezone
        await context.set_timezone_id("America/New_York")

        # Set locale
        await context.set_locale("en-US")

        # Set geolocation (optional)
        await context.set_geolocation({"latitude": 40.7128, "longitude": -74.0060})

        # Grant permissions for geolocation
        await context.grant_permissions(["geolocation"])

        self._logger.debug("anti_detection_applied")

    def get_context_options(
        self, session_id: str, user_agent: str | None = None
    ) -> dict[str, Any]:
        """Get context options for isolated context creation.

        Args:
            session_id: Session ID
            user_agent: Custom user agent (optional)

        Returns:
            dict[str, Any]: Context options
        """
        options = {
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
        }

        # User agent rotation
        if self.config.user_agent_rotation:
            options["user_agent"] = user_agent or self._get_rotated_user_agent()

        # Proxy rotation
        if self.config.proxy_rotation and self._proxies:
            proxy = self._proxies[self._proxy_index]
            options["proxy"] = {"server": proxy}
            self._proxy_index = (self._proxy_index + 1) % len(self._proxies)
            self._logger.debug("proxy_rotated", session_id=session_id, proxy=proxy)

        return options

    def get_proxy(self) -> str | None:
        """Get next proxy for rotation.

        Returns:
            str | None: Proxy server or None
        """
        if not self.config.proxy_rotation or not self._proxies:
            return None

        proxy = self._proxies[self._proxy_index]
        self._proxy_index = (self._proxy_index + 1) % len(self._proxies)
        return proxy

    async def clear_session_data(self, context: BrowserContext) -> None:
        """Clear all session data from context.

        Args:
            context: Playwright browser context
        """
        # Clear cookies
        await context.clear_cookies()

        # Clear storage (would need page access)
        self._logger.debug("session_data_cleared")
