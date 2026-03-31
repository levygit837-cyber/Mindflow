"""Chains management commands for MindFlow CLI."""

from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mindflow_cli.commands.chat import build_client
from mindflow_cli.render.theme import MINDFLOW_THEME

console = Console(theme=MINDFLOW_THEME)


def register_chains_commands(app: typer.Typer) -> None:
    """Register chains management commands."""
    
    chains_app = typer.Typer(help="Chains management and testing")
    app.add_typer(chains_app, name="chains")
    
    @chains_app.command("list")
    def list_chains(
        capability: str = typer.Option(None, "--capability", "-c", help="Filter by capability"),
        complexity: str = typer.Option(None, "--complexity", help="Filter by complexity"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """List all available chains."""
        try:
            client = build_client(base_url)
            
            # Build query parameters
            params = {}
            if capability:
                params["capability"] = capability
            if complexity:
                params["complexity"] = complexity
            
            # Make request to chains API
            with httpx.Client() as http_client:
                response = http_client.get(
                    f"{client.base_url}/v1/chains",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                chains = data.get("chains", [])
                total = data.get("total", 0)
                
                console.print()
                console.print(Panel(
                    Text("🔗 Available Chains", style="bold cyan"),
                    subtitle=f"{total} chains found",
                    border_style="cyan"
                ))
                
                if chains:
                    table = Table(title="Chains")
                    table.add_column("Chain ID", style="cyan", no_wrap=True)
                    table.add_column("Name", style="white")
                    table.add_column("Complexity", style="yellow")
                    table.add_column("Capabilities", style="green")
                    table.add_column("Agents", style="magenta")
                    
                    for chain in chains:
                        capabilities = ", ".join(chain.get("capabilities", []))
                        agents = ", ".join(chain.get("required_agents", []))
                        
                        table.add_row(
                            chain.get("chain_id", "N/A"),
                            chain.get("name", "N/A"),
                            chain.get("complexity", "N/A"),
                            capabilities[:50] + "..." if len(capabilities) > 50 else capabilities,
                            agents[:30] + "..." if len(agents) > 30 else agents
                        )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No chains found[/]")
            else:
                console.print(f"[red]Error: {data.get('message', 'Unknown error')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to list chains: {e}[/]")
    
    @chains_app.command("info")
    def get_chain_info(
        chain_id: str = typer.Argument(..., help="Chain identifier"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Get detailed information about a specific chain."""
        try:
            client = build_client(base_url)
            
            with httpx.Client() as http_client:
                response = http_client.get(f"{client.base_url}/v1/chains/{chain_id}")
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                chain = data.get("chain", {})
                stats = data.get("stats", {})
                
                console.print()
                console.print(Panel(
                    Text(f"🔗 {chain.get('name', chain_id)}", style="bold cyan"),
                    subtitle="Chain Information",
                    border_style="cyan"
                ))
                
                # Basic info
                console.print(f"[bold]Chain ID:[/] {chain.get('chain_id')}")
                console.print(f"[bold]Description:[/] {chain.get('description', 'N/A')}")
                console.print(f"[bold]Version:[/] {chain.get('version', 'N/A')}")
                console.print(f"[bold]Complexity:[/] {chain.get('complexity', 'N/A')}")
                
                # Capabilities
                capabilities = chain.get("capabilities", [])
                if capabilities:
                    console.print("[bold]Capabilities:[/]")
                    for cap in capabilities:
                        console.print(f"  • {cap}")
                
                # Required agents
                agents = chain.get("required_agents", [])
                if agents:
                    console.print("[bold]Required Agents:[/]")
                    for agent in agents:
                        console.print(f"  • {agent}")
                
                # Configuration
                config = chain.get("default_config", {})
                if config:
                    console.print("[bold]Default Configuration:[/]")
                    for key, value in config.items():
                        console.print(f"  {key}: {value}")
                
                # Statistics
                if stats:
                    console.print("[bold]Execution Statistics:[/]")
                    console.print(f"  Total Executions: {stats.get('total_executions', 0)}")
                    console.print(f"  Successful: {stats.get('successful_executions', 0)}")
                    console.print(f"  Failed: {stats.get('failed_executions', 0)}")
                    console.print(f"  Average Time: {stats.get('average_execution_time', 0):.2f}s")
                    console.print(f"  Last Execution: {stats.get('last_execution', 'Never')}")
                
            else:
                console.print(f"[red]Error: {data.get('message', 'Chain not found')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to get chain info: {e}[/]")
    
    @chains_app.command("execute")
    def execute_chain(
        chain_id: str = typer.Argument(..., help="Chain identifier"),
        message: str = typer.Option(..., "--message", "-m", help="Message/context for chain execution"),
        context_file: str = typer.Option(None, "--context-file", "-f", help="JSON file with execution context"),
        priority: int = typer.Option(0, "--priority", "-p", help="Execution priority (higher = more priority)"),
        request_id: str = typer.Option(None, "--request-id", help="Custom request ID"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Execute a specific chain."""
        try:
            client = build_client(base_url)
            
            # Load context from file if provided
            execution_context = {}
            if context_file:
                import json
                with open(context_file) as f:
                    execution_context = json.load(f)
            
            # Prepare request payload
            payload = {
                "context": execution_context,
                "priority": priority,
                "request_id": request_id
            }
            
            console.print()
            console.print(Panel(
                Text(f"🚀 Executing Chain: {chain_id}", style="bold green"),
                subtitle="Chain Execution",
                border_style="green"
            ))
            console.print(f"[bold]Message:[/] {message}")
            
            # Execute chain via streaming
            with httpx.Client(timeout=None) as http_client, httpx.stream(
                "POST",
                f"{client.base_url}/v1/chains/{chain_id}/execute",
                json=payload,
                headers={"Accept": "text/event-stream"}
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            import json
                            event = json.loads(line)
                            
                            if event.get("type") == "response":
                                console.print(event.get("data", ""), end="")
                            elif event.get("type") == "error":
                                console.print(f"\n[red]Error: {event.get('data')}[/]")
                            elif event.get("type") == "done":
                                console.print("\n[bold green]✅ Chain execution completed[/]")
                                break
                                
                        except json.JSONDecodeError:
                            continue
                                
        except Exception as e:
            console.print(f"[red]Failed to execute chain: {e}[/]")
    
    @chains_app.command("find")
    def find_chains(
        task_type: str = typer.Option(..., "--task", "-t", help="Task type to find chains for"),
        complexity: str = typer.Option(None, "--complexity", help="Filter by complexity"),
        capabilities: str = typer.Option(None, "--capabilities", help="Comma-separated list of required capabilities"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Find chains suitable for a specific task type."""
        try:
            client = build_client(base_url)
            
            # Prepare request payload
            payload = {
                "task_type": task_type
            }
            if complexity:
                payload["complexity"] = complexity
            if capabilities:
                payload["required_capabilities"] = [cap.strip() for cap in capabilities.split(",")]
            
            with httpx.Client() as http_client:
                response = http_client.post(
                    f"{client.base_url}/v1/chains/find",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                chains = data.get("chains", [])
                total = data.get("total", 0)
                
                console.print()
                console.print(Panel(
                    Text(f"🔍 Chains for Task: {task_type}", style="bold cyan"),
                    subtitle=f"{total} suitable chains found",
                    border_style="cyan"
                ))
                
                if chains:
                    table = Table(title="Suitable Chains")
                    table.add_column("Chain ID", style="cyan", no_wrap=True)
                    table.add_column("Name", style="white")
                    table.add_column("Complexity", style="yellow")
                    table.add_column("Score", style="green")
                    
                    for chain in chains:
                        table.add_row(
                            chain.get("chain_id", "N/A"),
                            chain.get("name", "N/A"),
                            chain.get("complexity", "N/A"),
                            "🎯"  # Placeholder for suitability score
                        )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No suitable chains found[/]")
            else:
                console.print(f"[red]Error: {data.get('message', 'Unknown error')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to find chains: {e}[/]")
    
    @chains_app.command("stats")
    def get_chain_stats(
        chain_id: str = typer.Argument(..., help="Chain identifier"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Get execution statistics for a specific chain."""
        try:
            client = build_client(base_url)
            
            with httpx.Client() as http_client:
                response = http_client.get(f"{client.base_url}/v1/chains/{chain_id}/stats")
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                stats = data.get("stats", {})
                
                console.print()
                console.print(Panel(
                    Text(f"📊 {chain_id} Statistics", style="bold cyan"),
                    subtitle="Execution Statistics",
                    border_style="cyan"
                ))
                
                console.print(f"[bold]Total Executions:[/] {stats.get('total_executions', 0)}")
                console.print(f"[bold]Successful:[/] {stats.get('successful_executions', 0)}")
                console.print(f"[bold]Failed:[/] {stats.get('failed_executions', 0)}")
                console.print(f"[bold]Success Rate:[/] {stats.get('success_rate', 0):.1%}")
                console.print(f"[bold]Average Time:[/] {stats.get('average_execution_time', 0):.2f}s")
                console.print(f"[bold]Total Time:[/] {stats.get('total_execution_time', 0):.2f}s")
                console.print(f"[bold]Last Execution:[/] {stats.get('last_execution', 'Never')}")
                
            else:
                console.print(f"[red]Error: {data.get('message', 'Stats not found')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to get chain stats: {e}[/]")
