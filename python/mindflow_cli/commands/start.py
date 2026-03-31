from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from mindflow_cli.render.theme import MINDFLOW_THEME

console = Console(theme=MINDFLOW_THEME)


def register_start_commands(app: typer.Typer) -> None:
    """Register start commands for the MindFlow CLI."""
    
    @app.command("start")
    def start_app(
        mode: str = typer.Option("interactive", "--mode", help="Mode: interactive, test, benchmark"),
        provider: str | None = typer.Option(None, "--provider", help="LLM provider"),
        model: str | None = typer.Option(None, "--model", help="LLM model"),
        debug_orchestrator: bool = typer.Option(False, "--debug-orchestrator", help="Show orchestrator decisions"),
        save_session: bool = typer.Option(True, "--save-session", help="Save session logs"),
        base_url: str | None = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Start the MindFlow application with interactive interface."""
        
        console.print()
        console.print(Panel(
            Text("🚀 MindFlow CLI", style="bold blue"),
            subtitle="Interactive Agent Orchestration System",
            border_style="blue"
        ))
        
        if mode == "interactive":
            _start_interactive_mode(provider, model, debug_orchestrator, save_session, base_url)
        elif mode == "test":
            _start_test_mode(provider, model, debug_orchestrator, base_url)
        elif mode == "benchmark":
            _start_benchmark_mode(provider, model, base_url)
        else:
            console.print(f"[red]Unknown mode: {mode}[/]")
            raise typer.Exit(code=1)


def _start_interactive_mode(
    provider: str | None,
    model: str | None,
    debug_orchestrator: bool,
    save_session: bool,
    base_url: str | None,
) -> None:
    """Start interactive mode with Rich console."""
    from rich.prompt import Prompt
    from rich.table import Table
    
    console.print("\n[bold green]🎯 Interactive Mode Started[/]")
    console.print(f"[dim]Provider: {provider or 'default'}[/]")
    console.print(f"[dim]Model: {model or 'default'}[/]")
    console.print(f"[dim]Debug Orchestrator: {debug_orchestrator}[/]")
    console.print(f"[dim]Save Session: {save_session}[/]")
    
    # Show available agents
    table = Table(title="Available Agents")
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Specialization", style="green")
    
    table.add_row("CODER", "Implementation & Development", "Code generation, debugging, architecture")
    table.add_row("ANALYST", "Code Analysis & Review", "Security audits, code review, analysis")
    table.add_row("RESEARCHER", "Research & Documentation", "Web search, documentation, comparison")
    table.add_row("ORCHESTRATOR", "Multi-agent Coordination", "Task delegation, session management")
    
    console.print(table)
    console.print("\n[dim]Type your message below, or use /help for commands[/]")
    
    # Interactive loop
    while True:
        try:
            message = Prompt.ask("\n[bold blue]You[/]")
            
            if message.lower() in {"/exit", "/quit", "/q"}:
                console.print("[yellow]👋 Goodbye![/]")
                break
            elif message.lower() == "/help":
                _show_help()
                continue
            elif message.lower() == "/agents":
                console.print(table)
                continue
            elif not message.strip():
                continue
            
            # Process message through orchestrator
            _process_message_interactive(message, provider, model, debug_orchestrator, base_url)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Interrupted. Goodbye![/]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


def _start_test_mode(
    provider: str | None,
    model: str | None,
    debug_orchestrator: bool,
    base_url: str | None,
) -> None:
    """Start test mode for orchestrator flow testing."""
    console.print("\n[bold yellow]🧪 Test Mode Started[/]")
    console.print("[dim]Use 'mindflow test orchestrator' for specific tests[/]")
    
    # Import test orchestrator command
    from mindflow_cli.commands.test_orchestrator import test_orchestrator_flow
    
    # Run a quick test
    test_messages = [
        "Create a Python function that calculates factorial",
        "Analyze this codebase for security vulnerabilities", 
        "Research the best practices for API design"
    ]
    
    console.print("\n[bold]Running quick orchestrator tests...[/]")
    
    for i, message in enumerate(test_messages, 1):
        console.print(f"\n[cyan]Test {i}: {message}[/]")
        try:
            test_orchestrator_flow(
                message=message,
                show_routing=True,
                show_agent_selection=True,
                trace_execution=debug_orchestrator,
                provider=provider,
                model=model,
                base_url=base_url
            )
        except Exception as e:
            console.print(f"[red]Test {i} failed: {e}[/]")


def _start_benchmark_mode(
    provider: str | None,
    model: str | None,
    base_url: str | None,
) -> None:
    """Start benchmark mode for performance testing."""
    console.print("\n[bold magenta]📊 Benchmark Mode Started[/]")
    console.print("[dim]Running performance benchmarks...[/]")
    
    # TODO: Implement benchmarking
    console.print("[yellow]Benchmark mode coming soon![/]")


def _process_message_interactive(
    message: str,
    provider: str | None,
    model: str | None,
    debug_orchestrator: bool,
    base_url: str | None,
) -> None:
    """Process a message through the orchestrator interactively."""
    from mindflow_cli.client import MindFlowCliClient
    from mindflow_cli.render.orchestrator_stream import OrchestratorStreamRenderer

    client = MindFlowCliClient(base_url)
    renderer = OrchestratorStreamRenderer(console)
    
    try:
        # Stream the response through orchestrator
        response_chunks = []
        seen_done = False
        
        for event in client.stream_chat(
            message=message,
            provider=provider,
            model=model,
            debug_steps=debug_orchestrator,
            orchestrate=True,  # Enable orchestration
        ):
            renderer.render(event)
            
            if event.type == "response":
                response_chunks.append(event.data)
            elif event.type == "done":
                seen_done = True
                break
        
        if not seen_done:
            console.print("[yellow]⚠️ Stream ended without completion[/]")
            
    except Exception as e:
        console.print(f"[red]Error processing message: {e}[/]")


def _show_help() -> None:
    """Show help information."""
    from rich.table import Table
    
    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    
    table.add_row("/help", "Show this help message")
    table.add_row("/agents", "Show available agents")
    table.add_row("/exit, /quit, /q", "Exit the application")
    
    console.print(table)
