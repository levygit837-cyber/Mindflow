from __future__ import annotations

import typer

from omnimind_cli.commands.chat import _run_chat


def register_workflow_commands(app: typer.Typer) -> None:
    workflow_app = typer.Typer(help="Workflow operations")
    app.add_typer(workflow_app, name="workflow")

    @workflow_app.command("run")
    def workflow_run(
        message: str = typer.Option(..., "--message", "-m", help="Workflow prompt"),
        provider: str | None = typer.Option(None, "--provider", help="Provider override"),
        model: str | None = typer.Option(None, "--model", help="Model override"),
        debug_steps: bool = typer.Option(False, "--debug-steps", help="Enable debug-oriented stream flags"),
        base_url: str | None = typer.Option(
            None,
            "--base-url",
            envvar="OMNIMIND_API_URL",
            help="OmniMind backend base URL",
        ),
    ) -> None:
        _run_chat(
            message=message,
            provider=provider,
            model=model,
            base_url=base_url,
            debug_steps=debug_steps,
        )
