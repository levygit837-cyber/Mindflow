from __future__ import annotations

import typer
from rich.console import Console

from mindflow_cli.client import MindFlowCliClient
from mindflow_cli.render.chat_stream import ChatStreamRenderer
from mindflow_cli.render.orchestrator_stream import OrchestratorStreamRenderer
from mindflow_cli.render.theme import MINDFLOW_THEME
from mindflow_cli.commands.settings import get_settings

console = Console(theme=MINDFLOW_THEME)
EXIT_COMMANDS = {"/exit", "/quit", "/q", "/sair"}
RESET_COMMANDS = {"/reset", "/clear", "/limpar"}
SETTINGS_COMMANDS = {"/settings", "/config"}


def build_client(base_url: str | None) -> MindFlowCliClient:
    settings = get_settings()
    api_url = base_url or settings.get("api_url")
    return MindFlowCliClient(base_url=api_url)


def _show_settings_help() -> None:
    """Show quick settings help in chat."""
    from mindflow_cli.commands.settings import load_settings
    
    settings = load_settings()
    
    console.print()
    console.print(Panel(
        "⚙️ Quick Settings",
        title="Current Configuration",
        border_style="cyan"
    ))
    
    console.print(f"[bold]🔗 API:[/] {settings.get('api_url', 'Not set')}")
    console.print(f"[bold]🤖 Agent:[/] {settings.get('default_agent', 'auto')}")
    console.print(f"[bold]🔄 Auto-Orchestrate:[/] {settings.get('auto_orchestrate', True)}")
    console.print(f"[bold]🐛 Debug:[/] {settings.get('debug_mode', False)}")
    
    console.print("\n[bold cyan]Commands:[/]")
    console.print("  /settings show - Show all settings")
    console.print("  /settings set <key> <value> - Change setting")
    console.print("  /settings reset - Reset to defaults")
    console.print("\n[dim]Use 'mindflow settings' for full configuration.[/]")


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
    client: MindFlowCliClient,
    renderer: ChatStreamRenderer | OrchestratorStreamRenderer,
    message: str,
    provider: str | None,
    model: str | None,
    debug_steps: bool,
    agent_type: str | None = None,
    orchestrate: bool = False,
) -> str:
    response_chunks: list[str] = []
    seen_done = False
    for event in client.stream_chat(
        message=message,
        provider=provider,
        model=model,
        debug_steps=debug_steps,
        agent_type=agent_type,
        orchestrate=orchestrate,
    ):
        renderer.render(event)
        if event.type == "response":
            response_chunks.append(event.data)
        if event.type == "done":
            seen_done = True
            break
    if not seen_done:
        raise RuntimeError("No terminal done event in stream")
    return "".join(response_chunks).strip()


def _run_chat(
    *,
    message: str,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    debug_steps: bool,
    orchestrate: bool = False,
) -> None:
    settings = get_settings()
    
    # Use settings defaults if not provided
    if not provider:
        provider = settings.get("default_provider", "vertexai")
    if not model:
        model = settings.get("default_model", "gemini-3-flash")
    if not base_url:
        base_url = settings.get("api_url")
    
    # Auto-orchestration based on settings
    if orchestrate is None:
        orchestrate = settings.get("auto_orchestrate", True)
    
    client = build_client(base_url)
    renderer: ChatStreamRenderer | OrchestratorStreamRenderer = (
        OrchestratorStreamRenderer(console) if orchestrate else ChatStreamRenderer(console)
    )

    try:
        _stream_chat_once(
            client=client,
            renderer=renderer,
            message=message,
            provider=provider,
            model=model,
            debug_steps=debug_steps or settings.get("debug_mode", False),
            orchestrate=orchestrate,
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
        orchestrate: bool = typer.Option(False, "--orchestrate", help="Use orchestrator (route to specialist agents)"),
        base_url: str | None = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        prompt = message or typer.prompt("Message")
        _run_chat(
            message=prompt,
            provider=provider,
            model=model,
            base_url=base_url,
            debug_steps=debug_steps,
            orchestrate=orchestrate,
        )

    @app.command("connect")
    def connect(
        agent: str = typer.Option("coder", "--agent", "-a", help="Personalidade do agente (coder, analyst, researcher, etc)"),
        provider: str = typer.Option("vertexai", "--provider", help="Provider override"),
        model: str = typer.Option("gemini-3-flash-preview", "--model", help="Model override"),
        debug_steps: bool = typer.Option(False, "--debug-steps", help="Enable debug-oriented stream flags"),
        orchestrate: bool = typer.Option(False, "--orchestrate", "-o", help="Usar orquestrador inteligente (roteia para agente especialista)"),
        base_url: str | None = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        settings = get_settings()
        client = build_client(base_url)
        try:
            health_payload = client.get_health()
        except Exception as exc:
            console.print(f"[bold red]Connection failed:[/] {exc}")
            raise typer.Exit(code=1) from exc

        status = str(health_payload.get("status", "unknown"))
        console.print(f"[green]Conexao estabelecida[/] (backend status: {status})")
        if orchestrate:
            console.print(f"Modo: [bold]Orquestrador Inteligente[/] via {provider} / {model}")
        else:
            console.print(f"Modo: [bold]Agente Direto ({agent})[/] via {provider} / {model}")
        console.print("Comandos: /sair para encerrar, /reset para limpar contexto local.")

        renderer: ChatStreamRenderer | OrchestratorStreamRenderer = (
            OrchestratorStreamRenderer(console) if orchestrate else ChatStreamRenderer(console)
        )
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

            if lowered in SETTINGS_COMMANDS:
                _show_settings_help()
                continue

            # In orchestrator mode, send raw message (orchestrator handles context);
            # in direct mode, include local history for continuity.
            if orchestrate:
                send_message = user_message
            else:
                send_message = _compose_message_with_history(history, user_message)

            try:
                assistant_text = _stream_chat_once(
                    client=client,
                    renderer=renderer,
                    message=send_message,
                    provider=provider,
                    model=model,
                    debug_steps=debug_steps or settings.get("debug_mode", False),
                    agent_type=None if orchestrate else agent,
                    orchestrate=orchestrate,
                )
            except Exception as exc:
                console.print(f"[bold red]Chat failed:[/] {exc}")
                continue

            history.append(("user", user_message))
            if assistant_text:
                history.append(("assistant", assistant_text))
