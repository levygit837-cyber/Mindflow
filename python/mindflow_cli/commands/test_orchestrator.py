from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from mindflow_cli.client import MindFlowCliClient
from mindflow_cli.render.theme import MINDFLOW_THEME

console = Console(theme=MINDFLOW_THEME)


def register_test_orchestrator_commands(app: typer.Typer) -> None:
    """Register orchestrator test commands."""
    
    test_app = typer.Typer(help="Test orchestrator flows and agent decisions")
    app.add_typer(test_app, name="test")
    
    @test_app.command("orchestrator")
    def test_orchestrator_flow(
        message: str = typer.Option(..., "--message", "-m", help="Test message for orchestrator"),
        show_routing: bool = typer.Option(True, "--show-routing", help="Show routing decision process"),
        show_agent_selection: bool = typer.Option(True, "--show-agent-selection", help="Show agent selection process"),
        trace_execution: bool = typer.Option(False, "--trace-execution", help="Full execution trace"),
        provider: str | None = typer.Option(None, "--provider", help="LLM provider override"),
        model: str | None = typer.Option(None, "--model", help="LLM model override"),
        base_url: str | None = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Test the orchestrator flow with detailed output."""
        
        console.print()
        console.print(Panel(
            Text("🧪 Orchestrator Flow Test", style="bold yellow"),
            subtitle="Testing agent routing and execution",
            border_style="yellow"
        ))
        
        console.print(f"\n[bold]Test Message:[/] {message}")
        console.print(f"[dim]Provider: {provider or 'default'}[/]")
        console.print(f"[dim]Model: {model or 'default'}[/]")
        
        # Run orchestrator test
        _run_orchestrator_test(
            message=message,
            show_routing=show_routing,
            show_agent_selection=show_agent_selection,
            trace_execution=trace_execution,
            provider=provider,
            model=model,
            base_url=base_url
        )
    
    @test_app.command("routing")
    def test_routing_analysis(
        message: str = typer.Option(..., "--message", "-m", help="Message to analyze routing"),
        provider: str | None = typer.Option(None, "--provider", help="LLM provider"),
        model: str | None = typer.Option(None, "--model", help="LLM model"),
        base_url: str | None = typer.Option(None, "--base-url", help="Backend URL"),
    ) -> None:
        """Test only the routing analysis component."""
        
        console.print()
        console.print(Panel(
            Text("🔀 Routing Analysis Test", style="bold cyan"),
            subtitle="Testing intelligent routing decisions",
            border_style="cyan"
        ))
        
        console.print(f"\n[bold]Message:[/] {message}")
        
        # TODO: Implement direct routing test when backend endpoint is available
        console.print("[yellow]Direct routing test coming soon![/]")
        console.print("[dim]Use 'test orchestrator --show-routing' for now[/]")
    
    @test_app.command("agents")
    def test_agent_registry() -> None:
        """Test the agent registry and show available agents."""
        console.print()
        console.print(Panel(
            Text("🤖 Agent Registry Test", style="bold green"),
            subtitle="Testing agent registration and capabilities",
            border_style="green"
        ))
        
        # Show agent registry
        table = Table(title="Registered Agents")
        table.add_column("Agent Type", style="cyan", no_wrap=True)
        table.add_column("Status", style="white")
        table.add_column("Capabilities", style="green")
        table.add_column("Sandbox Mode", style="yellow")
        
        # Mock data for now - will be dynamic when backend integration is ready
        agents = [
            ("CODER", "✅ Available", "Code generation, debugging, architecture", "READ_ONLY"),
            ("ANALYST", "✅ Available", "Code analysis, security audits, review", "READ_ONLY"),
            ("RESEARCHER", "✅ Available", "Web search, documentation, research", "NONE"),
            ("ORCHESTRATOR", "✅ Available", "Multi-agent coordination", "NONE"),
        ]
        
        for agent_type, status, capabilities, sandbox in agents:
            table.add_row(agent_type, status, capabilities, sandbox)
        
        console.print(table)
    
    @test_app.command("scenarios")
    def test_scenarios(
        scenario: str = typer.Option("basic", "--scenario", help="Test scenario: basic, complex, multi-agent"),
        provider: str | None = typer.Option(None, "--provider", help="LLM provider"),
        model: str | None = typer.Option(None, "--model", help="LLM model"),
        base_url: str | None = typer.Option(None, "--base-url", help="Backend URL"),
    ) -> None:
        """Run predefined test scenarios."""
        
        scenarios = {
            "basic": [
                "Create a Python function to calculate fibonacci numbers",
                "Write a simple REST API endpoint",
                "Debug this Python code: print('hello world'",
            ],
            "complex": [
                "Analyze this codebase for security vulnerabilities and suggest fixes",
                "Design a microservices architecture for an e-commerce platform",
                "Refactor this legacy code to follow clean architecture principles",
            ],
            "multi-agent": [
                "Research best practices for API security, then implement a secure authentication system",
                "Analyze the performance bottlenecks in this system and optimize the code",
                "Create comprehensive documentation for this codebase including API docs and user guides",
            ]
        }
        
        messages = scenarios.get(scenario, scenarios["basic"])
        
        console.print()
        console.print(Panel(
            Text(f"🎭 {scenario.title()} Scenario Test", style="bold magenta"),
            subtitle=f"Running {len(messages)} test messages",
            border_style="magenta"
        ))
        
        for i, message in enumerate(messages, 1):
            console.print(f"\n[cyan]Test {i}/{len(messages)}:[/] {message}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Processing...", total=None)
                
                try:
                    _run_orchestrator_test(
                        message=message,
                        show_routing=True,
                        show_agent_selection=True,
                        trace_execution=False,
                        provider=provider,
                        model=model,
                        base_url=base_url
                    )
                    progress.update(task, description="✅ Completed")
                except Exception as e:
                    progress.update(task, description=f"❌ Failed: {e}")
                    console.print(f"[red]Test {i} failed: {e}[/]")


def _run_orchestrator_test(
    message: str,
    show_routing: bool,
    show_agent_selection: bool,
    trace_execution: bool,
    provider: str | None,
    model: str | None,
    base_url: str | None,
) -> None:
    """Run a single orchestrator test with detailed output."""
    
    client = MindFlowCliClient(base_url)
    renderer = OrchestratorTestRenderer(console, show_routing, show_agent_selection, trace_execution)
    
    try:
        # Track the orchestration process
        routing_decision = None
        selected_agent = None
        execution_steps = []
        response_chunks = []
        
        console.print("\n[bold yellow]🔄 Starting Orchestrator Flow...[/]")
        
        for event in client.stream_chat(
            message=message,
            provider=provider,
            model=model,
            debug_steps=True,  # Enable debug for detailed flow
            orchestrate=True,  # Enable orchestration
        ):
            renderer.render_test_event(event)
            
            # Extract key information for summary
            if event.type == "agent_step" and show_routing:
                if "routing" in event.data.lower():
                    routing_decision = event.data
            elif event.type == "response" and show_agent_selection:
                if selected_agent is None:
                    # Try to extract agent type from metadata or content
                    selected_agent = _extract_agent_from_event(event)
            elif event.type == "step":
                execution_steps.append(event.data)
            elif event.type == "response":
                response_chunks.append(event.data)
            elif event.type == "done":
                break
        
        # Show test summary
        _show_test_summary(
            message=message,
            routing_decision=routing_decision,
            selected_agent=selected_agent,
            execution_steps=execution_steps,
            response="".join(response_chunks).strip(),
            show_routing=show_routing,
            show_agent_selection=show_agent_selection,
        )
        
    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/]")
        raise


def _extract_agent_from_event(event) -> str | None:
    """Try to extract agent type from event."""
    # Check event meta first
    if event.meta and "agent" in event.meta:
        return event.meta["agent"]
    
    # Try to extract from content
    content = event.data.lower()
    agents = ["coder", "analyst", "researcher", "orchestrator"]
    for agent in agents:
        if agent in content:
            return agent.upper()
    
    return None


def _show_test_summary(
    message: str,
    routing_decision: str | None,
    selected_agent: str | None,
    execution_steps: list[str],
    response: str,
    show_routing: bool,
    show_agent_selection: bool,
) -> None:
    """Show a summary of the test results."""
    
    console.print("\n" + "="*60)
    console.print("[bold green]📊 Test Summary[/]")
    console.print("="*60)
    
    # Original message
    console.print(f"\n[bold]Original Message:[/] {message}")
    
    # Routing decision
    if show_routing and routing_decision:
        console.print("\n[bold cyan]🔀 Routing Decision:[/]")
        console.print(f"[dim]{routing_decision}[/]")
    
    # Selected agent
    if show_agent_selection and selected_agent:
        console.print(f"\n[bold green]🤖 Selected Agent:[/] {selected_agent}")
    elif show_agent_selection:
        console.print("\n[bold yellow]🤖 Selected Agent:[/] [dim]Not detected[/]")
    
    # Execution steps
    if execution_steps:
        console.print(f"\n[bold]⚡ Execution Steps:[/] {len(execution_steps)} steps")
        for i, step in enumerate(execution_steps[:3], 1):  # Show first 3 steps
            console.print(f"  [dim]{i}. {step[:100]}...[/]")
        if len(execution_steps) > 3:
            console.print(f"  [dim]... and {len(execution_steps) - 3} more steps[/]")
    
    # Response preview
    if response:
        preview = response[:200] + "..." if len(response) > 200 else response
        console.print("\n[bold]💬 Response Preview:[/]")
        console.print(f"[dim]{preview}[/]")
    
    console.print("\n" + "="*60)


class OrchestratorTestRenderer:
    """Enhanced renderer for orchestrator testing."""
    
    def __init__(
        self,
        console: Console,
        show_routing: bool,
        show_agent_selection: bool,
        trace_execution: bool
    ):
        self.console = console
        self.show_routing = show_routing
        self.show_agent_selection = show_agent_selection
        self.trace_execution = trace_execution
        self.step_count = 0
    
    def render_test_event(self, event) -> None:
        """Render events with orchestrator-specific formatting."""
        
        if event.type == "thought":
            if self.trace_execution:
                self.console.print(f"[dim]💭 {event.data}[/]")
        
        elif event.type == "agent_step":
            self.step_count += 1
            if self.show_routing and "routing" in event.data.lower():
                self.console.print(f"[cyan]🔀 Step {self.step_count}: {event.data}[/]")
            elif self.show_agent_selection and "agent" in event.data.lower():
                self.console.print(f"[green]🤖 Step {self.step_count}: {event.data}[/]")
            elif self.trace_execution:
                self.console.print(f"[dim]⚡ Step {self.step_count}: {event.data}[/]")
        
        elif event.type == "tool_call":
            if self.trace_execution:
                self.console.print(f"[yellow]🔧 Tool: {event.data}[/]")
        
        elif event.type == "tool_result":
            if self.trace_execution:
                result = event.data[:100] + "..." if len(event.data) > 100 else event.data
                self.console.print(f"[dim]✅ Tool Result: {result}[/]")
        
        elif event.type == "response":
            # Show response as it comes in
            self.console.print(Text(event.data, style="white"), end="")
        
        elif event.type == "done":
            self.console.print("\n[bold green]✅ Test Completed[/]")
        
        elif event.type == "error":
            self.console.print(f"\n[bold red]❌ Error: {event.data}[/]")
        
        else:
            if self.trace_execution:
                self.console.print(f"[dim]{event.type}: {event.data[:100]}...[/]")
