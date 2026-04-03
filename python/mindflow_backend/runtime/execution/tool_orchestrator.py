"""Canonical orchestration for batched tool execution.

This module centralizes MindFlow tool execution with Claude-style semantics:
- consecutive concurrency-safe tools execute as a parallel batch
- non-safe tools execute exclusively
- final tool results are emitted in original tool-call order
- oversized aggregate tool output is persisted to disk with previews
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass(slots=True)
class OrchestratedToolCallResult:
    """Normalized result for a tool call executed by the orchestrator."""

    tool_call_id: str
    tool_name: str
    tool_args: dict[str, Any]
    raw_result: Any
    serialized_result: str
    tool_meta: dict[str, Any] | None = None
    persisted_output_path: Path | None = None
    error: str | None = None


class ToolOrchestrator:
    """Execute tool calls through one canonical orchestration path."""

    def __init__(
        self,
        *,
        lc_tools: list[Any],
        event_dispatcher: Any | None = None,
        session_id: str | None = None,
        max_concurrent: int = 5,
        result_store_dir: str | Path | None = None,
        max_turn_result_chars: int = 250_000,
    ) -> None:
        self._lc_tools = lc_tools
        self._tools_by_name = {tool.name: tool for tool in lc_tools}
        self._event_dispatcher = event_dispatcher
        self._session_id = session_id or "anonymous-session"
        self._max_concurrent = max(1, max_concurrent)
        self._max_turn_result_chars = max_turn_result_chars
        self._turn_result_chars = 0
        self._result_store_dir = Path(result_store_dir) if result_store_dir else (
            Path(tempfile.gettempdir()) / "mindflow_tool_results" / self._session_id
        )

    async def execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[OrchestratedToolCallResult]:
        """Execute tool calls using Claude-style batch partitioning."""
        if not tool_calls:
            return []

        ordered_results: list[OrchestratedToolCallResult] = []

        for batch in self._partition_tool_calls(tool_calls):
            await self._dispatch_start_events(batch)
            batch_results = await self._execute_batch(batch)
            for result in batch_results:
                self._apply_turn_budget(result)
            await self._dispatch_result_events(batch_results)
            ordered_results.extend(batch_results)

        return ordered_results

    def _partition_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[list[dict[str, Any]]]:
        """Group consecutive concurrency-safe tools into parallel batches."""
        batches: list[list[dict[str, Any]]] = []
        current_safe_batch: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            if self._is_concurrency_safe(tool_name):
                current_safe_batch.append(tool_call)
                continue

            if current_safe_batch:
                batches.append(current_safe_batch)
                current_safe_batch = []

            batches.append([tool_call])

        if current_safe_batch:
            batches.append(current_safe_batch)

        return batches

    async def _dispatch_start_events(self, batch: list[dict[str, Any]]) -> None:
        """Emit tool start notifications in original request order."""
        if self._event_dispatcher is None:
            return

        for tool_call in batch:
            tool_name = tool_call.get("name", "")
            tool = self._tools_by_name.get(tool_name)
            tool_meta = self._extract_tool_meta(tool)
            try:
                await self._event_dispatcher(
                    "tool_call_start",
                    {
                        "tool": tool_name,
                        "args": tool_call.get("args", {}),
                        "tool_call_id": tool_call.get("id", ""),
                        "tool_meta": tool_meta,
                    },
                )
            except Exception as exc:
                _logger.debug(
                    "tool_call_start_event_dispatch_failed",
                    tool=tool_name,
                    error=str(exc),
                )

    async def _dispatch_result_events(
        self,
        results: list[OrchestratedToolCallResult],
    ) -> None:
        """Emit final tool result notifications in original request order."""
        if self._event_dispatcher is None:
            return

        for result in results:
            try:
                await self._event_dispatcher(
                    "tool_call",
                    {
                        "tool": result.tool_name,
                        "args": result.tool_args,
                        "result_preview": result.serialized_result[:300],
                        "tool_call_id": result.tool_call_id,
                        "tool_meta": result.tool_meta,
                    },
                )
            except Exception as exc:
                _logger.debug(
                    "tool_call_event_dispatch_failed",
                    tool=result.tool_name,
                    error=str(exc),
                )

    async def _execute_batch(
        self,
        batch: list[dict[str, Any]],
    ) -> list[OrchestratedToolCallResult]:
        """Execute one tool batch and preserve original result ordering."""
        if len(batch) == 1 and not self._is_concurrency_safe(batch[0].get("name", "")):
            return [await self._execute_tool_call(batch[0])]

        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def _run(tool_call: dict[str, Any]) -> OrchestratedToolCallResult:
            async with semaphore:
                return await self._execute_tool_call(tool_call)

        tasks = [asyncio.create_task(_run(tool_call)) for tool_call in batch]
        return await asyncio.gather(*tasks)

    async def _execute_tool_call(
        self,
        tool_call: dict[str, Any],
    ) -> OrchestratedToolCallResult:
        """Execute one tool and normalize the result."""
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {}) or {}
        tool_call_id = tool_call.get("id", "") or str(uuid.uuid4())
        tool = self._tools_by_name.get(tool_name)
        tool_meta = self._extract_tool_meta(tool)

        if tool is None:
            serialized = json.dumps(
                {"success": False, "error": f"Unknown tool: {tool_name}"},
                ensure_ascii=False,
            )
            return OrchestratedToolCallResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_args=tool_args,
                raw_result=None,
                serialized_result=serialized,
                tool_meta=None,
                error=f"Unknown tool: {tool_name}",
            )

        try:
            _logger.info(
                "tool_invoked",
                tool=tool_name,
                args=str(tool_args)[:200],
                session_id=self._session_id,
            )
            raw_result = await tool.ainvoke(tool_args)
            serialized_result = self._serialize_tool_result(raw_result)
            return OrchestratedToolCallResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_args=tool_args,
                raw_result=raw_result,
                serialized_result=serialized_result,
                tool_meta=tool_meta,
            )
        except Exception as exc:
            _logger.warning(
                "tool_execution_error",
                tool=tool_name,
                error=str(exc),
                session_id=self._session_id,
            )
            serialized = json.dumps(
                {"success": False, "error": f"Tool execution failed: {exc}"},
                ensure_ascii=False,
            )
            return OrchestratedToolCallResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_args=tool_args,
                raw_result=None,
                serialized_result=serialized,
                tool_meta=tool_meta,
                error=str(exc),
            )

    def _apply_turn_budget(self, result: OrchestratedToolCallResult) -> None:
        """Persist oversized results and replace them with stable previews."""
        serialized = result.serialized_result
        if not serialized:
            return

        tool_limit = self._max_result_size_for_tool(result.tool_meta)
        exceeds_tool_limit = tool_limit is not None and len(serialized) > tool_limit
        exceeds_turn_limit = (
            self._max_turn_result_chars > 0
            and self._turn_result_chars + len(serialized) > self._max_turn_result_chars
        )

        if not exceeds_tool_limit and not exceeds_turn_limit:
            self._turn_result_chars += len(serialized)
            return

        persisted_path = self._persist_output(
            tool_call_id=result.tool_call_id,
            tool_name=result.tool_name,
            content=serialized,
        )
        preview = serialized[:500]
        result.persisted_output_path = persisted_path
        result.serialized_result = (
            f"{preview}\n\n[output truncated] Full output saved to: {persisted_path}"
        )
        self._turn_result_chars += len(result.serialized_result)

    def _persist_output(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        content: str,
    ) -> Path:
        """Persist a full tool output to disk for later inspection."""
        self._result_store_dir.mkdir(parents=True, exist_ok=True)
        safe_tool_name = tool_name.replace("/", "_").replace(" ", "_") or "tool"
        path = self._result_store_dir / f"{safe_tool_name}-{tool_call_id}.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def _is_concurrency_safe(self, tool_name: str) -> bool:
        """Return whether a tool is explicitly marked safe for parallel runs."""
        tool = self._tools_by_name.get(tool_name)
        if tool is None:
            return False

        tool_meta = self._extract_tool_meta(tool)
        return bool(tool_meta.get("is_concurrency_safe", False))

    @staticmethod
    def _extract_tool_meta(tool: Any | None) -> dict[str, Any] | None:
        """Normalize tool metadata to a plain dictionary."""
        if tool is None:
            return None

        tool_meta = getattr(tool, "metadata", None)
        if tool_meta is None:
            return None

        if isinstance(tool_meta, dict):
            return dict(tool_meta)

        try:
            return dict(tool_meta)
        except Exception:
            return {"value": str(tool_meta)}

    @staticmethod
    def _serialize_tool_result(raw_result: Any) -> str:
        """Serialize arbitrary tool output to a stable string payload."""
        if isinstance(raw_result, str):
            return raw_result
        return json.dumps(raw_result, ensure_ascii=False, default=str)

    @staticmethod
    def _max_result_size_for_tool(tool_meta: dict[str, Any] | None) -> int | None:
        """Resolve per-tool max result size metadata."""
        if not tool_meta:
            return None

        limit = tool_meta.get("max_result_size_chars")
        if isinstance(limit, int) and limit > 0:
            return limit
        return None
