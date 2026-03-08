"""Compatibility re-export for AgentRuntime.

Some gRPC modules import `AgentRuntime` from `mindflow_backend.runtime.stream`,
while the implementation lives under `mindflow_backend.runtime.streaming.stream`.
"""

from __future__ import annotations

from mindflow_backend.runtime.streaming.stream import AgentRuntime

__all__ = ["AgentRuntime"]

