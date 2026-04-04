from unittest.mock import AsyncMock, patch

import pytest

from mindflow_backend.agents.tools.web.api_client import ApiClientTool
from mindflow_backend.agents.tools.web.api_client_v3 import (
    ApiClientInput,
    api_client_execute,
)
from mindflow_backend.agents.tools.web.http_client import HttpClientTool
from mindflow_backend.agents.tools.web.http_client_v3 import (
    HttpClientInput,
    http_client_execute,
)
from mindflow_backend.agents.tools.web.web_scraper import (
    ApiClientTool as WebScraperApiClientTool,
)
from mindflow_backend.agents.tools.web.web_scraper import (
    HttpClientTool as WebScraperHttpClientTool,
)
from mindflow_backend.agents.tools.web.web_scraper_v3 import (
    WebScraperInput,
    web_scraper_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


def test_web_scraper_module_reexports_canonical_clients() -> None:
    assert WebScraperHttpClientTool is HttpClientTool
    assert WebScraperApiClientTool is ApiClientTool


def test_canonical_web_clients_accept_compatibility_backend_arg() -> None:
    backend = object()

    http_tool = HttpClientTool(backend=backend)
    api_tool = ApiClientTool(backend=backend)

    assert http_tool.backend is backend
    assert api_tool.backend is backend


@pytest.mark.asyncio
async def test_api_client_delegates_to_canonical_http_client() -> None:
    backend = object()
    tool = ApiClientTool(backend=backend)

    with patch(
        "mindflow_backend.agents.tools.web.api_client.HttpClientTool.execute",
        new=AsyncMock(
            return_value={
                "success": True,
                "result": {
                    "status_code": 201,
                    "body": '{"ok": true}',
                    "headers": {"content-type": "application/json"},
                    "url": "https://api.example.com/v1/items",
                },
            }
        ),
    ) as execute_mock:
        result = await tool.execute(
            api_url="https://api.example.com",
            endpoint="v1/items",
            method="POST",
            auth_type="bearer",
            auth_token="secret-token",
            data={"name": "MindFlow"},
            params={"mode": "test"},
        )

    execute_mock.assert_awaited_once()
    _, kwargs = execute_mock.await_args
    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "https://api.example.com/v1/items"
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["params"] == {"mode": "test"}
    assert result["success"] is True
    assert result["result"]["data"] == {"ok": True}
    assert result["result"]["success"] is True


@pytest.mark.asyncio
async def test_api_client_supports_basic_auth_without_auth_token() -> None:
    tool = ApiClientTool()

    with patch(
        "mindflow_backend.agents.tools.web.api_client.HttpClientTool.execute",
        new=AsyncMock(
            return_value={
                "success": True,
                "result": {
                    "status_code": 200,
                    "body": '{"ok": true}',
                    "headers": {"content-type": "application/json"},
                    "url": "https://api.example.com/v1/items",
                },
            }
        ),
    ) as execute_mock:
        result = await tool.execute(
            api_url="https://api.example.com",
            endpoint="v1/items",
            method="GET",
            auth_type="basic",
            username="mindflow",
            password="secret",
        )

    execute_mock.assert_awaited_once()
    _, kwargs = execute_mock.await_args
    assert kwargs["headers"]["Authorization"] == "Basic bWluZGZsb3c6c2VjcmV0"
    assert result["success"] is True
    assert result["result"]["success"] is True


@pytest.mark.asyncio
async def test_web_scraper_v3_delegates_to_canonical_scraper() -> None:
    context = ToolContext(metadata={})

    with patch(
        "mindflow_backend.agents.tools.web.web_scraper_v3.WebScraperTool.execute",
        new=AsyncMock(
            return_value={
                "success": True,
                "result": {
                    "url": "https://example.com",
                    "title": "Example",
                    "extracted_data": {},
                    "links": [],
                    "images": [],
                    "metadata": {"status_code": 200},
                    "content": "content",
                },
            }
        ),
    ) as execute_mock:
        result = await web_scraper_execute(
            WebScraperInput(url="https://example.com"),
            context,
        )

    execute_mock.assert_awaited_once()
    assert result["success"] is True
    assert result["title"] == "Example"


@pytest.mark.asyncio
async def test_http_client_v3_delegates_to_canonical_http_client() -> None:
    context = ToolContext(metadata={})

    with patch(
        "mindflow_backend.agents.tools.web.http_client_v3.HttpClientTool.execute",
        new=AsyncMock(
            return_value={
                "success": True,
                "result": {
                    "status_code": 200,
                    "headers": {"content-type": "application/json"},
                    "body": '{"ok": true}',
                    "url": "https://example.com/api",
                    "elapsed": 0.12,
                    "content_type": "application/json",
                    "content_length": 12,
                },
            }
        ),
    ) as execute_mock:
        result = await http_client_execute(
            HttpClientInput(method="GET", url="https://example.com/api"),
            context,
        )

    execute_mock.assert_awaited_once()
    assert result["success"] is True
    assert result["status_code"] == 200


@pytest.mark.asyncio
async def test_api_client_v3_delegates_to_canonical_api_client() -> None:
    context = ToolContext(metadata={})

    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(
            return_value={
                "success": True,
                "result": {
                    "status_code": 202,
                    "data": {"queued": True},
                    "headers": {"content-type": "application/json"},
                    "url": "https://api.example.com/v1/jobs",
                    "success": True,
                },
            }
        ),
    ) as execute_mock:
        result = await api_client_execute(
            ApiClientInput(
                api_url="https://api.example.com",
                endpoint="v1/jobs",
                method="POST",
            ),
            context,
        )

    execute_mock.assert_awaited_once()
    assert result["success"] is True
    assert result["status_code"] == 202
