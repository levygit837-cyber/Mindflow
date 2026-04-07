"""Advanced automation helpers for LightPanda."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from playwright.async_api import Page, Locator, Frame

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class AutomationHelper:
    """Helpers for advanced browser automation."""

    def __init__(self, page: Page):
        """Initialize the automation helper.

        Args:
            page: Playwright page
        """
        self.page = page
        self._logger = get_logger(__name__)

        # Console logs capture
        self._console_logs: list[dict[str, Any]] = []
        page.on("console", self._handle_console_message)

    def _handle_console_message(self, msg) -> None:
        """Capture console messages.

        Args:
            msg: Console message
        """
        self._console_logs.append(
            {"type": msg.type, "text": msg.text, "timestamp": datetime.utcnow().isoformat()}
        )

    async def fill_form(
        self,
        form_data: dict[str, str],
        submit: bool = True,
        submit_selector: str | None = None,
    ) -> dict[str, Any]:
        """Fill form with data.

        Args:
            form_data: Form field data (field_name -> value)
            submit: Whether to automatically submit
            submit_selector: Custom submit selector

        Returns:
            dict[str, Any]: Form fill results
        """
        results = {"filled": [], "errors": []}

        for field_name, value in form_data.items():
            try:
                # Try multiple selectors
                selectors = [
                    f'[name="{field_name}"]',
                    f'#{field_name}',
                    f'[id="{field_name}"]',
                    f'[data-testid="{field_name}"]',
                ]

                filled = False
                for selector in selectors:
                    try:
                        await self.page.fill(selector, value, timeout=5000)
                        results["filled"].append(field_name)
                        filled = True
                        break
                    except Exception:
                        continue

                if not filled:
                    results["errors"].append(f"Could not fill field: {field_name}")
            except Exception as exc:
                results["errors"].append(f"Error filling {field_name}: {str(exc)}")

        # Submit form if requested
        if submit:
            try:
                if submit_selector:
                    await self.page.click(submit_selector)
                else:
                    # Try to find submit button
                    await self.page.click(
                        'button[type="submit"], input[type="submit"]', timeout=5000
                    )

                # Wait for navigation
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as exc:
                results["errors"].append(f"Submit failed: {str(exc)}")

        return results

    async def click_element(
        self,
        selector: str,
        wait_for_selector: bool = True,
        timeout: int = 5000,
    ) -> bool:
        """Click on element with waiting.

        Args:
            selector: CSS selector
            wait_for_selector: Whether to wait for selector
            timeout: Timeout in milliseconds

        Returns:
            bool: True if successful
        """
        try:
            if wait_for_selector:
                await self.page.wait_for_selector(selector, timeout=timeout)

            await self.page.click(selector, timeout=timeout)
            return True
        except Exception as exc:
            self._logger.error("click_failed", selector=selector, error=str(exc))
            return False

    async def wait_for_dynamic_content(
        self,
        selector: str,
        timeout: int = 30000,
        state: Literal["attached", "detached", "hidden", "visible"] = "visible",
    ) -> bool:
        """Wait for dynamic content.

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds
            state: Element state

        Returns:
            bool: True if successful
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except Exception as exc:
            self._logger.error(
                "wait_for_content_failed", selector=selector, error=str(exc)
            )
            return False

    async def handle_iframe(self, iframe_selector: str, operation: callable) -> Any:
        """Execute operation within iframe.

        Args:
            iframe_selector: Iframe selector
            operation: Operation to execute (receives Frame)

        Returns:
            Any: Operation result
        """
        try:
            frame = self.page.frame_locator(iframe_selector)
            return await operation(frame)
        except Exception as exc:
            self._logger.error(
                "iframe_operation_failed", selector=iframe_selector, error=str(exc)
            )
            raise

    async def handle_shadow_dom(self, selector: str, operation: callable) -> Any:
        """Execute operation in Shadow DOM.

        Args:
            selector: Element selector with shadow root
            operation: Operation to execute

        Returns:
            Any: Operation result

        Note:
            Shadow DOM access is limited in Playwright. This is a simplified
            implementation that uses evaluate to access the shadow root.
        """
        try:
            # Use evaluate to access shadow DOM and execute operation
            result = await self.page.evaluate(
                """(selector) => {
                const element = document.querySelector(selector);
                if (!element || !element.shadowRoot) {
                    return null;
                }
                // Return shadow root for further processing
                return element.shadowRoot.innerHTML;
            }""",
                selector,
            )
            return result
        except Exception as exc:
            self._logger.error(
                "shadow_dom_operation_failed", selector=selector, error=str(exc)
            )
            raise

    async def upload_file(self, selector: str, file_path: str) -> bool:
        """Upload file.

        Args:
            selector: File input selector
            file_path: Path to file

        Returns:
            bool: True if successful
        """
        try:
            await self.page.set_input_files(selector, file_path)
            return True
        except Exception as exc:
            self._logger.error("file_upload_failed", selector=selector, error=str(exc))
            return False

    async def capture_screenshot(
        self,
        selector: str | None = None,
        full_page: bool = False,
        path: str | None = None,
    ) -> bytes:
        """Capture screenshot.

        Args:
            selector: Element selector (optional)
            full_page: Whether to capture full page
            path: Save path (optional)

        Returns:
            bytes: Screenshot bytes
        """
        try:
            if selector:
                element = await self.page.query_selector(selector)
                if element:
                    screenshot = await element.screenshot(path=path)
                else:
                    screenshot = await self.page.screenshot(full_page=full_page, path=path)
            else:
                screenshot = await self.page.screenshot(full_page=full_page, path=path)

            return screenshot
        except Exception as exc:
            self._logger.error("screenshot_failed", selector=selector, error=str(exc))
            raise

    async def generate_pdf(
        self,
        path: str | None = None,
        format: Literal["A4", "Letter"] = "A4",
    ) -> bytes:
        """Generate PDF of page.

        Args:
            path: Save path (optional)
            format: Paper format

        Returns:
            bytes: PDF bytes
        """
        try:
            pdf = await self.page.pdf(
                path=path,
                format=format,
                print_background=True,
            )
            return pdf
        except Exception as exc:
            self._logger.error("pdf_generation_failed", error=str(exc))
            raise

    def get_console_logs(self) -> list[dict[str, Any]]:
        """Get captured console logs.

        Returns:
            list[dict[str, Any]]: Console logs
        """
        return self._console_logs.copy()

    def clear_console_logs(self) -> None:
        """Clear console logs."""
        self._console_logs.clear()
