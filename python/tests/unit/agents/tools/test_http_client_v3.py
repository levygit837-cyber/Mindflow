"""Unit tests for HttpClientToolV3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from mindflow_backend.agents.tools.web.http_client_v3 import (
    HttpClientInput,
    HttpClientToolV3,
    http_client_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.fixture
def mock_response():
    """Mock requests.Response."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {"content-type": "application/json", "content-length": "100"}
    response.text = '{"status": "success"}'
    response.url = "https://api.example.com/test"
    return response


@pytest.mark.asyncio
async def test_http_client_get_request(mock_tool_context, mock_response):
    """Test basic GET request."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test"
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["method"] == "GET"
        assert result["status_code"] == 200
        assert result["body"] == '{"status": "success"}'


@pytest.mark.asyncio
async def test_http_client_post_with_json(mock_tool_context, mock_response):
    """Test POST request with JSON data."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="POST",
            url="https://api.example.com/test",
            data={"key": "value"}
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["method"] == "POST"


@pytest.mark.asyncio
async def test_http_client_with_headers(mock_tool_context, mock_response):
    """Test request with custom headers."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test",
            headers={"Authorization": "Bearer token123"}
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_http_client_with_params(mock_tool_context, mock_response):
    """Test request with query parameters."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test",
            params={"page": "1", "limit": "10"}
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_http_client_invalid_url(mock_tool_context):
    """Test request with invalid URL."""
    input_data = HttpClientInput(
        method="GET",
        url="invalid-url"
    )

    result = await http_client_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "INVALID_URL"


@pytest.mark.asyncio
async def test_http_client_timeout(mock_tool_context):
    """Test request timeout."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.side_effect = requests.exceptions.Timeout("Timeout")
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test",
            timeout=5
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_http_client_ssl_error(mock_tool_context):
    """Test SSL verification error."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.side_effect = requests.exceptions.SSLError("SSL Error")
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test"
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "SSL_ERROR"


@pytest.mark.asyncio
async def test_http_client_connection_error(mock_tool_context):
    """Test connection error."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test"
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "CONNECTION_ERROR"


@pytest.mark.asyncio
async def test_http_client_http_error(mock_tool_context):
    """Test HTTP error (4xx, 5xx)."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        http_error = requests.exceptions.HTTPError("Not Found")
        http_error.response = mock_error_response
        mock_session.request.side_effect = http_error
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test"
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "HTTP_ERROR"


@pytest.mark.asyncio
async def test_http_client_response_truncation(mock_tool_context):
    """Test large response truncation."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        large_response = MagicMock()
        large_response.status_code = 200
        large_response.headers = {"content-type": "text/plain"}
        large_response.text = "x" * (11 * 1024 * 1024)  # 11MB
        large_response.url = "https://api.example.com/test"
        mock_session.request.return_value = large_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test"
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["truncated"] is True
        assert "truncated" in result["body"].lower()


@pytest.mark.asyncio
async def test_http_client_custom_timeout(mock_tool_context, mock_response):
    """Test request with custom timeout."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test",
            timeout=60
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_http_client_disable_ssl_verification(mock_tool_context, mock_response):
    """Test request with SSL verification disabled."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test",
            verify_ssl=False
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_http_client_disable_redirects(mock_tool_context, mock_response):
    """Test request with redirects disabled."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = HttpClientInput(
            method="GET",
            url="https://api.example.com/test",
            follow_redirects=False
        )

        result = await http_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
