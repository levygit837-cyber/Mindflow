from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner

from mindflow_backend.schemas.agent import StreamEvent
from mindflow_cli.render.theme import MINDFLOW_THEME


class ChatStreamRenderer:
    def __init__(self, console: Console) -> None:
        self.console = console
        self._response_open = False
        self._current_agent: str | None = None
        self._live_thought: Live | None = None

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
        if self._live_thought:
            self._live_thought.stop()
            self._live_thought = None

    def _get_agent_style(self, agent_type: str) -> str:
        return f"agent.{agent_type.lower()}"

    def _render_agent_header(self, agent_type: str) -> None:
        if self._current_agent == agent_type:
            return
        
        self._current_agent = agent_type
        style = self._get_agent_style(agent_type)
        header = Text.assemble(
            (f"  {agent_type.upper()}  ", style),
            (" acting on your request...", "info")
        )
        self.console.print()
        self.console.print(Panel(header, border_style="panel.border", padding=(0, 1)))

    def _render_step(self, event: StreamEvent) -> None:
        parsed = self._safe_json(event.data)
        if parsed is None:
            self.console.print(f"[step.start]Step[/]: {event.data}")
            return

        step_name = parsed.get("stepName") or "step"
        detail = parsed.get("detail") or ""
        action = parsed.get("action")
        
        if action == "start":
            prefix = "[step.start]→[/]"
            color = "step.start"
        elif action == "complete":
            prefix = "[step.complete]✓[/]"
            color = "step.complete"
        else:
            prefix = "[info]•[/]"
            color = "info"

        message = Text.assemble(
            (f"  {prefix} ", ""),
            (f"{step_name}", f"bold {color}"),
        )
        if detail:
            message.append(f" — {detail}", "info")
            
        self.console.print(message)

    def _render_tool_call(self, event: StreamEvent) -> None:
        parsed = self._safe_json(event.data)
        if parsed is None:
            self.console.print(f"  [tool.name]Tool call[/]: {event.data}")
            return

        name = parsed.get("name") or "unknown_tool"
        args = parsed.get("args")
        self.console.print(Text.assemble(
            ("  [", "panel.border"),
            ("TOOL", "action"),
            ("] ", "panel.border"),
            (f"{name}", "tool.name"),
            (f" (args={args})", "tool.args")
        ))

    def _render_tool_result(self, event: StreamEvent) -> None:
        parsed = self._safe_json(event.data)
        if parsed is None:
            self.console.print(f"  [tool.name]Tool result[/]: {event.data}")
            return

        name = parsed.get("name") or "unknown_tool"
        result = str(parsed.get("result", ""))
        compact = result if len(result) <= 220 else f"{result[:220]}..."
        self.console.print(Text.assemble(
            ("  [", "panel.border"),
            ("DONE", "success"),
            ("] ", "panel.border"),
            (f"{name}", "tool.name"),
            (f": {compact}", "info")
        ))

    def _render_response(self, event: StreamEvent) -> None:
        if not self._response_open:
            # First response chunk, close any open thoughts
            if self._live_thought:
                self._live_thought.stop()
                self._live_thought = None
            
            agent_style = self._get_agent_style(self._current_agent or "coder")
            
            sender_name = self._current_agent or "MindFlow"
            if event.meta and event.meta.model:
                provider = event.meta.provider or "AI"
                sender_name = f"{sender_name.capitalize()} ({provider}/{event.meta.model})"
                
            self.console.print(Text.assemble(
                (f"{sender_name} ", f"bold {agent_style}"),
                ("› ", "panel.border")
            ), end="")
            self._response_open = True
            
        self.console.print(Text(event.data, style="response.text"), end="")

    def _render_thought(self, thought: str) -> None:
        # Instead of a static line, we can use a Live spinner for thoughts
        if not self._live_thought:
            spinner = Spinner("dots", text=Text(f" {thought}", style="thinking"), style="thinking")
            self._live_thought = Live(spinner, console=self.console, transient=True, refresh_per_second=10)
            self._live_thought.start()
        else:
            # Update current live thought text if needed
            self._live_thought.update(Spinner("dots", text=Text(f" {thought}", style="thinking"), style="thinking"))

    def render(self, event: StreamEvent) -> None:
        # Handle agent metadata if present in event.meta
        if event.meta and "agent" in event.meta:
            self._render_agent_header(event.meta["agent"])

        if event.type == "response":
            self._render_response(event)
            return

        self._ensure_response_line_closed()

        if event.type == "thought":
            self._render_thought(event.data)
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
            self.console.print(Panel(f"[bold red]ERROR[/]\n{event.data}", border_style="error"))
            return
            
        if event.type == "done":
            self.console.print()
            self.console.print(Text("  ✓ Task completed successfully", style="success"))
            return

        self.console.print(f"[{event.type}] {event.data}")
