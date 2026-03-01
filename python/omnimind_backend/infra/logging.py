"""Logging setup — dual output: structured JSON (production) and Rich console (dev).

Uses ``structlog`` for structured key-value logging.  The log format is
controlled by the ``LOG_FORMAT`` environment variable (``json`` or ``console``).
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    pass

from omnimind_backend.infra.config import get_settings as _get_settings

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog + stdlib logging.

    Call once at startup.  Subsequent calls are no-ops.
    """
    global _configured  # noqa: PLW0603
    if _configured:
        return
    _configured = True

    settings = _get_settings()
    is_json = settings.log_format == "json"

    # Shared processors for both renderers.
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger with the given name."""
    return structlog.get_logger(name)


def reset_logging() -> None:
    """Reset the configured flag (for testing)."""
    global _configured  # noqa: PLW0603
    _configured = False
