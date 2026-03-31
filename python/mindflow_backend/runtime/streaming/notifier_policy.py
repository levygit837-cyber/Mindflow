"""Policies for deciding which runtime notifiers are worth surfacing to the UI."""

from __future__ import annotations

_NOISY_KIND_PREFIXES = (
    "file_",
    "shell_",
)

_NOISY_KINDS = {
    "search_done",
    "tool_start",
}

_ALWAYS_VISIBLE_KINDS = {
    "context_loaded",
    "gitnexus_status",
    "gitnexus_query",
    "gitnexus_context",
    "gitnexus_impact",
}

_IMPORTANT_TOKENS = (
    "error",
    "failed",
    "failure",
    "warning",
    "fallback",
    "scope",
    "slow",
    "performance",
)


def should_emit_backend_notifier(kind: str | None) -> bool:
    """Return whether a notifier kind should be emitted into the SSE stream.

    The runtime keeps structured events such as ``tool_call`` and ``tool_result``
    for operational detail. This policy trims the parallel notifier stream so the
    frontend only receives high-signal summaries instead of a second card for the
    same filesystem/shell/tool action.
    """

    normalized = str(kind or "").strip().lower()
    if not normalized:
        return False

    if normalized in _ALWAYS_VISIBLE_KINDS:
        return True

    if normalized.startswith(_NOISY_KIND_PREFIXES):
        return False

    if normalized in _NOISY_KINDS:
        return False

    if any(token in normalized for token in _IMPORTANT_TOKENS):
        return True

    return True
