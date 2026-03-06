from __future__ import annotations

from rich.theme import Theme

MINDFLOW_THEME = Theme(
    {
        "agent.coder": "bold cyan",
        "agent.analyst": "bold blue",
        "agent.researcher": "bold green",
        "action": "bold magenta",
        "error": "bold red",
        "info": "dim",
        "panel.border": "bright_black",
        "response.text": "white",
        "step.complete": "green",
        "step.start": "yellow",
        "success": "bold green",
        "thinking": "italic bright_black",
        "tool.args": "dim",
        "tool.name": "cyan",
    }
)
