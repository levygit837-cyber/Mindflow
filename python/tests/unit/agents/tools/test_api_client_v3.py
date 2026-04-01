"""Unit tests for ApiClientToolV3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from mindflow_backend.agents.tools.web.api_client_v3 import (
    ApiClientInput,
    ApiClientToolV3,
    api_client_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.fixture
def mock_api_response():
    """Mock API response."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {"content-type": "application/json"}
    response.url = "https://api.example.com/users"
    response.json.return_value = {"id": 1, "name": "Test User"}
    return response


@pytest.mark.asyncio
async def test_api_client_basic_get(mock_tool_context, mock_api_response):
    """Test basic GET request."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            method="GET"
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["api_success"] is True
        assert result["status_code"] == 200
        assert result["data"]["id"] == 1


@pytest.mark.asyncio
async def test_api_client_bearer_auth(mock_tool_context, mock_api_response):
    """Test Bearer token authentication."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            auth_type="bearer",
            auth_token="token123"
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_api_client_api_key_auth(mock_tool_context, mock_api_response):
    """Test API key authentication."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            auth_type="api_key",
            auth_token="key123",
            api_key_header="X-API-Key"
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_api_client_basic_auth(mock_tool_context, mock_api_response):
    """Test Basic authentication."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            auth_type="basic",
            auth_token="dummy",
            username="user",
            password="pass"
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_api_client_basic_auth_missing_credentials(mock_tool_context):
    """Test Basic auth without username/password."""
    input_data = ApiClientInput(
        api_url="https://api.example.com",
        endpoint="/users",
        auth_type="basic",
        auth_token="dummy"
    )

    result = await api_client_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "MISSING_CREDENTIALS"


@pytest.mark.asyncio
async def test_api_client_post_with_data(mock_tool_context, mock_api_response):
    """Test POST request with JSON data."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            method="POST",
            data={"name": "New User", "email": "user@example.com"}
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["method"] == "POST"


@pytest.mark.asyncio
async def test_api_client_with_query_params(mock_tool_context, mock_api_response):
    """Test request with query parameters."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            params={"page": "1", "limit": "10"}
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_api_client_endpoint_without_slash(mock_tool_context, mock_api_response):
    """Test endpoint without leading slash."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="users"  # No leading slash
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_api_client_non_json_response(mock_tool_context):
    """Test handling non-JSON response."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/users"
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Plain text response"
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users"
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["data"] == "Plain text response"


@pytest.mark.asyncio
async def test_api_client_timeout(mock_tool_context):
    """Test API request timeout."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.side_effect = requests.exceptions.Timeout("Timeout")
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            timeout=5
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_api_client_connection_error(mock_tool_context):
    """Test API connection error."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users"
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "CONNECTION_ERROR"


@pytest.mark.asyncio
async def test_api_client_custom_headers(mock_tool_context, mock_api_response):
    """Test request with custom headers."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.request.return_value = mock_api_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users",
            headers={"X-Custom-Header": "value"}
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_api_client_4xx_response(mock_tool_context):
    """Test handling 4xx response."""
    with patch('requests.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/users"
        mock_response.json.return_value = {"error": "Not found"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        input_data = ApiClientInput(
            api_url="https://api.example.com",
            endpoint="/users"
        )

        result = await api_client_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["api_success"] is False  # 4xx is not success
        assert result["status_code"] == 404
