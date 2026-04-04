"""Unit tests for ApiClientToolV3."""

from unittest.mock import AsyncMock, patch

import pytest

from mindflow_backend.agents.tools.web.api_client_v3 import (
    ApiClientInput,
    api_client_execute,
)


def _make_canonical_success(
    *,
    status_code: int = 200,
    data: object = None,
    url: str = "https://api.example.com/users",
) -> dict[str, object]:
    if data is None:
        data = {"id": 1, "name": "Test User"}
    return {
        "success": True,
        "result": {
            "status_code": status_code,
            "data": data,
            "headers": {"content-type": "application/json"},
            "url": url,
            "success": 200 <= status_code < 300,
        },
    }


def _make_canonical_error(error_code: str, *, error: str) -> dict[str, object]:
    return {
        "success": False,
        "error": error,
        "error_code": error_code,
    }


@pytest.mark.asyncio
async def test_api_client_basic_get(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success()),
    ) as execute_mock:
        result = await api_client_execute(
            ApiClientInput(
                api_url="https://api.example.com",
                endpoint="/users",
                method="GET",
            ),
            mock_tool_context,
        )

    execute_mock.assert_awaited_once_with(
        api_url="https://api.example.com",
        endpoint="/users",
        method="GET",
        headers={},
        auth_type=None,
        auth_token=None,
        username=None,
        password=None,
        api_key_header="X-API-Key",
        data=None,
        params={},
        timeout=30,
    )
    assert result["success"] is True
    assert result["api_success"] is True
    assert result["status_code"] == 200
    assert result["data"] == {"id": 1, "name": "Test User"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("auth_type", "extra_fields"),
    [
        ("bearer", {"auth_token": "token123"}),
        ("api_key", {"auth_token": "key123", "api_key_header": "X-API-Key"}),
        ("basic", {"username": "user", "password": "pass"}),
    ],
)
async def test_api_client_auth_variants_are_forwarded(
    mock_tool_context,
    auth_type,
    extra_fields,
) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success()),
    ) as execute_mock:
        input_kwargs = {
            "api_url": "https://api.example.com",
            "endpoint": "/users",
            "auth_type": auth_type,
        }
        input_kwargs.update(extra_fields)
        result = await api_client_execute(
            ApiClientInput(**input_kwargs),
            mock_tool_context,
        )

    _, kwargs = execute_mock.await_args
    assert kwargs["auth_type"] == auth_type
    for key, value in extra_fields.items():
        assert kwargs[key] == value
    assert result["success"] is True


@pytest.mark.asyncio
async def test_api_client_basic_auth_missing_credentials(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(
            return_value=_make_canonical_error(
                "MISSING_CREDENTIALS",
                error="Basic auth requires username and password",
            )
        ),
    ):
        result = await api_client_execute(
            ApiClientInput(
                api_url="https://api.example.com",
                endpoint="/users",
                auth_type="basic",
            ),
            mock_tool_context,
        )

    assert result["success"] is False
    assert result["error_code"] == "MISSING_CREDENTIALS"


@pytest.mark.asyncio
async def test_api_client_post_with_data(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success(status_code=201)),
    ) as execute_mock:
        result = await api_client_execute(
            ApiClientInput(
                api_url="https://api.example.com",
                endpoint="/users",
                method="POST",
                data={"name": "New User", "email": "user@example.com"},
            ),
            mock_tool_context,
        )

    _, kwargs = execute_mock.await_args
    assert kwargs["data"] == {"name": "New User", "email": "user@example.com"}
    assert result["success"] is True
    assert result["method"] == "POST"


@pytest.mark.asyncio
async def test_api_client_non_json_response(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success(data="Plain text response")),
    ):
        result = await api_client_execute(
            ApiClientInput(
                api_url="https://api.example.com",
                endpoint="/users",
            ),
            mock_tool_context,
        )

    assert result["success"] is True
    assert result["data"] == "Plain text response"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error_code", "error_message"),
    [
        ("TIMEOUT", "Request timeout after configured timeout"),
        ("CONNECTION_ERROR", "Connection failed: boom"),
    ],
)
async def test_api_client_error_codes_are_preserved(
    mock_tool_context,
    error_code,
    error_message,
) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(
            return_value=_make_canonical_error(error_code, error=error_message)
        ),
    ):
        result = await api_client_execute(
            ApiClientInput(
                api_url="https://api.example.com",
                endpoint="/users",
            ),
            mock_tool_context,
        )

    assert result["success"] is False
    assert result["error_code"] == error_code


@pytest.mark.asyncio
async def test_api_client_4xx_response(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.api_client_v3.ApiClientTool.execute",
        new=AsyncMock(
            return_value=_make_canonical_success(
                status_code=404,
                data={"error": "Not found"},
            )
        ),
    ):
        result = await api_client_execute(
            ApiClientInput(
                api_url="https://api.example.com",
                endpoint="/users",
            ),
            mock_tool_context,
        )

    assert result["success"] is True
    assert result["api_success"] is False
    assert result["status_code"] == 404
