"""PinchTab browser automation service.

Provides HTTP API wrapper for PinchTab browser automation with
async instance management, lifecycle control, and error handling.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx

from mindflow_backend.utils.network import get_port_manager
from mindflow_backend.agents.tools.specialist.research.monitoring.pitchtab_monitor import get_pitchtab_monitor
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.agents.research import (
    BrowserAction,
    BrowserActionRequest,
    BrowserActionResponse,
    BrowserSession,
    IterationType,
    ResearchStatus,
)

_logger = get_logger(__name__)


class PinchTabService:
    """Service for managing PinchTab browser instances and operations."""
    
    def __init__(self) -> None:
        """Initialize PinchTab service with default configuration."""
        self.settings = get_settings()
        # Remove global base_url - each instance will have its own client
        self._active_instances: dict[str, BrowserSession] = {}
        self._instance_clients: dict[str, httpx.AsyncClient] = {}
        self.port_manager = get_port_manager()
        self.monitor = get_pitchtab_monitor()
        
    async def __aenter__(self) -> PinchTabService:
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - cleanup all instances."""
        await self.cleanup_all()
        # Cleanup all instance clients
        for client in self._instance_clients.values():
            await client.aclose()
        self._instance_clients.clear()
            
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        browser_id: str | None = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Make HTTP request to PinchTab API with error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            browser_id: Browser session identifier (required for instance-specific requests)
            **kwargs: Additional request arguments
        """
        if browser_id and browser_id in self._instance_clients:
            # Use instance-specific client
            client = self._instance_clients[browser_id]
        else:
            # For global operations like listing instances, use default client
            if not hasattr(self, '_default_client') or self._default_client is None:
                self._default_client = httpx.AsyncClient(
                    base_url="http://localhost:9867",
                    timeout=30.0,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
                )
            client = self._default_client
        
        try:
            response = await client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            _logger.error(
                "pinchtab_http_error",
                method=method,
                endpoint=endpoint,
                browser_id=browser_id,
                status_code=exc.response.status_code,
                response_text=exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            _logger.error(
                "pinchtab_request_error",
                method=method,
                endpoint=endpoint,
                browser_id=browser_id,
                error=str(exc),
            )
            raise
            
    async def create_instance(
        self, 
        headless: bool = True, 
        stealth: bool = True,
        preferred_port: int | None = None,
    ) -> BrowserSession:
        """Create a new browser instance.
        
        Args:
            headless: Run browser without UI
            stealth: Enable stealth mode to avoid detection
            preferred_port: Preferred port for the instance
            
        Returns:
            BrowserSession with instance details
            
        Raises:
            httpx.HTTPStatusError: If instance creation fails
        """
        start_time = time.time()
        
        try:
            # Allocate port using port manager
            if preferred_port and await self.port_manager.is_available(preferred_port):
                port = preferred_port
            else:
                port = await self.port_manager.allocate_port()
            
            # Update base URL for this instance
            instance_base_url = f"http://localhost:{port}"
            
            # Create instance via monitor for better process management
            instance_id = f"browser_{int(time.time())}"
            instance_info = await self.monitor.start_instance(
                instance_id=instance_id,
                headless=headless,
                stealth=stealth,
                preferred_port=port,
            )
            
            # Create instance-specific HTTP client
            instance_client = httpx.AsyncClient(
                base_url=instance_base_url,
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            # Create browser session
            session = BrowserSession(
                browser_id=instance_info["instance_id"],
                instance_id=instance_info["instance_id"],
                tab_id=instance_info["port"],  # Use port as tab_id for API compatibility
                status=ResearchStatus.COMPLETED,
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                last_activity=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            
            # Store instance and its dedicated client
            self._active_instances[browser_id] = session
            self._instance_clients[browser_id] = instance_client
            
            # Update health checker with successful start
            await self.monitor.health_checker.update_process_health(
                instance_id, "running", is_error=False
            )
            
            _logger.info(
                "pinchtab_instance_created",
                browser_id=browser_id,
                instance_id=session.instance_id,
                port=port,
                duration_ms=int((time.time() - start_time) * 1000),
            )
            
            return session
            
        except Exception as exc:
            _logger.error(
                "pinchtab_instance_creation_failed",
                error=str(exc),
                duration_ms=int((time.time() - start_time) * 1000),
            )
            raise
            
    async def close_instance(self, browser_id: str) -> bool:
        """Close a browser instance.
        
        Args:
            browser_id: Browser session identifier
            
        Returns:
            True if successful, False otherwise
        """
        if browser_id not in self._active_instances:
            _logger.warning("pinchtab_instance_not_found", browser_id=browser_id)
            return False
            
        session = self._active_instances[browser_id]
        start_time = time.time()
        
        try:
            # Stop instance via monitor
            success = await self.monitor.stop_instance(browser_id)
            
            if success:
                # Close instance-specific client
                if browser_id in self._instance_clients:
                    await self._instance_clients[browser_id].aclose()
                    del self._instance_clients[browser_id]
                
                # Update session status
                session.status = ResearchStatus.COMPLETED
                session.last_activity = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Remove from active instances
                del self._active_instances[browser_id]
                
                _logger.info(
                    "pinchtab_instance_closed",
                    browser_id=browser_id,
                    instance_id=session.instance_id,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                
                return True
            else:
                session.status = ResearchStatus.FAILED
                return False
            
        except Exception as exc:
            _logger.error(
                "pinchtab_instance_close_failed",
                browser_id=browser_id,
                instance_id=session.instance_id,
                error=str(exc),
                duration_ms=int((time.time() - start_time) * 1000),
            )
            session.status = ResearchStatus.FAILED
            return False
            
    async def cleanup_all(self) -> int:
        """Close all active browser instances.
        
        Returns:
            Number of instances successfully closed
        """
        if not self._active_instances:
            return 0
            
        # Cleanup all instance clients
        cleanup_tasks = []
        browser_ids = list(self._active_instances.keys())
        for browser_id in browser_ids:
            if browser_id in self._instance_clients:
                cleanup_tasks.append(self._instance_clients[browser_id].aclose())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            self._instance_clients.clear()
        
        # Cleanup browser instances
        tasks = [self.close_instance(browser_id) for browser_id in browser_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for result in results if result is True)
        
        _logger.info(
            "pinchtab_cleanup_completed",
            total_instances=len(browser_ids),
            successful=successful,
            failed=len(browser_ids) - successful,
        )
        
        return successful
        
    async def navigate(self, browser_id: str, url: str) -> BrowserActionResponse:
        """Navigate browser to URL.
        
        Args:
            browser_id: Browser session identifier
            url: Target URL to navigate
            
        Returns:
            BrowserActionResponse with navigation result
        """
        return await self._execute_browser_action(
            browser_id=browser_id,
            iteration_type=IterationType.NAVIGATE,
            action_data={"action": "navigate", "url": url}
        )
        
    async def extract_text(self, browser_id: str) -> BrowserActionResponse:
        """Extract text content from current page.
        
        Args:
            browser_id: Browser session identifier
            
        Returns:
            BrowserActionResponse with extracted text
        """
        return await self._execute_browser_action(
            browser_id=browser_id,
            iteration_type=IterationType.EXTRACT,
            action_data={"action": "text"}
        )
        
    async def get_snapshot(self, browser_id: str, filter_interactive: bool = True) -> BrowserActionResponse:
        """Get page snapshot with interactive elements.
        
        Args:
            browser_id: Browser session identifier
            filter_interactive: Filter to interactive elements only
            
        Returns:
            BrowserActionResponse with snapshot data
        """
        params = {"filter": "interactive"} if filter_interactive else {}
        return await self._execute_browser_action(
            browser_id=browser_id,
            iteration_type=IterationType.SNAPSHOT,
            action_data={},
            params=params
        )
        
    async def click_element(self, browser_id: str, element_ref: str) -> BrowserActionResponse:
        """Click an element on the page.
        
        Args:
            browser_id: Browser session identifier
            element_ref: Element reference from snapshot
            
        Returns:
            BrowserActionResponse with click result
        """
        return await self._execute_browser_action(
            browser_id=browser_id,
            iteration_type=IterationType.CLICK,
            action_data={"action": "click", "ref": element_ref}
        )
        
    async def fill_input(self, browser_id: str, element_ref: str, value: str) -> BrowserActionResponse:
        """Fill a text input field.
        
        Args:
            browser_id: Browser session identifier
            element_ref: Element reference from snapshot
            value: Text value to fill
            
        Returns:
            BrowserActionResponse with fill result
        """
        return await self._execute_browser_action(
            browser_id=browser_id,
            iteration_type=IterationType.FILL,
            action_data={"action": "fill", "ref": element_ref, "value": value}
        )
        
    async def press_key(self, browser_id: str, element_ref: str, key: str) -> BrowserActionResponse:
        """Press a key on an element.
        
        Args:
            browser_id: Browser session identifier
            element_ref: Element reference from snapshot
            key: Key to press (e.g., "Enter", "Tab")
            
        Returns:
            BrowserActionResponse with key press result
        """
        return await self._execute_browser_action(
            browser_id=browser_id,
            iteration_type=IterationType.PRESS,
            action_data={"action": "press", "ref": element_ref, "key": key}
        )
        
    async def _execute_browser_action(
        self,
        browser_id: str,
        iteration_type: IterationType,
        action_data: dict[str, Any],
        params: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> BrowserActionResponse:
        """Execute a browser action with logging and error handling.
        
        Args:
            browser_id: Browser session identifier
            iteration_type: Type of action being executed
            action_data: Action data for PinchTab API
            params: Additional query parameters
            timeout_seconds: Custom timeout for this action
            
        Returns:
            BrowserActionResponse with action result
        """
        start_time = time.time()
        
        if browser_id not in self._active_instances:
            return BrowserActionResponse(
                success=False,
                browser_id=browser_id,
                iteration_type=iteration_type,
                error_message=f"Browser {browser_id} not found in active instances",
                duration_ms=int((time.time() - start_time) * 1000),
            )
            
        session = self._active_instances[browser_id]
        session.last_activity = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Determine endpoint based on action type
            if iteration_type == IterationType.SNAPSHOT:
                endpoint = f"/instances/{session.tab_id}/snapshot"
                method = "GET"
                request_kwargs = {"params": params}
            else:
                endpoint = f"/instances/{session.tab_id}/action"
                method = "POST"
                request_kwargs = {"json": action_data}
                
            # Set custom timeout if provided
            if timeout_seconds:
                original_timeout = self._instance_clients[browser_id].timeout
                self._instance_clients[browser_id].timeout = httpx.Timeout(timeout_seconds)
                
            try:
                result = await self._make_request(method, endpoint, browser_id=browser_id, **request_kwargs)
                
                # Update session state
                session.actions_completed += 1
                session.status = ResearchStatus.IN_PROGRESS
                
                # Update current URL for navigation actions
                if iteration_type == IterationType.NAVIGATE:
                    session.current_url = action_data.get("url")
                    
                duration_ms = int((time.time() - start_time) * 1000)
                
                _logger.info(
                    "pinchtab_action_completed",
                    browser_id=browser_id,
                    iteration_type=iteration_type,
                    duration_ms=duration_ms,
                    actions_completed=session.actions_completed,
                )
                
                return BrowserActionResponse(
                    success=True,
                    browser_id=browser_id,
                    iteration_type=iteration_type,
                    result_data=result,
                    duration_ms=duration_ms,
                )
                
            finally:
                # Restore original timeout
                if timeout_seconds and browser_id in self._instance_clients:
                    original_timeout = self._instance_clients[browser_id].timeout
                    self._instance_clients[browser_id].timeout = original_timeout
                    
        except Exception as exc:
            session.error_count += 1
            duration_ms = int((time.time() - start_time) * 1000)
            
            _logger.error(
                "pinchtab_action_failed",
                browser_id=browser_id,
                iteration_type=iteration_type,
                error=str(exc),
                duration_ms=duration_ms,
                error_count=session.error_count,
            )
            
            return BrowserActionResponse(
                success=False,
                browser_id=browser_id,
                iteration_type=iteration_type,
                error_message=str(exc),
                duration_ms=duration_ms,
            )
            
    async def list_instances(self) -> list[dict[str, Any]]:
        """List all active PinchTab instances.
        
        Returns:
            List of instance information from PinchTab API
        """
        try:
            # Use default client for global operations
            result = await self._make_request("GET", "/instances")
            return result.get("instances", [])
        except Exception as exc:
            _logger.error("pinchtab_list_instances_failed", error=str(exc))
            return []
            
    async def get_session_info(self, browser_id: str) -> BrowserSession | None:
        """Get information about a browser session.
        
        Args:
            browser_id: Browser session identifier
            
        Returns:
            BrowserSession if found, None otherwise
        """
        return self._active_instances.get(browser_id)
        
    @asynccontextmanager
    async def managed_instance(
        self, 
        headless: bool = True, 
        stealth: bool = True
    ):
        """Context manager for automatic browser instance cleanup.
        
        Args:
            headless: Run browser without UI
            stealth: Enable stealth mode
            
        Yields:
            BrowserSession for the managed instance
        """
        session = await self.create_instance(headless=headless, stealth=stealth)
        try:
            yield session
        finally:
            await self.close_instance(session.browser_id)
            
    async def health_check(self) -> bool:
        """Check if PinchTab service is healthy and responsive.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Use default client for global health check
            await self._make_request("GET", "/instances")
            return True
        except Exception as exc:
            _logger.warning("pinchtab_health_check_failed", error=str(exc))
            return False


# Global service instance
_pinchtab_service: PinchTabService | None = None


async def get_pinchtab_service() -> PinchTabService:
    """Get or create the global PinchTab service instance."""
    global _pinchtab_service
    if _pinchtab_service is None:
        _pinchtab_service = PinchTabService()
    return _pinchtab_service
