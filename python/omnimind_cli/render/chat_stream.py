from __future__ import annotations

import json
from typing import Any

from rich.console import Console

from omnimind_backend.schemas.agent import StreamEvent


class ChatStreamRenderer:
    def __init__(self, console: Console) -> None:
        self.console = console
        self._response_open = False

    def _safe_json(self, payload: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(payload)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    def _ensure_response_line_closed(self) -> None:
        if self._response_open:
            self.console.print()
            self._response_open = False

    def _render_step(self, event: StreamEvent) -> None:
        parsed = self._safe_json(event.data)
        if parsed is None:
            self.console.print(f"[cyan]Step[/]: {event.data}")
            return

        step_name = parsed.get("stepName") or "step"
        detail = parsed.get("detail") or ""
        action = parsed.get("action")
        if action == "start":
            prefix = "[cyan]→[/]"
        elif action == "complete":
            prefix = "[green]✓[/]"
        else:
            prefix = "[cyan]•[/]"

        message = f"{prefix} [bold]{step_name}[/]"
        if detail:
            message += f" - {detail}"
        self.console.print(message)

    def _render_tool_call(self, event: StreamEvent) -> None:
        parsed = self._safe_json(event.data)
        if parsed is None:
            self.console.print(f"[yellow]Tool call[/]: {event.data}")
            return

        name = parsed.get("name") or "unknown_tool"
        args = parsed.get("args")
        self.console.print(f"[yellow]Tool call[/] [bold]{name}[/] args={args}")

    def _render_tool_result(self, event: StreamEvent) -> None:
        parsed = self._safe_json(event.data)
        if parsed is None:
            self.console.print(f"[yellow]Tool result[/]: {event.data}")
            return

        name = parsed.get("name") or "unknown_tool"
        result = str(parsed.get("result", ""))
        compact = result if len(result) <= 220 else f"{result[:220]}..."
        self.console.print(f"[yellow]Tool result[/] [bold]{name}[/]: {compact}")

    def _render_response(self, chunk: str) -> None:
        if not self._response_open:
            self.console.print("[bold green]Assistant:[/] ", end="")
            self._response_open = True
        self.console.print(chunk, end="")

    def render(self, event: StreamEvent) -> None:
        if event.type == "response":
            self._render_response(event.data)
            return

        self._ensure_response_line_closed()

        if event.type == "thought":
            self.console.print(f"[cyan]Thinking[/]: {event.data}")
            return
        if event.type in {"step", "agent_step"}:
            self._render_step(event)
            return
        if event.type == "tool_call":
            self._render_tool_call(event)
            return
        if event.type == "tool_result":
            self._render_tool_result(event)
            return
        if event.type == "error":
            self.console.print(f"[bold red]Error:[/] {event.data}")
            return
        if event.type == "done":
            self.console.print("[green]Done.[/]")
            return

        self.console.print(f"[{event.type}] {event.data}")
