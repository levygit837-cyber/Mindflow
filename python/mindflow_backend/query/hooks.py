"""Session hook helpers for the unified QueryEngine kernel.

Pure async functions that fire the same lifecycle hooks as the legacy
``AgentRuntime`` (``SessionStartHandler``, ``SessionEndHandler``,
``UserPromptSubmitHandler``) and attach the
``HookEventBroadcaster`` bridge that persists hook events to
``execution_memory``.

These helpers are stateless on purpose — they receive every dependency as an
argument so they are trivial to unit-test and can be called from either the
new kernel (`query/engine.py`) or the legacy path (`runtime/streaming/stream.py`)
during the migration.

Phase 2 of the unified-engine plan — see
.windsurf/plans/unified-engine-47796c.md §4.2.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mindflow_backend.hooks.event_broadcaster import HookEventBroadcaster
from mindflow_backend.hooks.handlers.session_end import SessionEndHandler
from mindflow_backend.hooks.handlers.session_start import SessionStartHandler
from mindflow_backend.hooks.handlers.user_prompt_submit import UserPromptSubmitHandler
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

HookHandler = Callable[[Any], Awaitable[None]]


async def fire_session_start(session_id: str, *, cwd: str | None = None) -> None:
    """Run ``SessionStart`` and ``InstructionsLoaded`` hooks for a session.

    Safe to call repeatedly. Failures are logged and swallowed because hooks
    must never prevent request processing.
    """
    try:
        async for result in SessionStartHandler.execute(session_id=session_id, cwd=cwd):
            if result.add_context:
                _logger.debug(
                    "session_start_hook_context",
                    session_id=session_id,
                    context=result.add_context[:200],
                )
    except Exception as exc:  # noqa: BLE001 - hook failures never block requests
        _logger.warning(
            "session_start_hooks_error",
            session_id=session_id,
            error=str(exc),
        )


async def fire_session_end(
    session_id: str,
    reason: str = "other",
    *,
    cwd: str | None = None,
) -> None:
    """Run ``SessionEnd`` hooks for a session. Failures logged but not raised."""
    try:
        async for result in SessionEndHandler.execute(
            session_id=session_id,
            reason=reason,
            cwd=cwd,
        ):
            if result.add_context:
                _logger.debug(
                    "session_end_hook_context",
                    session_id=session_id,
                    reason=reason,
                    context=result.add_context[:200],
                )
    except Exception as exc:  # noqa: BLE001 - hook failures never block requests
        _logger.warning(
            "session_end_hooks_error",
            session_id=session_id,
            reason=reason,
            error=str(exc),
        )


async def fire_user_prompt_submit(
    session_id: str,
    prompt: str,
    *,
    cwd: str | None = None,
) -> None:
    """Run ``UserPromptSubmit`` hooks. ``prompt`` kept for signature compat."""
    del prompt  # matches legacy AgentRuntime.handle_user_prompt behaviour
    try:
        async for result in UserPromptSubmitHandler.execute(
            session_id=session_id,
            cwd=cwd or get_settings().working_path,
        ):
            if result.add_context:
                _logger.debug(
                    "user_prompt_submit_hook_context",
                    session_id=session_id,
                    context=result.add_context[:200],
                )
    except Exception as exc:  # noqa: BLE001 - hook failures never block requests
        _logger.warning(
            "user_prompt_submit_hooks_error",
            session_id=session_id,
            error=str(exc),
        )


async def attach_hook_event_bridge(
    *,
    execution_id: str,
    session_id: str,
    execution_memory: Any,
) -> HookHandler | None:
    """Register a ``HookEventBroadcaster`` bridge that persists hook events.

    Returns the registered handler so the caller can deregister if needed.
    Returns ``None`` when ``execution_memory`` is missing or ``execution_id``
    is empty — mirroring the legacy contract.
    """
    if execution_memory is None or not execution_id:
        return None

    broadcaster = HookEventBroadcaster.get_instance()

    async def _handler(event: Any) -> None:
        if event.session_id not in {None, session_id}:
            return
        await execution_memory.append_event(
            execution_id,
            "hook_execution",
            {
                "hook_id": event.hook_id,
                "hook_name": event.hook_name,
                "hook_event": event.hook_event,
                "hook_state": event.state.value,
                "stdout": event.stdout,
                "stderr": event.stderr,
                "output": event.output,
                "exit_code": event.exit_code,
                "outcome": event.outcome,
                "visibility": "internal",
            },
            stage="hooking",
        )

    broadcaster.register(_handler)
    for pending in broadcaster.drain_pending(
        lambda event: event.session_id in {None, session_id},
    ):
        await _handler(pending)
    return _handler
