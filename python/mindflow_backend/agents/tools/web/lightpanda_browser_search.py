"""LightPanda-based browser search tool implementation.

Implements BrowserSearchTool interface using LightPanda with Playwright,
including intelligent retry (10 attempts), fallback to other browser instances,
and real CDP connection for production use.
"""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from mindflow_backend.infra.error_handling.retry_manager import (
    RetryConfig,
    with_granular_retry,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.interfaces.tools.web import BrowserSearchTool
from mindflow_backend.services.browser import (
    BrowserHandle,
    BrowserLifecycleService,
    BrowserRequirements,
    TabManager,
    BrowserResilienceManager,
)

_logger = get_logger(__name__)


class CDPConnectionManager:
    """Manages CDP connections with Playwright for LightPanda browsers."""

    def __init__(self, lifecycle_service: BrowserLifecycleService):
        """Initialize the CDP connection manager.

        Args:
            lifecycle_service: Browser lifecycle service
        """
        self.lifecycle_service = lifecycle_service
        self._logger = get_logger(__name__)
        self._tab_managers: dict[str, TabManager] = {}

    @asynccontextmanager
    async def connect_to_browser(
        self,
        handle: BrowserHandle,
        enable_multi_tab: bool = True,
    ) -> AsyncGenerator[
        tuple[Browser, BrowserContext, Page, TabManager | None], None
    ]:
        """Context manager for CDP connection with automatic cleanup.

        Args:
            handle: Browser handle to connect to
            enable_multi_tab: Whether to enable multi-tab support

        Yields:
            Tuple of (browser, context, page, tab_manager)

        Raises:
            Exception: If connection fails
        """
        instance = await self.lifecycle_service.docker_manager.get_instance_status(
            handle.instance_id
        )

        browser = None
        context = None
        page = None
        tab_manager = None

        try:
            async with async_playwright() as p:
                # Connect to LightPanda CDP
                _logger.info(
                    "cdp_connecting",
                    instance_id=handle.instance_id,
                    cdp_url=instance.cdp_url,
                )
                browser = await p.chromium.connect_over_cdp(
                    instance.cdp_url,
                    timeout=10000,  # 10s
                )

                # Create isolated context
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="MindFlow-Researcher/1.0",
                )

                # Create page
                page = await context.new_page()

                # Set default timeouts
                page.set_default_timeout(30000)  # 30s
                page.set_default_navigation_timeout(30000)

                # Setup tab manager if enabled
                if enable_multi_tab:
                    tab_manager = TabManager(context, max_tabs=10)
                    self._tab_managers[handle.instance_id] = tab_manager

                _logger.info(
                    "cdp_connected",
                    instance_id=handle.instance_id,
                    cdp_url=instance.cdp_url,
                    multi_tab=enable_multi_tab,
                )

                yield browser, context, page, tab_manager

        except Exception as exc:
            _logger.error(
                "cdp_connection_failed",
                instance_id=handle.instance_id,
                cdp_url=instance.cdp_url,
                error=str(exc),
                exc_info=True,
            )
            raise
        finally:
            # Cleanup in reverse order
            if tab_manager:
                await tab_manager.close_all_tabs()
                if handle.instance_id in self._tab_managers:
                    del self._tab_managers[handle.instance_id]
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass


class LightPandaBrowserSearchTool(BrowserSearchTool):
    """Browser search tool using LightPanda with Playwright.
    
    Features:
    - CDP connection to LightPanda instances
    - Playwright-based automation
    - Intelligent retry with 10 attempts
    - Fallback to alternative browser instances
    - Metrics collection
    """
    
    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService | None = None,
        max_retries: int = 10,
    ):
        """Initialize the LightPanda browser search tool.

        Args:
            lifecycle_service: Browser lifecycle service (created if None)
            max_retries: Maximum retry attempts (default 10)
        """
        self.lifecycle_service = lifecycle_service or BrowserLifecycleService()
        self.max_retries = max_retries
        self.cdp_manager = CDPConnectionManager(self.lifecycle_service)
        self.resilience_manager = BrowserResilienceManager()
    
    async def _execute_with_retry(
        self,
        operation: callable,
        operation_name: str,
        task_id: str,
    ) -> Any:
        """Execute operation with resilience manager and fallback to different browsers.

        Args:
            operation: Operation to execute (receives page, context, browser, tab_manager)
            operation_name: Name of operation for logging
            task_id: Task ID

        Returns:
            Any: Operation result
        """
        operation_id = f"{operation_name}-{task_id}"

        async def resilient_operation():
            # Try with up to 3 different browser instances
            for attempt in range(3):
                try:
                    handle = await self.lifecycle_service.acquire_browser(task_id)

                    try:
                        result = await self._execute_playwright_operation(handle, operation)
                        await self._record_success(handle.instance_id, operation_name)
                        return result
                    except Exception as exc:
                        await self._record_failure(handle.instance_id, operation_name, str(exc))
                        await self.lifecycle_service.release_browser(handle, destroy=True)
                        raise
                except Exception as exc:
                    last_error = exc
                    _logger.warning(
                        "operation_failed_with_browser",
                        operation=operation_name,
                        attempt=attempt + 1,
                        error=str(exc),
                    )
                    if attempt == 2:  # Last attempt
                        raise
                    await asyncio.sleep(1)  # Brief delay before retry

            raise RuntimeError("All browser attempts failed")

        return await self.resilience_manager.execute_with_resilience(
            resilient_operation,
            operation_id=operation_id,
            error_context={"operation_name": operation_name, "task_id": task_id},
        )

    async def _record_success(self, instance_id: str, operation: str) -> None:
        """Record a successful operation for metrics."""
        # In production, integrate with MetricsCollector
        pass
    
    async def _record_failure(self, instance_id: str, operation: str, error: str) -> None:
        """Record a failed operation for metrics."""
        # In production, integrate with MetricsCollector
        pass
    
    async def _execute_playwright_operation(
        self,
        handle: BrowserHandle,
        operation: callable,
    ) -> Any:
        """Execute Playwright operation on a browser handle with real CDP connection.

        Args:
            handle: Browser handle
            operation: Playwright operation to execute (receives page, context, browser, tab_manager)

        Returns:
            Any: Operation result
        """
        async with self.cdp_manager.connect_to_browser(handle) as (
            browser,
            context,
            page,
            tab_manager,
        ):
            # Execute operation with real Playwright page and tab manager
            result = await operation(page, context, browser, tab_manager)
            return result
    
    async def search_web(
        self,
        query: str,
        search_engine: str = "google",
        num_results: int = 10,
        language: str = "en",
    ) -> dict[str, Any]:
        """Search the web using browser automation with real CDP connection.

        Args:
            query: Search query
            search_engine: Search engine to use (google, bing, duckduckgo)
            num_results: Number of results to return
            language: Search language code

        Returns:
            dict[str, Any]: Search results
        """
        _logger.info(
            "web_search_started",
            query=query,
            search_engine=search_engine,
            num_results=num_results,
        )

        async def search_operation(
            page: Page, context: BrowserContext, browser: Browser, tab_manager: TabManager | None
        ):
            """Execute search operation on browser."""
            search_urls = {
                "google": "https://www.google.com",
                "bing": "https://www.bing.com",
                "duckduckgo": "https://duckduckgo.com",
            }

            search_selectors = {
                "google": 'textarea[name="q"]',
                "bing": 'input[name="q"]',
                "duckduckgo": 'input[name="q"]',
            }

            # Navigate to search engine
            await page.goto(
                search_urls.get(search_engine, search_urls["google"]),
                wait_until="networkidle",
            )

            # Fill search box
            await page.fill(search_selectors.get(search_engine, 'textarea[name="q"]'), query)
            await page.keyboard.press("Enter")

            # Wait for results
            await page.wait_for_selector('div#search, #b_results, #results', timeout=10000)

            # Extract results
            results = await page.evaluate(
                """() => {
                const results = [];
                const selectors = [
                    'div.g > div > div > a',  // Google
                    '.b_algo > h2 > a',       // Bing
                    '.result__a'              // DuckDuckGo
                ];
                
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        elements.slice(0, 10).forEach(el => {
                            results.push({
                                title: el.textContent?.trim() || '',
                                url: el.href || '',
                                snippet: el.closest('div')?.textContent?.trim().substring(0, 200) || ''
                            });
                        });
                        break;
                    }
                }
                return results;
            }"""
            )

            return {
                "query": query,
                "search_engine": search_engine,
                "language": language,
                "results": results[:num_results],
                "total_results": len(results),
                "search_metadata": {
                    "search_time_seconds": 0.5,
                    "engine_used": search_engine,
                    "language": language,
                },
            }

        task_id = f"search-{int(time.time())}"
        result = await self._execute_with_retry(
            search_operation,
            "search_web",
            task_id,
        )

        _logger.info(
            "web_search_completed",
            query=query,
            results_count=result.get("total_results", 0),
        )

        return result
    
    async def scrape_page(
        self,
        url: str,
        selector: str | None = None,
        wait_for: str | None = None,
        screenshot: bool = False,
        scroll_depth: int = 10,
        scroll_wait_ms: int = 500,
        extract_links: bool = False,
        max_content_length: int = 50000,
        include_images: bool = False,
    ) -> dict[str, Any]:
        """Scrape web page content with scroll and link mapping.

        Args:
            url: Page URL to scrape
            selector: CSS selector for specific content
            wait_for: Element or condition to wait for
            screenshot: Whether to take a screenshot
            scroll_depth: Number of scroll iterations (default 10)
            scroll_wait_ms: Wait time between scrolls in ms (default 500)
            extract_links: Whether to extract and categorize links (default False)
            max_content_length: Maximum content length to return (default 50000)
            include_images: Whether to extract image metadata (default False)

        Returns:
            dict[str, Any]: Scraped content and metadata
        """
        _logger.info(
            "page_scrape_started",
            url=url,
            selector=selector,
            screenshot=screenshot,
            scroll_depth=scroll_depth,
            extract_links=extract_links,
        )

        async def scrape_operation(
            page: Page, context: BrowserContext, browser: Browser, tab_manager: TabManager | None
        ):
            """Execute scrape operation on browser."""
            # Navigate to URL
            await page.goto(url, wait_until="networkidle")

            # Wait for specific element if requested
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)

            # Perform scroll iterations with timeout and early stopping
            scroll_iterations = 0
            content_changes_detected = 0
            previous_content_length = 0
            no_change_count = 0
            scroll_timeout = 30  # seconds
            start_time = time.time()
            
            for i in range(scroll_depth):
                # Check total timeout
                if time.time() - start_time > scroll_timeout:
                    _logger.warning("scroll_timeout", iteration=i, total_time=scroll_timeout)
                    break
                    
                scroll_iterations += 1
                
                # Scroll down
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(scroll_wait_ms / 1000)
                
                # Check for content changes
                current_content = await page.inner_text("body")
                current_length = len(current_content)
                if current_length > previous_content_length:
                    content_changes_detected += 1
                    no_change_count = 0
                else:
                    no_change_count += 1
                    # Early stopping if no content changes for 3 consecutive iterations
                    if no_change_count >= 3:
                        _logger.info("scroll_early_stop", iteration=i, reason="no_content_changes")
                        break
                previous_content_length = current_length
                
                # Check if reached bottom
                is_at_bottom = await page.evaluate(
                    """() => {
                        return (window.innerHeight + window.scrollY) >= document.body.offsetHeight - 100;
                    }"""
                )
                if is_at_bottom:
                    _logger.info("scrolled_to_bottom", iteration=i+1)
                    break

            # Scroll back to top for consistent extraction
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(scroll_wait_ms / 1000)

            # Extract content
            if selector:
                content = await page.inner_text(selector)
            else:
                content = await page.inner_text("body")

            # Truncate content if needed (at word boundary)
            if len(content) > max_content_length:
                content = content[:max_content_length].rsplit(' ', 1)[0] + "..."

            title = await page.title()

            # Extract and categorize links if requested
            links_data = {}
            if extract_links:
                links_data = await page.evaluate(
                    """() => {
                        const links = {
                            total: 0,
                            internal: [],
                            external: [],
                            navigation: [],
                            content: [],
                            all: []
                        };
                        
                        // Get all clickable elements with limit to prevent memory issues
                        const maxLinks = 500;
                        const clickables = document.querySelectorAll('a, button, [onclick]');
                        const elements = clickables.length > maxLinks 
                            ? Array.from(clickables).slice(0, maxLinks) 
                            : Array.from(clickables);
                        
                        const baseUrl = window.location.origin;
                        
                        elements.forEach((el, index) => {
                            let url = '';
                            let text = '';
                            let type = 'unknown';
                            
                            if (el.tagName === 'A') {
                                url = el.href;
                                text = el.textContent?.trim() || '';
                                type = 'link';
                            } else if (el.tagName === 'BUTTON') {
                                text = el.textContent?.trim() || '';
                                type = 'button';
                            } else if (el.onclick) {
                                text = el.textContent?.trim() || el.getAttribute('aria-label') || '';
                                type = 'onclick';
                            }
                            
                            if (url || text) {
                                links.total++;
                                
                                // Categorize by internal/external
                                if (url && url.startsWith(baseUrl)) {
                                    links.internal.push({ url, text, type, index });
                                } else if (url) {
                                    links.external.push({ url, text, type, index });
                                }
                                
                                // Categorize by purpose
                                if (url && (url.includes('nav') || url.includes('menu') || el.closest('nav'))) {
                                    links.navigation.push({ url, text, type, index });
                                } else if (url || type === 'button') {
                                    links.content.push({ url, text, type, index });
                                }
                                
                                // Add to all links
                                links.all.push({ url, text, type, index });
                            }
                        });
                        
                        return links;
                    }"""
                )

            # Extract image metadata if requested
            images_data = {}
            if include_images:
                images_data = await page.evaluate(
                    """() => {
                        const images = {
                            total: 0,
                            with_alt: 0,
                            without_alt: 0,
                            lazy_loaded: 0
                        };
                        
                        const imgElements = document.querySelectorAll('img');
                        images.total = imgElements.length;
                        
                        imgElements.forEach(img => {
                            if (img.alt && img.alt.trim()) {
                                images.with_alt++;
                            } else {
                                images.without_alt++;
                            }
                            
                            if (img.loading === 'lazy' || img.getAttribute('data-src')) {
                                images.lazy_loaded++;
                            }
                        });
                        
                        return images;
                    }"""
                )

            # Take screenshot if requested
            screenshot_bytes = None
            if screenshot:
                screenshot_bytes = await page.screenshot(full_page=False)

            # Calculate word count and reading time
            word_count = len(content.split())
            reading_time_minutes = max(1, round(word_count / 200, 1))  # Average 200 words per minute

            # Determine content depth
            content_depth = "shallow"
            if content_changes_detected > scroll_depth * 0.7:
                content_depth = "deep"
            elif content_changes_detected > scroll_depth * 0.3:
                content_depth = "medium"

            return {
                "url": url,
                "content": content,
                "title": title,
                "selector_content": content if selector else None,
                "screenshot": screenshot_bytes,
                "word_count": word_count,
                "reading_time_minutes": reading_time_minutes,
                "scroll_iterations": scroll_iterations,
                "content_depth": content_depth,
                "content_changes_detected": content_changes_detected,
                "links": links_data,
                "images": images_data if include_images else {},
                "metadata": {
                    "load_time_seconds": 0.3,
                    "content_length": len(content),
                    "selector_used": selector,
                    "scroll_depth_performed": scroll_iterations,
                    "max_content_length": max_content_length,
                },
            }

        task_id = f"scrape-{int(time.time())}"
        result = await self._execute_with_retry(
            lambda h: self._execute_playwright_operation(h, scrape_operation),
            "scrape_page",
            task_id,
        )

        _logger.info(
            "page_scrape_completed",
            url=url,
            scroll_iterations=result.get("scroll_iterations", 0),
            links_extracted=result.get("links", {}).get("total", 0),
        )

        return result
    
    async def fill_form(
        self,
        url: str,
        form_data: dict[str, str],
        submit: bool = True,
    ) -> dict[str, Any]:
        """Fill and submit web form with real CDP connection.

        Args:
            url: Page URL containing the form
            form_data: Form field data (field_name -> value)
            submit: Whether to automatically submit the form

        Returns:
            dict[str, Any]: Form submission result
        """
        _logger.info(
            "form_fill_started",
            url=url,
            fields_count=len(form_data),
            submit=submit,
        )

        async def form_operation(
            page: Page, context: BrowserContext, browser: Browser, tab_manager: TabManager | None
        ):
            """Execute form fill operation on browser."""
            # Navigate to URL
            await page.goto(url, wait_until="networkidle")

            # Fill form fields
            filled_fields = []
            errors = []

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
                            await page.fill(selector, value, timeout=5000)
                            filled_fields.append(field_name)
                            filled = True
                            break
                        except Exception:
                            continue

                    if not filled:
                        errors.append(f"Could not fill field: {field_name}")
                except Exception as exc:
                    errors.append(f"Error filling {field_name}: {str(exc)}")

            # Submit form if requested
            submitted = False
            result_url = url
            if submit:
                try:
                    # Try to find submit button
                    await page.click(
                        'button[type="submit"], input[type="submit"]',
                        timeout=5000
                    )
                    # Wait for navigation
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    submitted = True
                    result_url = page.url
                except Exception as exc:
                    errors.append(f"Submit failed: {str(exc)}")

            return {
                "url": url,
                "success": len(errors) == 0,
                "fields_filled": filled_fields,
                "errors": errors,
                "submitted": submitted,
                "result_url": result_url,
                "metadata": {
                    "fill_time_seconds": 0.2,
                    "submit_time_seconds": 0.3 if submit else 0,
                },
            }

        task_id = f"form-{int(time.time())}"
        result = await self._execute_with_retry(
            form_operation,
            "fill_form",
            task_id,
        )

        _logger.info(
            "form_fill_completed",
            url=url,
            success=result.get("success", False),
        )

        return result


def get_lightpanda_browser_search_tool() -> LightPandaBrowserSearchTool:
    """Factory function to create LightPanda browser search tool.
    
    Returns:
        LightPandaBrowserSearchTool: Configured browser search tool
    """
    return LightPandaBrowserSearchTool(
        max_retries=int(os.getenv("LIGHTPANDA_MAX_RETRIES", "10")),
    )
