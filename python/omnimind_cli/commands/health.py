from __future__ import annotations

import typer
from rich.console import Console

from omnimind_cli.commands.chat import build_client

console = Console()


def register_health_commands(app: typer.Typer) -> None:
    @app.command("health")
    def health(
        base_url: str | None = typer.Option(
            None,
            "--base-url",
            envvar="OMNIMIND_API_URL",
            help="OmniMind backend base URL",
        ),
    ) -> None:
        client = build_client(base_url)
        try:
            payload = client.get_health()
        except Exception as exc:
            console.print(f"[bold red]Health check failed:[/] {exc}")
            raise typer.Exit(code=1) from exc

        status = str(payload.get("status", "unknown"))
        console.print(f"Backend health: [bold]{status}[/]")
