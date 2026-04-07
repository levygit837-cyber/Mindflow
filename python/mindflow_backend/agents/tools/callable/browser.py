"""Browser tools - Callable pattern (Phase 2).

These tools provide browser automation capabilities including search,
deep page scraping with scroll, and multi-tab search.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, HttpUrl

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.callable import (
    CallableTool,
    CallableToolResult,
    ProgressCallback,
    ToolContext,
    _callable_result_from_dict,
    build_readonly_tool,
)
from mindflow_backend.agents.tools.web.lightpanda_browser_search import (
    get_lightpanda_browser_search_tool,
)

_logger = get_logger(__name__)


def _callable_result_from_dict(
    data: dict[str, Any] | None,
    success: bool,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Convert a result dict to a callable tool result."""
    if success:
        return CallableToolResult(data=data, success=True, metadata=metadata or {})

    result_metadata = dict(metadata or {})
    return CallableToolResult(
        data=None,
        success=False,
        error=error or "Unknown error",
        metadata=result_metadata,
    )


# ---------------------------------------------------------------------------
# BrowserSearchCallable - Priority 6
# ---------------------------------------------------------------------------


class BrowserSearchInput(BaseModel):
    """Input schema for BrowserSearchCallable."""

    query: str = Field(description="Search query string")
    search_engine: str = Field(
        default="google",
        description="Search engine: google, bing, duckduckgo"
    )
    num_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of search results to return"
    )
    language: str = Field(
        default="en",
        description="Language code (e.g., en, pt, es)"
    )


async def browser_search_impl(
    input: BrowserSearchInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute web search through LightPanda browser service."""
    try:
        # Get LightPanda browser search tool
        browser_tool = get_lightpanda_browser_search_tool()

        # Execute search
        result = await browser_tool.search_web(
            query=input.query,
            search_engine=input.search_engine,
            num_results=input.num_results,
            language=input.language,
        )

        if result.get("success"):
            return _callable_result_from_dict(
                data={
                    "results": result.get("results", []),
                    "total_results": result.get("total_results", 0),
                    "search_engine": input.search_engine,
                },
                success=True,
                metadata={"operation": "browser_search"},
            )
        else:
            return _callable_result_from_dict(
                data=None,
                success=False,
                error=result.get("error", "Search failed"),
                metadata={"operation": "browser_search"},
            )

    except Exception as e:
        _logger.error("browser_search_failed", error=str(e), query=getattr(input, 'query', 'unknown'), exc_info=True)
        return _callable_result_from_dict(
            data=None,
            success=False,
            error=str(e),
            metadata={"operation": "browser_search", "error_type": type(e).__name__},
        )


BrowserSearchCallable = build_readonly_tool(
    name="browser_search",
    description=(
        "Web search using LightPanda browser automation. "
        "Executes real browser-based search with support for multiple search engines. "
        "Returns structured search results with titles, URLs, and snippets. "
        "Uses Chrome DevTools Protocol for browser control. "
        "Concurrent-safe: can perform multiple searches in parallel."
    ),
    input_schema=BrowserSearchInput,
    call_fn=browser_search_impl,
    is_concurrency_safe=True,
    interrupt_behavior="cancel",
)


# ---------------------------------------------------------------------------
# DeepPageScraperCallable - Priority 6 (Advanced scraping with scroll)
# ---------------------------------------------------------------------------


class DeepPageScraperInput(BaseModel):
    """Input schema for DeepPageScraperCallable."""

    url: str = Field(description="URL to scrape completely")
    scroll_depth: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of scroll iterations"
    )
    scroll_wait_ms: int = Field(
        default=500,
        ge=100,
        le=5000,
        description="Wait time between scrolls in milliseconds"
    )
    extract_links: bool = Field(
        default=True,
        description="Extract all clickable links from the page"
    )
    max_content_length: int = Field(
        default=50000,
        ge=1000,
        le=200000,
        description="Maximum content characters to extract"
    )
    include_images: bool = Field(
        default=False,
        description="Extract image metadata"
    )


async def deep_page_scraper_impl(
    input: DeepPageScraperInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute deep page scraping with scroll and link mapping through LightPanda."""
    try:
        # Get LightPanda browser search tool
        browser_tool = get_lightpanda_browser_search_tool()

        # Report progress
        if on_progress:
            await on_progress(0.1, "Navigating to URL...")

        # Execute deep scrape with scroll
        result = await browser_tool.scrape_page(
            url=input.url,
            selector=None,  # Extract full page
            wait_for=None,
            screenshot=False,
            scroll_depth=input.scroll_depth,
            scroll_wait_ms=input.scroll_wait_ms,
            extract_links=input.extract_links,
            max_content_length=input.max_content_length,
            include_images=input.include_images,
        )

        # The scrape_page now returns the data directly (not wrapped in "success")
        content = result.get("content", "")
        title = result.get("title", "")
        
        # Use the links data from scrape_page if extract_links was enabled
        links_data = result.get("links", {})
        if not links_data:
            links_data = {
                "total": 0,
                "internal": [],
                "external": [],
                "navigation": [],
                "content": [],
                "all": [],
            }
        
        # Use the images data from scrape_page if include_images was enabled
        images_data = result.get("images", {})

        # Use metrics from scrape_page (they are already calculated)
        word_count = result.get("word_count", 0)
        reading_time = result.get("reading_time_minutes", 0)
        scroll_iterations = result.get("scroll_iterations", input.scroll_depth)
        content_depth = result.get("content_depth", "medium")

        return _callable_result_from_dict(
            data={
                "url": input.url,
                "title": title,
                "content": content,
                "word_count": word_count,
                "reading_time_minutes": reading_time,
                "extracted_at": result.get("metadata", {}).get("timestamp"),
                "scroll_iterations": scroll_iterations,
                "content_depth": content_depth,
                "content_changes_detected": result.get("content_changes_detected", 0),
                "links": links_data,
                "images": images_data,
                "metadata": {
                    "description": result.get("metadata", {}).get("description", ""),
                    "load_time_seconds": result.get("metadata", {}).get("load_time_seconds", 0),
                    "content_length": result.get("metadata", {}).get("content_length", 0),
                },
            },
            success=True,
            metadata={"operation": "deep_page_scrape"},
        )

    except Exception as e:
        _logger.error("deep_page_scrape_failed", error=str(e), url=getattr(input, 'url', 'unknown'), exc_info=True)
        return _callable_result_from_dict(
            data=None,
            success=False,
            error=str(e),
            metadata={"operation": "deep_page_scrape", "error_type": type(e).__name__},
        )


DeepPageScraperCallable = build_readonly_tool(
    name="deep_page_scraper",
    description=(
        "Advanced web page scraper with automatic scrolling and link mapping. "
        "Scrolls to end of page to capture lazy-loaded content, extracts all clickable links, "
        "categorizes links (internal/external, navigation/content), and detects dynamic content. "
        "Returns complete page content with metadata, link structure, and scraping metrics. "
        "Uses Chrome DevTools Protocol via LightPanda. "
        "Concurrent-safe: can scrape multiple pages in parallel."
    ),
    input_schema=DeepPageScraperInput,
    call_fn=deep_page_scraper_impl,
    is_concurrency_safe=True,
    interrupt_behavior="cancel",
)


# ---------------------------------------------------------------------------
# MultiTabSearchCallable - Priority 6 (Parallel multi-tab search)
# ---------------------------------------------------------------------------


class MultiTabSearchInput(BaseModel):
    """Input schema for MultiTabSearchCallable."""

    queries: list[str] = Field(
        min_length=1,
        max_length=10,
        description="List of search queries to execute in parallel"
    )
    sources_per_query: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of sources to find per query"
    )
    search_engine: str = Field(
        default="google",
        description="Search engine: google, bing, duckduckgo"
    )


async def multi_tab_search_impl(
    input: MultiTabSearchInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute parallel multi-tab search through LightPanda TabManager."""
    try:
        import asyncio

        # Get LightPanda browser search tool
        browser_tool = get_lightpanda_browser_search_tool()

        # Execute searches in parallel
        tasks = []
        for query in input.queries:
            task = browser_tool.search_web(
                query=query,
                search_engine=input.search_engine,
                num_results=input.sources_per_query,
            )
            tasks.append(task)

        # Wait for all searches to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_results = []
        successful_queries = 0
        failed_queries = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _logger.error(f"Query {i} failed: {result}")
                failed_queries += 1
            elif result.get("success"):
                all_results.extend(result.get("results", []))
                successful_queries += 1
            else:
                failed_queries += 1

        return _callable_result_from_dict(
            data={
                "results": all_results,
                "total_results": len(all_results),
                "queries_executed": len(input.queries),
                "successful_queries": successful_queries,
                "failed_queries": failed_queries,
                "search_engine": input.search_engine,
            },
            success=True,
            metadata={"operation": "multi_tab_search"},
        )

    except Exception as e:
        _logger.error(f"Multi-tab search failed: {e}", exc_info=True)
        return _callable_result_from_dict(
            data=None,
            success=False,
            error=str(e),
            metadata={"operation": "multi_tab_search", "error_type": type(e).__name__},
        )


MultiTabSearchCallable = build_readonly_tool(
    name="multi_tab_search",
    description=(
        "Parallel multi-tab search using LightPanda TabManager. "
        "Executes multiple search queries simultaneously in different browser tabs, "
        "aggregating results for comprehensive research. Supports up to 10 parallel queries. "
        "Ideal for exploring multiple aspects of a research topic concurrently. "
        "Uses Chrome DevTools Protocol with TabManager for efficient parallel execution. "
        "Concurrent-safe: designed for parallel execution."
    ),
    input_schema=MultiTabSearchInput,
    call_fn=multi_tab_search_impl,
    is_concurrency_safe=True,
    interrupt_behavior="cancel",
)


# Re-export existing WebScraperCallable from web.py for convenience
from mindflow_backend.agents.tools.callable.web import WebScraperCallable

__all__ = [
    "BrowserSearchCallable",
    "WebScraperCallable",
    "DeepPageScraperCallable",
    "MultiTabSearchCallable",
]
