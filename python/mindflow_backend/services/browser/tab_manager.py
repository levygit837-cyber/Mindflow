"""Multi-tab management for LightPanda browsers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from playwright.async_api import Page, BrowserContext

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class TabInfo:
    """Information about a tab/page."""

    tab_id: str
    page: Page
    created_at: datetime
    last_used: datetime
    url: str | None = None
    status: str = "idle"  # idle, loading, ready, error

    def is_idle(self, timeout_seconds: int = 300) -> bool:
        """Check if tab has been idle for too long."""
        return self.status == "idle" and (
            datetime.utcnow() - self.last_used
        ).total_seconds() > timeout_seconds


class TabManager:
    """Manages multiple tabs in a browser context."""

    def __init__(
        self, context: BrowserContext, max_tabs: int = 10, tab_idle_timeout: int = 300
    ):
        """Initialize the tab manager.

        Args:
            context: Playwright browser context
            max_tabs: Maximum number of tabs per context
            tab_idle_timeout: Timeout before idle tabs are cleaned up (seconds)
        """
        self.context = context
        self.max_tabs = max_tabs
        self.tab_idle_timeout = tab_idle_timeout
        self._tabs: dict[str, TabInfo] = {}
        self._lock = asyncio.Lock()
        self._logger = get_logger(__name__)

    async def create_tab(self, tab_id: str | None = None) -> TabInfo:
        """Create a new tab in the current context.

        Args:
            tab_id: Tab ID (generated if None)

        Returns:
            TabInfo: Created tab information

        Raises:
            RuntimeError: If max tabs limit reached
        """
        if tab_id is None:
            tab_id = f"tab-{int(datetime.utcnow().timestamp())}"

        async with self._lock:
            # Check max tabs limit
            if len(self._tabs) >= self.max_tabs:
                # Cleanup idle tabs first
                await self.cleanup_idle_tabs()

                if len(self._tabs) >= self.max_tabs:
                    raise RuntimeError(f"Max tabs limit reached: {self.max_tabs}")

            # Create new page
            page = await self.context.new_page()

            tab_info = TabInfo(
                tab_id=tab_id,
                page=page,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow(),
            )

            self._tabs[tab_id] = tab_info

            self._logger.info(
                "tab_created", tab_id=tab_id, total_tabs=len(self._tabs)
            )

            return tab_info

    async def get_tab(self, tab_id: str) -> TabInfo | None:
        """Get existing tab by ID.

        Args:
            tab_id: Tab ID

        Returns:
            TabInfo | None: Tab information if found
        """
        async with self._lock:
            return self._tabs.get(tab_id)

    async def close_tab(self, tab_id: str) -> bool:
        """Close specific tab.

        Args:
            tab_id: Tab ID to close

        Returns:
            bool: True if tab was closed, False if not found
        """
        async with self._lock:
            tab_info = self._tabs.get(tab_id)
            if not tab_info:
                return False

            try:
                await tab_info.page.close()
                del self._tabs[tab_id]

                self._logger.info("tab_closed", tab_id=tab_id)
                return True
            except Exception as exc:
                self._logger.error("tab_close_failed", tab_id=tab_id, error=str(exc))
                return False

    async def cleanup_idle_tabs(self) -> int:
        """Remove tabs that have been idle for too long.

        Returns:
            int: Number of tabs cleaned up
        """
        async with self._lock:
            to_remove = [
                tab_id
                for tab_id, tab_info in self._tabs.items()
                if tab_info.is_idle(self.tab_idle_timeout)
            ]

            for tab_id in to_remove:
                await self.close_tab(tab_id)

            if to_remove:
                self._logger.info("idle_tabs_cleaned", count=len(to_remove))

            return len(to_remove)

    async def close_all_tabs(self) -> int:
        """Close all tabs.

        Returns:
            int: Number of tabs closed
        """
        async with self._lock:
            tab_ids = list(self._tabs.keys())
            count = 0

            for tab_id in tab_ids:
                if await self.close_tab(tab_id):
                    count += 1

            return count

    async def get_active_tabs_count(self) -> int:
        """Get number of active tabs.

        Returns:
            int: Number of active tabs
        """
        async with self._lock:
            return len(self._tabs)

    async def execute_in_tab(self, tab_id: str, operation: callable) -> Any:
        """Execute operation in specific tab.

        Args:
            tab_id: Tab ID
            operation: Operation to execute (receives Page)

        Returns:
            Any: Operation result

        Raises:
            ValueError: If tab not found
        """
        tab_info = await self.get_tab(tab_id)
        if not tab_info:
            raise ValueError(f"Tab {tab_id} not found")

        tab_info.last_used = datetime.utcnow()
        tab_info.status = "loading"

        try:
            result = await operation(tab_info.page)
            tab_info.status = "ready"
            tab_info.url = tab_info.page.url
            return result
        except Exception as exc:
            tab_info.status = "error"
            raise
