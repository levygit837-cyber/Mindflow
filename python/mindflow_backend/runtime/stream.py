"""Compatibility re-export for AgentRuntime.

Some modules still import runtime streaming symbols from
``mindflow_backend.runtime.stream``. Re-export the canonical implementation
surface so those imports stay adapter-only rather than becoming a second runtime.
"""

from __future__ import annotations

from mindflow_backend.runtime.streaming.stream import AgentRuntime, db_session

__all__ = ["AgentRuntime", "db_session"]
