"""Observability and debugging for LightPanda browsers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from playwright.async_api import Page, Browser

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class BrowserDebugInfo:
    """Browser debug information."""

    instance_id: str
    url: str
    title: str
    memory_usage_mb: float
    cpu_usage_percent: float
    open_tabs: int
    console_errors: int
    network_requests: int
    timestamp: datetime


class BrowserDebugger:
    """Tools for debug and observability."""

    def __init__(self):
        """Initialize the browser debugger."""
        self._logger = get_logger(__name__)
        self._debug_sessions: dict[str, dict[str, Any]] = {}

    async def start_debug_session(
        self, instance_id: str, page: Page, browser: Browser
    ) -> str:
        """Start debug session.

        Args:
            instance_id: Browser instance ID
            page: Playwright page
            browser: Playwright browser

        Returns:
            str: Session ID
        """
        session_id = f"debug-{instance_id}-{int(datetime.utcnow().timestamp())}"

        debug_info = {
            "session_id": session_id,
            "instance_id": instance_id,
            "started_at": datetime.utcnow(),
            "page": page,
            "browser": browser,
            "console_logs": [],
            "network_requests": [],
            "performance_metrics": [],
        }

        # Setup listeners
        page.on("console", lambda msg: self._handle_console(debug_info, msg))
        page.on("request", lambda request: self._handle_request(debug_info, request))
        page.on("response", lambda response: self._handle_response(debug_info, response))

        self._debug_sessions[session_id] = debug_info

        self._logger.info("debug_session_started", session_id=session_id, instance_id=instance_id)

        return session_id

    def _handle_console(self, debug_info: dict[str, Any], msg) -> None:
        """Handle console message.

        Args:
            debug_info: Debug session info
            msg: Console message
        """
        debug_info["console_logs"].append(
            {"type": msg.type, "text": msg.text, "timestamp": datetime.utcnow().isoformat()}
        )

    # Note: _handle_request and _handle_response removed as Playwright doesn't have direct event listeners
    # Use page.route() for request interception if needed

    async def get_debug_info(self, session_id: str) -> BrowserDebugInfo | None:
        """Get debug information.

        Args:
            session_id: Session ID

        Returns:
            BrowserDebugInfo | None: Debug info if found
        """
        if session_id not in self._debug_sessions:
            return None

        debug_info = self._debug_sessions[session_id]
        page = debug_info["page"]

        # Get current state
        url = page.url
        title = await page.title()

        # Count console errors
        console_errors = sum(
            1 for log in debug_info["console_logs"] if log["type"] in ["error", "warning"]
        )

        # Get performance metrics (simplified)
        metrics = await page.evaluate(
            """() => ({
            memory: performance.memory ? performance.memory.usedJSHeapSize / 1024 / 1024 : 0,
            timing: performance.timing ? {
                load: performance.timing.loadEventEnd - performance.timing.navigationStart,
                dom: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart
            } : null
        })"""
        )

        return BrowserDebugInfo(
            instance_id=debug_info["instance_id"],
            url=url,
            title=title,
            memory_usage_mb=metrics.get("memory", 0),
            cpu_usage_percent=0.0,  # Would need CDP for this
            open_tabs=1,  # Would need context tracking
            console_errors=console_errors,
            network_requests=len(debug_info["network_requests"]),
            timestamp=datetime.utcnow(),
        )

    async def capture_network_waterfall(self, session_id: str) -> list[dict[str, Any]]:
        """Capture network waterfall.

        Args:
            session_id: Session ID

        Returns:
            list[dict[str, Any]]: Network waterfall
        """
        if session_id not in self._debug_sessions:
            return []

        debug_info = self._debug_sessions[session_id]

        # Build waterfall from requests
        waterfall = []
        for i, req in enumerate(debug_info["network_requests"]):
            waterfall.append(
                {
                    "index": i,
                    "url": req["url"],
                    "method": req["method"],
                    "resource_type": req["resource_type"],
                    "timestamp": req["timestamp"],
                    "status": req.get("status"),
                    "duration": 0,  # Would need response timing
                }
            )

        return waterfall

    async def capture_screenshot_on_failure(
        self, session_id: str, error: Exception
    ) -> bytes | None:
        """Capture screenshot on failure.

        Args:
            session_id: Session ID
            error: Error that occurred

        Returns:
            bytes | None: Screenshot bytes
        """
        if session_id not in self._debug_sessions:
            return None

        debug_info = self._debug_sessions[session_id]
        page = debug_info["page"]

        try:
            self._logger.error(
                "capturing_screenshot_on_failure",
                session_id=session_id,
                error=str(error),
            )
            screenshot = await page.screenshot(full_page=True)
            return screenshot
        except Exception as exc:
            self._logger.error("screenshot_capture_failed", error=str(exc))
            return None

    async def close_debug_session(self, session_id: str) -> bool:
        """Close debug session.

        Args:
            session_id: Session ID

        Returns:
            bool: True if closed successfully
        """
        if session_id not in self._debug_sessions:
            return False

        del self._debug_sessions[session_id]
        self._logger.info("debug_session_closed", session_id=session_id)
        return True
