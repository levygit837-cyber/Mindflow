from __future__ import annotations

from fastapi import FastAPI
from starlette.requests import Request

from mindflow_backend.api.middleware.error_handler import ErrorHandlerMiddleware
from mindflow_backend.exceptions.infrastructure.configuration import (
    ConfigurationError as InfraConfigurationError,
)
from mindflow_backend.schemas.errors import ErrorCategory, ErrorSeverity


def test_error_handler_classifies_infra_configuration_error() -> None:
    handler = ErrorHandlerMiddleware(FastAPI())
    exception = InfraConfigurationError.__new__(InfraConfigurationError)
    Exception.__init__(exception, "missing configuration")

    category, severity = handler._classify_exception(exception)

    assert category is ErrorCategory.CONFIGURATION
    assert severity is ErrorSeverity.MEDIUM


def test_error_handler_builds_request_context_as_error_context() -> None:
    handler = ErrorHandlerMiddleware(FastAPI())
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": "/v1/agent/list",
            "headers": [
                (b"host", b"testserver"),
                (b"user-agent", b"pytest"),
                (b"x-request-id", b"req-123"),
                (b"x-forwarded-for", b"203.0.113.10"),
            ],
            "query_string": b"",
            "path_params": {},
            "client": ("127.0.0.1", 1234),
        }
    )

    schema = handler._create_error_schema(ValueError("bad input"), request)

    assert schema.context.component == "api"
    assert schema.context.request_id == "req-123"
    assert schema.context.metadata["client_ip"] == "203.0.113.10"
    assert schema.context.metadata["method"] == "GET"
