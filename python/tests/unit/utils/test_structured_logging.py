"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging
from io import StringIO
from unittest.mock import patch

import structlog

from omnimind_backend.infra.config import Settings
from omnimind_backend.infra.logging import configure_logging, get_logger, reset_logging


def _capture_log(log_format: str, message: str) -> str:
    """Configure logging, emit one message, return the captured output."""
    reset_logging()
    fake_settings = Settings(LOG_FORMAT=log_format)

    with patch("omnimind_backend.infra.logging._get_settings", return_value=fake_settings):
        configure_logging(level=logging.INFO)

    # Replace the handler to capture output into a buffer.
    buf = StringIO()
    handler = logging.StreamHandler(buf)

    renderer: structlog.types.Processor
    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)

    logger = get_logger("test_logger")
    logger.info(message, extra_key="extra_value")

    return buf.getvalue()


def test_json_format_produces_valid_json():
    output = _capture_log("json", "hello structured world")
    assert output.strip()
    parsed = json.loads(output.strip())
    assert parsed["event"] == "hello structured world"
    assert "level" in parsed or "log_level" in parsed


def test_console_format_is_human_readable():
    output = _capture_log("console", "human readable log")
    assert "human readable log" in output


def test_configure_logging_is_idempotent():
    reset_logging()
    fake_settings = Settings(LOG_FORMAT="console")
    with patch("omnimind_backend.infra.logging._get_settings", return_value=fake_settings):
        configure_logging(level=logging.INFO)
        handler_count = len(logging.getLogger().handlers)
        # Second call should be no-op
        configure_logging(level=logging.DEBUG)
        assert len(logging.getLogger().handlers) == handler_count
    reset_logging()
