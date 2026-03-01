from __future__ import annotations

import typer
from rich.console import Console

from omnimind_cli.client import OmniMindCliClient
from omnimind_cli.render.chat_stream import ChatStreamRenderer

console = Console()
EXIT_COMMANDS = {"/exit", "/quit", "/q", "/sair"}
RESET_COMMANDS = {"/reset", "/clear", "/limpar"}


def build_client(base_url: str | None) -> OmniMindCliClient:
    return OmniMindCliClient(base_url=base_url)


def _compose_message_with_history(history: list[tuple[str, str]], user_message: str) -> str:
    if not history:
        return user_message

    lines = [
        "Use the following conversation context to answer the latest message.",
        "Conversation history:",
    ]
    for role, text in history[-8:]:
        speaker = "User" if role == "user" else "Assistant"
        lines.append(f"{speaker}: {text}")
    lines.append(f"User: {user_message}")
    lines.append("Assistant:")
    return "\n".join(lines)


def _stream_chat_once(
    *,
    client: OmniMindCliClient,
    renderer: ChatStreamRenderer,
    message: str,
    provider: str | None,
    model: str | None,
    debug_steps: bool,
) -> str:
    response_chunks: list[str] = []
    for event in client.stream_chat(
        message=message,
        provider=provider,
        model=model,
        debug_steps=debug_steps,
    ):
        renderer.render(event)
        if event.type == "response":
            response_chunks.append(event.data)
        if event.type == "done":
            break
    return "".join(response_chunks).strip()


def _run_chat(
    *,
    message: str,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    debug_steps: bool,
) -> None:
    client = build_client(base_url)
    renderer = ChatStreamRenderer(console)

    try:
        _stream_chat_once(
            client=client,
            renderer=renderer,
            message=message,
            provider=provider,
            model=model,
            debug_steps=debug_steps,
        )
    except Exception as exc:
        console.print(f"[bold red]Chat failed:[/] {exc}")
        raise typer.Exit(code=1) from exc


def register_chat_commands(app: typer.Typer) -> None:
    @app.command("chat")
    def chat(
        message: str | None = typer.Option(None, "--message", "-m", help="Prompt to send to the agent"),
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
        prompt = message or typer.prompt("Message")
        _run_chat(
            message=prompt,
            provider=provider,
            model=model,
            base_url=base_url,
            debug_steps=debug_steps,
        )

    @app.command("connect")
    def connect(
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
        client = build_client(base_url)
        try:
            health_payload = client.get_health()
        except Exception as exc:
            console.print(f"[bold red]Connection failed:[/] {exc}")
            raise typer.Exit(code=1) from exc

        status = str(health_payload.get("status", "unknown"))
        console.print(f"[green]Conexao estabelecida[/] (backend status: {status})")
        console.print("Comandos: /sair para encerrar, /reset para limpar contexto local.")

        renderer = ChatStreamRenderer(console)
        history: list[tuple[str, str]] = []

        while True:
            user_message = typer.prompt("You").strip()
            if not user_message:
                continue

            lowered = user_message.lower()
            if lowered in EXIT_COMMANDS:
                console.print("Encerrando chat.")
                return

            if lowered in RESET_COMMANDS:
                history.clear()
                console.print("[yellow]Contexto local limpo.[/]")
                continue

            composed_message = _compose_message_with_history(history, user_message)
            try:
                assistant_text = _stream_chat_once(
                    client=client,
                    renderer=renderer,
                    message=composed_message,
                    provider=provider,
                    model=model,
                    debug_steps=debug_steps,
                )
            except Exception as exc:
                console.print(f"[bold red]Chat failed:[/] {exc}")
                continue

            history.append(("user", user_message))
            if assistant_text:
                history.append(("assistant", assistant_text))
