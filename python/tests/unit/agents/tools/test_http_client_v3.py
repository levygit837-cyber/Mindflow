"""Unit tests for HttpClientToolV3."""

from unittest.mock import AsyncMock, patch

import pytest

from mindflow_backend.agents.tools.web.http_client_v3 import (
    HttpClientInput,
    http_client_execute,
)


def _make_canonical_success(
    *,
    body: str = '{"status": "success"}',
    status_code: int = 200,
    url: str = "https://api.example.com/test",
) -> dict[str, object]:
    return {
        "success": True,
        "result": {
            "status_code": status_code,
            "headers": {
                "content-type": "application/json",
                "content-length": str(len(body)),
            },
            "body": body,
            "url": url,
            "elapsed": 0.42,
            "content_type": "application/json",
            "content_length": len(body),
        },
    }


def _make_canonical_error(
    error_code: str,
    *,
    error: str,
    status_code: int | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "success": False,
        "error": error,
        "error_code": error_code,
    }
    if status_code is not None:
        result["status_code"] = status_code
    return result


@pytest.mark.asyncio
async def test_http_client_get_request(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.http_client_v3.HttpClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success()),
    ) as execute_mock:
        result = await http_client_execute(
            HttpClientInput(method="GET", url="https://api.example.com/test"),
            mock_tool_context,
        )

    execute_mock.assert_awaited_once_with(
        method="GET",
        url="https://api.example.com/test",
        headers={},
        params={},
        data=None,
        form_data=None,
        timeout=30,
        verify_ssl=True,
        follow_redirects=True,
        max_redirects=5,
    )
    assert result["success"] is True
    assert result["method"] == "GET"
    assert result["status_code"] == 200
    assert result["body"] == '{"status": "success"}'


@pytest.mark.asyncio
async def test_http_client_post_with_json(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.http_client_v3.HttpClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success(status_code=201)),
    ) as execute_mock:
        result = await http_client_execute(
            HttpClientInput(
                method="POST",
                url="https://api.example.com/test",
                data={"key": "value"},
            ),
            mock_tool_context,
        )

    _, kwargs = execute_mock.await_args
    assert kwargs["data"] == {"key": "value"}
    assert result["success"] is True
    assert result["method"] == "POST"


@pytest.mark.asyncio
async def test_http_client_invalid_url(mock_tool_context) -> None:
    result = await http_client_execute(
        HttpClientInput(method="GET", url="invalid-url"),
        mock_tool_context,
    )

    assert result["success"] is False
    assert result["error_code"] == "INVALID_URL"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error_code", "error_message"),
    [
        ("TIMEOUT", "Request timeout after configured timeout"),
        ("SSL_ERROR", "SSL verification failed: SSL Error"),
        ("CONNECTION_ERROR", "Connection failed: boom"),
        ("HTTP_ERROR", "HTTP error: Not Found"),
    ],
)
async def test_http_client_preserves_canonical_error_codes(
    mock_tool_context,
    error_code,
    error_message,
) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.http_client_v3.HttpClientTool.execute",
        new=AsyncMock(
            return_value=_make_canonical_error(
                error_code,
                error=error_message,
                status_code=404 if error_code == "HTTP_ERROR" else None,
            )
        ),
    ):
        result = await http_client_execute(
            HttpClientInput(method="GET", url="https://api.example.com/test"),
            mock_tool_context,
        )

    assert result["success"] is False
    assert result["error_code"] == error_code
    if error_code == "HTTP_ERROR":
        assert result["status_code"] == 404


@pytest.mark.asyncio
async def test_http_client_response_truncation(mock_tool_context) -> None:
    truncated_body = "x" * 32 + "\n... Response truncated due to size limit."
    with patch(
        "mindflow_backend.agents.tools.web.http_client_v3.HttpClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success(body=truncated_body)),
    ):
        result = await http_client_execute(
            HttpClientInput(method="GET", url="https://api.example.com/test"),
            mock_tool_context,
        )

    assert result["success"] is True
    assert result["truncated"] is True
    assert "truncated" in result["body"].lower()


@pytest.mark.asyncio
async def test_http_client_custom_flags_are_forwarded(mock_tool_context) -> None:
    with patch(
        "mindflow_backend.agents.tools.web.http_client_v3.HttpClientTool.execute",
        new=AsyncMock(return_value=_make_canonical_success()),
    ) as execute_mock:
        result = await http_client_execute(
            HttpClientInput(
                method="GET",
                url="https://api.example.com/test",
                timeout=60,
                verify_ssl=False,
                follow_redirects=False,
                max_redirects=2,
            ),
            mock_tool_context,
        )

    _, kwargs = execute_mock.await_args
    assert kwargs["timeout"] == 60
    assert kwargs["verify_ssl"] is False
    assert kwargs["follow_redirects"] is False
    assert kwargs["max_redirects"] == 2
    assert result["success"] is True
