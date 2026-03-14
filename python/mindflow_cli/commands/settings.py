"""Settings and configuration commands for MindFlow CLI."""

from __future__ import annotations

import typer
import json
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm

from mindflow_cli.render.theme import MINDFLOW_THEME

console = Console(theme=MINDFLOW_THEME)

# Settings file path
SETTINGS_FILE = Path.home() / ".mindflow" / "settings.json"


def load_settings() -> dict:
    """Load settings from file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(settings: dict) -> None:
    """Save settings to file."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        console.print(f"[red]Failed to save settings: {e}[/]")


def register_settings_commands(app: typer.Typer) -> None:
    """Register settings management commands."""
    
    settings_app = typer.Typer(help="Configuration and settings management")
    app.add_typer(settings_app, name="settings")
    
    @settings_app.command("show")
    def show_settings() -> None:
        """Show current configuration."""
        settings = load_settings()
        
        console.print()
        console.print(Panel(
            Text("⚙️ Current Settings", style="bold cyan"),
            subtitle="MindFlow CLI Configuration",
            border_style="cyan"
        ))
        
        if not settings:
            console.print("[yellow]No settings configured. Use 'mindflow settings set' to configure.[/]")
            return
        
        # Display settings in categories
        console.print(f"[bold]🔗 API Configuration:[/]")
        api_url = settings.get("api_url", os.getenv("MINDFLOW_API_URL", "http://127.0.0.1:8000"))
        console.print(f"  Base URL: {api_url}")
        
        default_provider = settings.get("default_provider", "vertexai")
        console.print(f"  Default Provider: {default_provider}")
        
        default_model = settings.get("default_model", "gemini-3-flash")
        console.print(f"  Default Model: {default_model}")
        
        console.print(f"[bold]🤖 Agent Configuration:[/]")
        default_agent = settings.get("default_agent", "auto")
        console.print(f"  Default Agent: {default_agent}")
        auto_orchestrate = settings.get("auto_orchestrate", True)
        console.print(f"  Auto Orchestrate: {auto_orchestrate}")
        
        console.print(f"[bold]🎨 Interface Configuration:[/]")
        debug_mode = settings.get("debug_mode", False)
        console.print(f"  Debug Mode: {debug_mode}")
        show_routing = settings.get("show_routing", False)
        console.print(f"  Show Routing: {show_routing}")
        show_agent_selection = settings.get("show_agent_selection", False)
        console.print(f"  Show Agent Selection: {show_agent_selection}")
        
        console.print(f"[bold]📊 Performance Configuration:[/]")
        timeout_seconds = settings.get("timeout_seconds", 300)
        console.print(f"  Request Timeout: {timeout_seconds}s")
        max_retries = settings.get("max_retries", 3)
        console.print(f"  Max Retries: {max_retries}")
        
        console.print(f"[bold]💾 Session Configuration:[/]")
        save_history = settings.get("save_history", True)
        console.print(f"  Save Chat History: {save_history}")
        max_history_items = settings.get("max_history_items", 100)
        console.print(f"  Max History Items: {max_history_items}")
    
    @settings_app.command("set")
    def set_setting(
        key: str = typer.Argument(..., help="Setting key to set"),
        value: str = typer.Argument(..., help="Setting value"),
    ) -> None:
        """Set a configuration value."""
        settings = load_settings()
        
        # Validate key
        valid_keys = {
            # API Configuration
            "api_url", "default_provider", "default_model",
            # Agent Configuration  
            "default_agent", "auto_orchestrate",
            # Interface Configuration
            "debug_mode", "show_routing", "show_agent_selection",
            # Performance Configuration
            "timeout_seconds", "max_retries",
            # Session Configuration
            "save_history", "max_history_items"
        }
        
        if key not in valid_keys:
            console.print(f"[red]Invalid setting key: {key}[/]")
            console.print(f"[yellow]Valid keys: {', '.join(sorted(valid_keys))}[/]")
            return
        
        # Convert value to appropriate type
        if key in ["auto_orchestrate", "save_history"]:
            value = value.lower() in ["true", "1", "yes", "on"]
        elif key in ["debug_mode", "show_routing", "show_agent_selection"]:
            value = value.lower() in ["true", "1", "yes", "on"]
        elif key in ["timeout_seconds", "max_retries", "max_history_items"]:
            try:
                value = int(value)
                if value < 0:
                    console.print(f"[red]Value must be positive for {key}[/]")
                    return
            except ValueError:
                console.print(f"[red]Value must be a number for {key}[/]")
                return
        # String values
        else:
            value = value
        
        settings[key] = value
        save_settings(settings)
        
        console.print(f"[green]✅ Set {key} = {value}[/]")
    
    @settings_app.command("reset")
    def reset_settings(
        confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt")
    ) -> None:
        """Reset all settings to defaults."""
        if not confirm:
            if not Confirm.ask("[yellow]Are you sure you want to reset all settings to defaults?[/]", default=False):
                console.print("Operation cancelled.")
                return
        
        # Default settings
        default_settings = {
            "api_url": os.getenv("MINDFLOW_API_URL", "http://127.0.0.1:8000"),
            "default_provider": "vertexai",
            "default_model": "gemini-3-flash",
            "default_agent": "auto",
            "auto_orchestrate": True,
            "debug_mode": False,
            "show_routing": False,
            "show_agent_selection": False,
            "timeout_seconds": 300,
            "max_retries": 3,
            "save_history": True,
            "max_history_items": 100,
        }
        
        save_settings(default_settings)
        console.print("[green]✅ Settings reset to defaults[/]")
    
    @settings_app.command("edit")
    def edit_settings() -> None:
        """Open settings file in default editor."""
        settings = load_settings()
        
        if not SETTINGS_FILE.exists():
            # Create default settings first
            save_settings({})
        
        try:
            import subprocess
            editor = os.getenv("EDITOR", "nano")
            subprocess.run([editor, str(SETTINGS_FILE)])
            console.print(f"[green]✅ Opened settings in {editor}[/]")
        except Exception as e:
            console.print(f"[red]Failed to open editor: {e}[/]")
    
    @settings_app.command("export")
    def export_settings(
        output_file: str = typer.Option("mindflow-settings.json", "--output", "-o", help="Output file path"),
    ) -> None:
        """Export settings to a file."""
        settings = load_settings()
        
        try:
            with open(output_file, 'w') as f:
                json.dump(settings, f, indent=2)
            console.print(f"[green]✅ Settings exported to {output_file}[/]")
        except Exception as e:
            console.print(f"[red]Failed to export settings: {e}[/]")
    
    @settings_app.command("import")
    def import_settings(
        input_file: str = typer.Argument(..., help="Settings file to import"),
    ) -> None:
        """Import settings from a file."""
        try:
            with open(input_file, 'r') as f:
                imported_settings = json.load(f)
            
            # Validate imported settings
            current_settings = load_settings()
            current_settings.update(imported_settings)
            save_settings(current_settings)
            
            console.print(f"[green]✅ Settings imported from {input_file}[/]")
        except Exception as e:
            console.print(f"[red]Failed to import settings: {e}[/]")


def get_settings() -> dict:
    """Get current settings (for use by other commands)."""
    return load_settings()
