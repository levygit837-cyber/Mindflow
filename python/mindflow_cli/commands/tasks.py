"""Tasks management commands for MindFlow CLI."""

from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from mindflow_cli.commands.chat import build_client
from mindflow_cli.render.theme import MINDFLOW_THEME

console = Console(theme=MINDFLOW_THEME)


def register_tasks_commands(app: typer.Typer) -> None:
    """Register tasks management commands."""
    
    tasks_app = typer.Typer(help="Tasks management and monitoring")
    app.add_typer(tasks_app, name="tasks")
    
    @tasks_app.command("list")
    def list_tasks(
        session_id: str = typer.Option(None, "--session", "-s", help="Filter by session ID"),
        status: str = typer.Option(None, "--status", help="Filter by status"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """List tasks with optional filtering."""
        try:
            client = build_client(base_url)
            
            if session_id:
                # Get tasks for specific session
                with httpx.Client() as http_client:
                    response = http_client.get(f"{client.base_url}/v1/tasks/session/{session_id}")
                    response.raise_for_status()
                    data = response.json()
                
                if data.get("success"):
                    tasks = data.get("tasks", [])
                    total = data.get("total", 0)
                    
                    console.print()
                    console.print(Panel(
                        Text(f"📋 Tasks for Session: {session_id}", style="bold cyan"),
                        subtitle=f"{total} tasks found",
                        border_style="cyan"
                    ))
                else:
                    console.print(f"[red]Error: {data.get('message', 'Unknown error')}[/]")
            else:
                console.print("[yellow]Please provide a session ID with --session[/]")
                return
                
            if tasks:
                table = Table(title="Tasks")
                table.add_column("Task ID", style="cyan", no_wrap=True)
                table.add_column("Description", style="white")
                table.add_column("Status", style="yellow")
                table.add_column("Complexity", style="green")
                table.add_column("Agent", style="magenta")
                table.add_column("Created", style="dim")
                
                for task in tasks:
                    status_style = {
                        "completed": "green",
                        "in_progress": "yellow", 
                        "pending": "dim",
                        "failed": "red",
                        "cancelled": "red"
                    }.get(task.get("status", "pending"), "white")
                    
                    table.add_row(
                        task.get("task_id", "N/A"),
                        task.get("task_description", "N/A")[:40] + "..." if len(task.get("task_description", "")) > 40 else task.get("task_description", "N/A"),
                        f"[{status_style}]{task.get('status', 'N/A')}[/{status_style}]",
                        task.get("complexity_level", "N/A"),
                        task.get("agent_type", "N/A"),
                        task.get("created_at", "N/A")[:10]
                    )
                
                console.print(table)
            else:
                console.print("[yellow]No tasks found[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to list tasks: {e}[/]")
    
    @tasks_app.command("status")
    def get_task_status(
        task_id: str = typer.Argument(..., help="Task identifier"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Get status and information for a specific task."""
        try:
            client = build_client(base_url)
            
            with httpx.Client() as http_client:
                response = http_client.get(f"{client.base_url}/v1/tasks/{task_id}")
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                task = data.get("task", {})
                
                console.print()
                console.print(Panel(
                    Text(f"📋 Task Status: {task_id}", style="bold cyan"),
                    subtitle="Task Information",
                    border_style="cyan"
                ))
                
                console.print(f"[bold]Task ID:[/] {task.get('task_id')}")
                console.print(f"[bold]Description:[/] {task.get('task_description', 'N/A')}")
                console.print(f"[bold]Status:[/] {task.get('status', 'N/A')}")
                console.print(f"[bold]Complexity:[/] {task.get('complexity_level', 'N/A')}")
                console.print(f"[bold]Session ID:[/] {task.get('session_id', 'N/A')}")
                console.print(f"[bold]Created:[/] {task.get('created_at', 'N/A')}")
                console.print(f"[bold]Updated:[/] {task.get('updated_at', 'N/A')}")
                
            else:
                console.print(f"[red]Error: {data.get('message', 'Task not found')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to get task status: {e}[/]")
    
    @tasks_app.command("cancel")
    def cancel_task(
        task_id: str = typer.Argument(..., help="Task identifier"),
        reason: str = typer.Option("User requested cancellation", "--reason", "-r", help="Reason for cancellation"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Cancel execution of a specific task."""
        try:
            client = build_client(base_url)
            
            with httpx.Client() as http_client:
                response = http_client.post(
                    f"{client.base_url}/v1/tasks/{task_id}/cancel",
                    json={"reason": reason}
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                console.print()
                console.print(Panel(
                    Text(f"⏹ Task Cancelled: {task_id}", style="bold yellow"),
                    subtitle="Task Cancellation",
                    border_style="yellow"
                ))
                
                cancel_result = data.get("cancel_result", {})
                console.print(f"[bold]Status:[/] {cancel_result.get('status', 'N/A')}")
                console.print(f"[bold]Cancelled At:[/] {cancel_result.get('cancelled_at', 'N/A')}")
                console.print(f"[bold]Reason:[/] {cancel_result.get('reason', 'N/A')}")
                
            else:
                console.print(f"[red]Error: {data.get('message', 'Cancellation failed')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to cancel task: {e}[/]")
    
    @tasks_app.command("retry")
    def retry_task(
        task_id: str = typer.Argument(..., help="Task identifier"),
        retry_subtasks: bool = typer.Option(False, "--retry-subtasks", help="Retry failed subtasks individually"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Retry execution of a failed or cancelled task."""
        try:
            client = build_client(base_url)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Retrying task...", total=None)
                
                with httpx.Client() as http_client:
                    response = http_client.post(
                        f"{client.base_url}/v1/tasks/{task_id}/retry",
                        json={"retry_subtasks": retry_subtasks}
                    )
                    response.raise_for_status()
                    data = response.json()
                
                progress.update(task, description="✅ Task retry initiated")
            
            if data.get("success"):
                console.print()
                console.print(Panel(
                    Text(f"🔄 Task Retry: {task_id}", style="bold green"),
                    subtitle="Task Retry",
                    border_style="green"
                ))
                
                retry_result = data.get("retry_result", {})
                console.print(f"[bold]Status:[/] {retry_result.get('status', 'N/A')}")
                console.print(f"[bold]Retry Attempt:[/] {retry_result.get('retry_attempt', 'N/A')}")
                console.print(f"[bold]Retry Subtasks:[/] {retry_result.get('retry_subtasks', 'N/A')}")
                console.print(f"[bold]Initiated At:[/] {retry_result.get('initiated_at', 'N/A')}")
                
            else:
                console.print(f"[red]Error: {data.get('message', 'Retry failed')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to retry task: {e}[/]")
    
    @tasks_app.command("progress")
    def get_task_progress(
        task_id: str = typer.Argument(..., help="Task identifier"),
        watch: bool = typer.Option(False, "--watch", "-w", help="Watch progress in real-time"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Get real-time progress information for a task."""
        try:
            client = build_client(base_url)
            
            if watch:
                # Watch mode - continuous updates
                console.print()
                console.print(Panel(
                    Text(f"👀 Watching Task: {task_id}", style="bold cyan"),
                    subtitle="Real-time Progress Monitoring",
                    border_style="cyan"
                ))
                
                import time
                try:
                    while True:
                        with httpx.Client() as http_client:
                            response = http_client.get(f"{client.base_url}/v1/tasks/{task_id}/progress")
                            response.raise_for_status()
                            data = response.json()
                        
                        if data.get("success"):
                            progress = data.get("progress", {})
                            
                            # Clear previous lines and show updated progress
                            console.print("\r" + " " * 50, end="")  # Clear line
                            
                            progress_pct = progress.get("progress_percentage", 0)
                            current_step = progress.get("current_step", "Unknown")
                            subtasks_done = progress.get("subtasks_completed", 0)
                            subtasks_total = progress.get("subtasks_total", 0)
                            
                            status_color = "green" if progress_pct == 100 else "yellow"
                            console.print(f"[{status_color}]Progress: {progress_pct}%[/] | Step: {current_step} | Subtasks: {subtasks_done}/{subtasks_total}", end="")
                        
                        time.sleep(2)  # Update every 2 seconds
                        
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]👋 Stopped watching[/]")
                    return
            else:
                # Single check
                with httpx.Client() as http_client:
                    response = http_client.get(f"{client.base_url}/v1/tasks/{task_id}/progress")
                    response.raise_for_status()
                    data = response.json()
                
                if data.get("success"):
                    progress = data.get("progress", {})
                    
                    console.print()
                    console.print(Panel(
                        Text(f"📊 Task Progress: {task_id}", style="bold cyan"),
                        subtitle="Progress Information",
                        border_style="cyan"
                    ))
                    
                    console.print(f"[bold]Status:[/] {progress.get('status', 'N/A')}")
                    console.print(f"[bold]Progress:[/] {progress.get('progress_percentage', 0)}%")
                    console.print(f"[bold]Current Step:[/] {progress.get('current_step', 'N/A')}")
                    console.print(f"[bold]Subtasks:[/] {progress.get('subtasks_completed', 0)}/{progress.get('subtasks_total', 0)}")
                    
                    if progress.get("estimated_completion"):
                        console.print(f"[bold]Est. Completion:[/] {progress.get('estimated_completion', 'N/A')}")
                    
                    errors = progress.get("errors", [])
                    if errors:
                        console.print("[bold red]Errors:[/]")
                        for error in errors:
                            console.print(f"  • {error}")
                    
                    warnings = progress.get("warnings", [])
                    if warnings:
                        console.print("[bold yellow]Warnings:[/]")
                        for warning in warnings:
                            console.print(f"  • {warning}")
                else:
                    console.print(f"[red]Error: {data.get('message', 'Progress not found')}[/]")
                    
        except Exception as e:
            console.print(f"[red]Failed to get task progress: {e}[/]")
    
    @tasks_app.command("subtasks")
    def get_task_subtasks(
        task_id: str = typer.Argument(..., help="Task identifier"),
        base_url: str = typer.Option(
            None,
            "--base-url",
            envvar="MINDFLOW_API_URL",
            help="MindFlow backend base URL",
        ),
    ) -> None:
        """Get subtasks for a decomposed task."""
        try:
            client = build_client(base_url)
            
            with httpx.Client() as http_client:
                response = http_client.get(f"{client.base_url}/v1/tasks/{task_id}/subtasks")
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                subtasks = data.get("subtasks", [])
                total = data.get("total", 0)
                
                console.print()
                console.print(Panel(
                    Text(f"📋 Subtasks for: {task_id}", style="bold cyan"),
                    subtitle=f"{total} subtasks found",
                    border_style="cyan"
                ))
                
                if subtasks:
                    table = Table(title="Subtasks")
                    table.add_column("Subtask ID", style="cyan", no_wrap=True)
                    table.add_column("Title", style="white")
                    table.add_column("Status", style="yellow")
                    table.add_column("Agent", style="green")
                    table.add_column("Created", style="dim")
                    
                    for subtask in subtasks:
                        status_style = {
                            "completed": "green",
                            "in_progress": "yellow",
                            "pending": "dim",
                            "failed": "red"
                        }.get(subtask.get("status", "pending"), "white")
                        
                        table.add_row(
                            subtask.get("subtask_id", "N/A"),
                            subtask.get("title", "N/A"),
                            f"[{status_style}]{subtask.get('status', 'N/A')}[/{status_style}]",
                            subtask.get("agent_type", "N/A"),
                            subtask.get("created_at", "N/A")[:10]
                        )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No subtasks found[/]")
                
            else:
                console.print(f"[red]Error: {data.get('message', 'Subtasks not found')}[/]")
                
        except Exception as e:
            console.print(f"[red]Failed to get subtasks: {e}[/]")
