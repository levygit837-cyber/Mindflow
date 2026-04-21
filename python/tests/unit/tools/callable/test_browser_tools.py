"""Unit tests for browser CallableTools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mindflow_backend.agents.tools.callable.browser import (
    BrowserSearchCallable,
    DeepPageScraperCallable,
    MultiTabSearchCallable,
)
from mindflow_backend.schemas.tools.context import ToolContext


class TestBrowserSearchCallable:
    """Tests for BrowserSearchCallable."""

    @pytest.fixture
    def context(self):
        return ToolContext(root_dir="/tmp", sandbox_mode=False)

    @pytest.mark.asyncio
    async def test_browser_search_success(self, context):
        """Test successful browser search."""
        input_data = BrowserSearchCallable.InputSchema(
            query="test query",
            search_engine="google",
            num_results=5,
            language="en",
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.search_web = AsyncMock(
                return_value={
                    "success": True,
                    "results": [
                        {"title": "Test 1", "url": "http://example.com/1", "snippet": "Snippet 1"},
                        {"title": "Test 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
                    ],
                    "total_results": 2,
                }
            )
            mock_get_tool.return_value = mock_tool

            result = await BrowserSearchCallable.call_fn(input_data, context)

            assert result.success is True
            assert result.data["total_results"] == 2
            assert len(result.data["results"]) == 2
            assert result.data["search_engine"] == "google"
            mock_tool.search_web.assert_called_once_with(
                query="test query",
                search_engine="google",
                num_results=5,
                language="en",
            )

    @pytest.mark.asyncio
    async def test_browser_search_failure(self, context):
        """Test browser search failure."""
        input_data = BrowserSearchCallable.InputSchema(
            query="test query",
            search_engine="google",
            num_results=5,
            language="en",
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.search_web = AsyncMock(
                return_value={"success": False, "error": "Search failed"}
            )
            mock_get_tool.return_value = mock_tool

            result = await BrowserSearchCallable.call_fn(input_data, context)

            assert result.success is False
            assert result.error == "Search failed"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_browser_search_exception(self, context):
        """Test browser search exception handling."""
        input_data = BrowserSearchCallable.InputSchema(
            query="test query",
            search_engine="google",
            num_results=5,
            language="en",
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.search_web = AsyncMock(side_effect=Exception("Test exception"))
            mock_get_tool.return_value = mock_tool

            result = await BrowserSearchCallable.call_fn(input_data, context)

            assert result.success is False
            assert "Test exception" in result.error
            assert result.metadata.get("error_type") == "Exception"


class TestDeepPageScraperCallable:
    """Tests for DeepPageScraperCallable."""

    @pytest.fixture
    def context(self):
        return ToolContext(root_dir="/tmp", sandbox_mode=False)

    @pytest.mark.asyncio
    async def test_deep_page_scraper_success(self, context):
        """Test successful deep page scraping."""
        input_data = DeepPageScraperCallable.InputSchema(
            url="http://example.com",
            scroll_depth=5,
            scroll_wait_ms=500,
            extract_links=True,
            wait_for_load=3000,
            max_content_length=50000,
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.scrape_page = AsyncMock(
                return_value={
                    "success": True,
                    "title": "Test Page",
                    "content": "This is test content that is long enough to be meaningful",
                    "description": "Test description",
                    "timestamp": "2024-01-01T00:00:00",
                }
            )
            mock_get_tool.return_value = mock_tool

            result = await DeepPageScraperCallable.call_fn(input_data, context)

            assert result.success is True
            assert result.data["url"] == "http://example.com"
            assert result.data["title"] == "Test Page"
            assert result.data["word_count"] > 0
            assert result.data["scroll_iterations"] == 5
            assert result.data["content_depth"] == "medium"
            assert result.data["links"]["total"] == 0
            mock_tool.scrape_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_page_scraper_content_truncation(self, context):
        """Test content truncation based on max_content_length."""
        input_data = DeepPageScraperCallable.InputSchema(
            url="http://example.com",
            max_content_length=100,
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.scrape_page = AsyncMock(
                return_value={
                    "success": True,
                    "title": "Test Page",
                    "content": "A" * 500,  # Long content
                    "timestamp": "2024-01-01T00:00:00",
                }
            )
            mock_get_tool.return_value = mock_tool

            result = await DeepPageScraperCallable.call_fn(input_data, context)

            assert result.success is True
            assert len(result.data["content"]) <= 100

    @pytest.mark.asyncio
    async def test_deep_page_scraper_failure(self, context):
        """Test deep page scraper failure."""
        input_data = DeepPageScraperCallable.InputSchema(
            url="http://example.com",
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.scrape_page = AsyncMock(
                return_value={"success": False, "error": "Scraping failed"}
            )
            mock_get_tool.return_value = mock_tool

            result = await DeepPageScraperCallable.call_fn(input_data, context)

            assert result.success is False
            assert result.error == "Scraping failed"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_deep_page_scraper_scroll_depth_validation(self):
        """Test scroll depth parameter validation."""
        # Test minimum value
        input_min = DeepPageScraperCallable.InputSchema(
            url="http://example.com",
            scroll_depth=1,
        )
        assert input_min.scroll_depth == 1

        # Test maximum value
        input_max = DeepPageScraperCallable.InputSchema(
            url="http://example.com",
            scroll_depth=50,
        )
        assert input_max.scroll_depth == 50

    @pytest.mark.asyncio
    async def test_deep_page_scraper_with_images(self, context):
        """Test scraping with image metadata extraction."""
        input_data = DeepPageScraperCallable.InputSchema(
            url="http://example.com",
            include_images=True,
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.scrape_page = AsyncMock(
                return_value={
                    "success": True,
                    "title": "Test Page",
                    "content": "Test content",
                    "images_count": 5,
                    "timestamp": "2024-01-01T00:00:00",
                }
            )
            mock_get_tool.return_value = mock_tool

            result = await DeepPageScraperCallable.call_fn(input_data, context)

            assert result.success is True
            assert result.data["metadata"]["images_count"] == 5


class TestMultiTabSearchCallable:
    """Tests for MultiTabSearchCallable."""

    @pytest.fixture
    def context(self):
        return ToolContext(root_dir="/tmp", sandbox_mode=False)

    @pytest.mark.asyncio
    async def test_multi_tab_search_success(self, context):
        """Test successful multi-tab search."""
        input_data = MultiTabSearchCallable.InputSchema(
            queries=["query 1", "query 2", "query 3"],
            sources_per_query=3,
            search_engine="google",
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.search_web = AsyncMock(
                side_effect=[
                    {
                        "success": True,
                        "results": [
                            {"title": f"Result {i}", "url": f"http://example.com/{i}", "snippet": f"Snippet {i}"}
                            for i in range(3)
                        ],
                    },
                    {
                        "success": True,
                        "results": [
                            {"title": f"Result {i}", "url": f"http://example.com/{i}", "snippet": f"Snippet {i}"}
                            for i in range(3, 6)
                        ],
                    },
                    {
                        "success": True,
                        "results": [
                            {"title": f"Result {i}", "url": f"http://example.com/{i}", "snippet": f"Snippet {i}"}
                            for i in range(6, 9)
                        ],
                    },
                ]
            )
            mock_get_tool.return_value = mock_tool

            result = await MultiTabSearchCallable.call_fn(input_data, context)

            assert result.success is True
            assert result.data["total_results"] == 9
            assert result.data["queries_executed"] == 3
            assert result.data["successful_queries"] == 3
            assert result.data["failed_queries"] == 0

    @pytest.mark.asyncio
    async def test_multi_tab_search_partial_failure(self, context):
        """Test multi-tab search with partial failures."""
        input_data = MultiTabSearchCallable.InputSchema(
            queries=["query 1", "query 2", "query 3"],
            sources_per_query=3,
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.search_web = AsyncMock(
                side_effect=[
                    {
                        "success": True,
                        "results": [{"title": "Result 1", "url": "http://example.com/1", "snippet": "Snippet 1"}],
                    },
                    {"success": False, "error": "Search failed"},
                    {
                        "success": True,
                        "results": [{"title": "Result 2", "url": "http://example.com/2", "snippet": "Snippet 2"}],
                    },
                ]
            )
            mock_get_tool.return_value = mock_tool

            result = await MultiTabSearchCallable.call_fn(input_data, context)

            assert result.success is True
            assert result.data["total_results"] == 2
            assert result.data["successful_queries"] == 2
            assert result.data["failed_queries"] == 1

    @pytest.mark.asyncio
    async def test_multi_tab_search_exception_handling(self, context):
        """Test multi-tab search with exceptions."""
        input_data = MultiTabSearchCallable.InputSchema(
            queries=["query 1", "query 2"],
            sources_per_query=3,
        )

        with patch(
            "mindflow_backend.agents.tools.callable.browser.get_lightpanda_browser_search_tool"
        ) as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.search_web = AsyncMock(
                side_effect=[
                    {"success": True, "results": [{"title": "Result 1", "url": "http://example.com/1"}]},
                    Exception("Search exception"),
                ]
            )
            mock_get_tool.return_value = mock_tool

            result = await MultiTabSearchCallable.call_fn(input_data, context)

            assert result.success is True
            assert result.data["total_results"] == 1
            assert result.data["successful_queries"] == 1
            assert result.data["failed_queries"] == 1

    @pytest.mark.asyncio
    async def test_multi_tab_search_validation(self):
        """Test input validation."""
        # Test minimum queries
        input_min = MultiTabSearchCallable.InputSchema(
            queries=["query 1"],
            sources_per_query=1,
        )
        assert len(input_min.queries) == 1

        # Test maximum queries
        input_max = MultiTabSearchCallable.InputSchema(
            queries=[f"query {i}" for i in range(10)],
            sources_per_query=1,
        )
        assert len(input_max.queries) == 10

        # Test sources_per_query validation
        input_sources = MultiTabSearchCallable.InputSchema(
            queries=["query 1"],
            sources_per_query=20,
        )
        assert input_sources.sources_per_query == 20
