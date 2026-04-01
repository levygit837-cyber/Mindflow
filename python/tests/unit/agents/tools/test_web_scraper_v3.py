"""Unit tests for WebScraperToolV3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from mindflow_backend.agents.tools.web.web_scraper_v3 import (
    WebScraperInput,
    WebScraperToolV3,
    web_scraper_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.fixture
def mock_html_response():
    """Mock HTML response."""
    return """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Title</h1>
            <p class="content">Paragraph 1</p>
            <p class="content">Paragraph 2</p>
            <a href="/relative">Relative Link</a>
            <a href="https://example.com/absolute">Absolute Link</a>
            <img src="/image.jpg" alt="Test Image">
            <script>console.log('test');</script>
        </body>
    </html>
    """


@pytest.mark.asyncio
async def test_web_scraper_basic(mock_tool_context, mock_html_response):
    """Test basic web scraping."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_response.headers = {"content-type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test"
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["url"] == "https://example.com/test"
        assert result["title"] == "Test Page"


@pytest.mark.asyncio
async def test_web_scraper_extract_text(mock_tool_context, mock_html_response):
    """Test text extraction."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_response.headers = {"content-type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test",
            extract_text=True
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert "content" in result
        # Script tags should be removed
        assert "console.log" not in result["content"]


@pytest.mark.asyncio
async def test_web_scraper_css_selectors(mock_tool_context, mock_html_response):
    """Test CSS selector extraction."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_response.headers = {"content-type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test",
            selectors=["p.content", "h1"]
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert "extracted_data" in result
        assert "p.content" in result["extracted_data"]
        assert len(result["extracted_data"]["p.content"]) == 2


@pytest.mark.asyncio
async def test_web_scraper_extract_links(mock_tool_context, mock_html_response):
    """Test link extraction."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_response.headers = {"content-type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test",
            extract_links=True
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert "links" in result
        assert result["links_count"] == 2
        # Check that relative URLs are converted to absolute
        assert any("https://example.com/relative" in link["url"] for link in result["links"])


@pytest.mark.asyncio
async def test_web_scraper_extract_images(mock_tool_context, mock_html_response):
    """Test image extraction."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_response.headers = {"content-type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test",
            extract_images=True
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert "images" in result
        assert result["images_count"] == 1
        assert result["images"][0]["alt"] == "Test Image"


@pytest.mark.asyncio
async def test_web_scraper_custom_headers(mock_tool_context, mock_html_response):
    """Test scraping with custom headers."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_response.headers = {"content-type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test",
            headers={"User-Agent": "CustomBot/1.0"}
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_web_scraper_fetch_error(mock_tool_context):
    """Test scraping with fetch error."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("Connection failed")
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test"
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "FETCH_ERROR"


@pytest.mark.asyncio
async def test_web_scraper_missing_beautifulsoup(mock_tool_context):
    """Test scraping without BeautifulSoup installed."""
    with patch('builtins.__import__', side_effect=ImportError("No module named 'bs4'")):
        input_data = WebScraperInput(
            url="https://example.com/test"
        )

        # This will fail at import time, so we test the error handling
        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "MISSING_DEPENDENCY"


@pytest.mark.asyncio
async def test_web_scraper_metadata(mock_tool_context, mock_html_response):
    """Test that metadata is included."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_response.headers = {"content-type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = WebScraperInput(
            url="https://example.com/test"
        )

        result = await web_scraper_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert "metadata" in result
        assert result["metadata"]["status_code"] == 200
        assert "content_type" in result["metadata"]
