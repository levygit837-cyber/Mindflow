"""Models management commands for MindFlow CLI."""

from __future__ import annotations

import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from mindflow_cli.client import MindFlowCliClient
from mindflow_cli.commands.chat import build_client
from mindflow_cli.commands.settings import get_settings
from mindflow_cli.render.theme import MINDFLOW_THEME

console = Console(theme=MINDFLOW_THEME)


def register_models_commands(app: typer.Typer) -> None:
    """Register models management commands."""
    
    models_app = typer.Typer(help="Models testing and management")
    app.add_typer(models_app, name="models")
    
    @models_app.command("list")
    def list_models(
        provider: str = typer.Option(None, "--provider", "-p", help="Filter by provider"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """List available models."""
        try:
            client = build_client(base_url)
            
            params = {}
            if provider:
                params["provider"] = provider
            
            with httpx.Client() as http_client:
                response = http_client.get(
                    f"{client.base_url}/v1/providers",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                providers = data.get("providers", [])
                
                console.print()
                console.print(Panel(
                    Text("🤖 Available Models", style="bold cyan"),
                    subtitle="Model Information",
                    border_style="cyan"
                ))
                
                for provider_info in providers:
                    provider_name = provider_info.get("name", "Unknown")
                    models = provider_info.get("models", [])
                    
                    console.print(f"\n[bold]{provider_name}:[/]")
                    if models:
                        table = Table()
                        table.add_column("Model", style="white")
                        table.add_column("Type", style="yellow")
                        table.add_column("Capabilities", style="green")
                        table.add_column("Status", style="magenta")
                        
                        for model in models:
                            capabilities = ", ".join(model.get("capabilities", []))
                            table.add_row(
                                model.get("name", "N/A"),
                                model.get("type", "N/A"),
                                capabilities[:30] + "..." if len(capabilities) > 30 else capabilities,
                                "✅ Available"
                            )
                        
                        console.print(table)
                    else:
                        console.print("[yellow]No models available[/]")
                
            else:
                console.print(f"[red]Error: {data.get('message', 'Unknown error')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to list models: {e}[/]")
    
    @models_app.command("test")
    def test_model(
        model: str = typer.Argument(..., help="Model name to test"),
        message: str = typer.Option("Hello, how are you?", "--message", "-m", help="Test message"),
        provider: str = typer.Option(None, "--provider", "-p", help="Provider override"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Test a specific model."""
        try:
            settings = get_settings()
            client = build_client(base_url or settings.get("api_url"))
            
            console.print()
            console.print(Panel(
                Text(f"🧪 Testing Model: {model}", style="bold yellow"),
                subtitle="Model Test",
                border_style="yellow"
            ))
            
            console.print(f"[bold]Test Message:[/] {message}")
            console.print(f"[bold]Provider:[/] {provider or settings.get('default_provider', 'default')}")
            console.print(f"[bold]Model:[/] {model}")
            
            # Simple test via chat endpoint
            from mindflow_cli.commands.chat import _stream_chat_once
            from mindflow_cli.render.chat_stream import ChatStreamRenderer
            
            renderer = ChatStreamRenderer(console)
            
            response = _stream_chat_once(
                client=client,
                renderer=renderer,
                message=message,
                provider=provider,
                model=model,
                debug_steps=True,
                agent_type=None,
                orchestrate=False,
            )
            
            console.print(f"\n[bold green]✅ Model test completed[/]")
            response_preview = response[:200] + "..." if len(response) > 200 else response
            console.print(f"[bold]Response:[/] {response_preview}")
            
        except Exception as e:
            console.print(f"[red]Failed to test model: {e}[/]")
    
    @models_app.command("compare")
    def compare_models(
        models: str = typer.Argument(..., help="Comma-separated model names to compare"),
        message: str = typer.Option("Compare these models on this task", "--message", "-m", help="Comparison test message"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Compare multiple models."""
        model_list = [m.strip() for m in models.split(",")]
        
        console.print()
        console.print(Panel(
            Text("⚖️ Model Comparison", style="bold cyan"),
            subtitle=f"Comparing {len(model_list)} models",
            border_style="cyan"
        ))
        
        for i, model in enumerate(model_list, 1):
            console.print(f"\n[bold]Testing {i}/{len(model_list)}: {model}[/]")
            
            try:
                settings = get_settings()
                client = build_client(base_url or settings.get("api_url"))
                
                from mindflow_cli.commands.chat import _stream_chat_once
                from mindflow_cli.render.chat_stream import ChatStreamRenderer
                
                renderer = ChatStreamRenderer(console)
                
                response = _stream_chat_once(
                    client=client,
                    renderer=renderer,
                    message=message,
                    provider=None,
                    model=model,
                    debug_steps=False,
                    agent_type=None,
                    orchestrate=False,
                )
                
                console.print(f"[dim]Response: {response[:100]}...[/]")
                
            except Exception as e:
                console.print(f"[red]Error with {model}: {e}[/]")
        
        console.print("\n[bold green]✅ Comparison completed[/]")
