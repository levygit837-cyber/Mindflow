"""Bridge between QueryEngine strategy events (dicts) and ``StreamEvent`` objects.

``QueryEngine.execute()`` yields raw dicts with a ``type`` key. The legacy
``AgentRuntime.stream_chat`` yields typed ``StreamEvent`` pydantic objects.
This module provides ``adapt_strategy_events()`` — an async generator that
converts the dict stream into ``StreamEvent`` objects so the unified path can
slot into ``stream_chat`` without changing the SSE contract exposed to the
frontend.

Phase 3 of the unified-engine plan — see
.windsurf/plans/unified-engine-47796c.md §4.3.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.query.streaming import custom_event, done_event, error_event, next_seq
from mindflow_backend.schemas.chat.agent import StreamEvent

_logger = get_logger(__name__)

_VALID_PROVIDERS = {"anthropic", "openai", "ollama", "google", "vertexai", "lmstudio", "windsurf"}


async def adapt_strategy_events(
    events: AsyncGenerator[dict[str, Any], None],
    *,
    provider: str,
    model: str,
    run_id: str,
    session_id: str,
    normalizer: Any,
    counter: list[int],
) -> AsyncGenerator[StreamEvent, None]:
    """Convert raw strategy-event dicts to typed ``StreamEvent`` objects.

    Emits a ``done`` event at the end if the strategy didn't yield one
    explicitly — preserving the invariant that every SSE stream ends with
    ``type="done"``.

    Args:
        events:     Async generator from ``QueryEngine.execute()``.
        provider:   LLM provider string (used for meta fields).
        model:      Model name (used for meta fields).
        run_id:     Unique run identifier.
        session_id: Session identifier (maps to ``turnRunId`` in meta).
        normalizer: ``AgentChatStreamNormalizer`` instance for step/tool events.
        counter:    Mutable ``[int]`` sequence counter shared with the caller.
    """
    safe_provider = provider if provider in _VALID_PROVIDERS else "anthropic"
    done_seen = False

    async for ev in events:
        ev_type = ev.get("type")

        if ev_type == "assistant":
            content = ev.get("content") or ""
            if content:
                # Emit as a normalizer response chunk (preserves SSE data format)
                yield normalizer.response_event(
                    next_seq(counter),
                    data=content,
                    run_id=run_id,
                )
            else:
                _logger.debug(
                    "adapt_strategy_events_empty_assistant",
                    session_id=session_id,
                )

        elif ev_type == "tool_result":
            tool_use_id = ev.get("tool_use_id", "")
            content = ev.get("content", "")
            is_error = bool(ev.get("is_error"))
            content_str = json.dumps(content) if not isinstance(content, str) else content
            yield normalizer.tool_result_event(
                next_seq(counter),
                tool_call_id=tool_use_id,
                content=content_str,
                is_error=is_error,
                run_id=run_id,
            )

        elif ev_type == "system":
            content = ev.get("content", "")
            is_error = bool(ev.get("is_error"))
            if is_error:
                # Surface as a visible error event
                yield error_event(
                    exc=Exception(content),
                    counter=counter,
                    provider=safe_provider,
                    model=model,
                    run_id=run_id,
                    session_id=session_id,
                    node="unified_engine",
                    node_category="RUNTIME",
                )
            else:
                yield custom_event(
                    counter=counter,
                    run_id=run_id,
                    session_id=session_id,
                    event_type="system_message",
                    data=content,
                )

        elif ev_type == "final":
            # Strategy signals completion with optional accumulated content.
            content = ev.get("content", "")
            if content:
                yield normalizer.response_event(
                    next_seq(counter),
                    data=content,
                    run_id=run_id,
                )

        elif ev_type == "done":
            done_seen = True
            yield done_event(
                counter=counter,
                provider=safe_provider,
                model=model,
                run_id=run_id,
                session_id=session_id,
            )

        else:
            _logger.debug(
                "adapt_strategy_events_unknown_type",
                event_type=ev_type,
                session_id=session_id,
            )

    if not done_seen:
        yield done_event(
            counter=counter,
            provider=safe_provider,
            model=model,
            run_id=run_id,
            session_id=session_id,
        )
