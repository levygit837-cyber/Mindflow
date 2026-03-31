from __future__ import annotations

import typer

from mindflow_cli.commands.chains import register_chains_commands
from mindflow_cli.commands.chat import register_chat_commands
from mindflow_cli.commands.health import register_health_commands
from mindflow_cli.commands.models import register_models_commands
from mindflow_cli.commands.settings import register_settings_commands
from mindflow_cli.commands.start import register_start_commands
from mindflow_cli.commands.tasks import register_tasks_commands
from mindflow_cli.commands.test_orchestrator import register_test_orchestrator_commands
from mindflow_cli.commands.workflow import register_workflow_commands

app = typer.Typer(help="MindFlow terminal-first CLI", invoke_without_command=True)

@app.callback()
def main(ctx: typer.Context) -> None:
    """MindFlow CLI - Modo interativo por padrão"""
    if ctx.invoked_subcommand is None:
        from rich.console import Console
        Console().print("[yellow]Dica: Rode `mindflow start` para iniciar o modo interativo. Para ajuda: `mindflow --help`[/]")


# Register all command groups
register_health_commands(app)
register_chat_commands(app)
register_workflow_commands(app)
register_start_commands(app)
register_test_orchestrator_commands(app)
register_chains_commands(app)
register_tasks_commands(app)
register_settings_commands(app)
register_models_commands(app)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
