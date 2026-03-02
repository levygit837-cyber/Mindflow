from __future__ import annotations

import typer

from omnimind_cli.commands.chat import register_chat_commands
from omnimind_cli.commands.health import register_health_commands
from omnimind_cli.commands.workflow import register_workflow_commands

app = typer.Typer(help="OmniMind terminal-first CLI", invoke_without_command=True)

@app.callback()
def main(ctx: typer.Context) -> None:
    """OmniMind CLI - Modo interativo por padrão"""
    if ctx.invoked_subcommand is None:
        from rich.console import Console
        Console().print("[yellow]Dica: Rode `omnimind connect` para iniciar o modo interativo. Para ajuda: `omnimind --help`[/]")


# Register all command groups
register_health_commands(app)
register_chat_commands(app)
register_workflow_commands(app)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
