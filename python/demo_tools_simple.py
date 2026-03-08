#!/usr/bin/env python3
"""Simple demo of dynamic tool visualization without backend dependencies."""

import sys
import time
from typing import Dict, Any
from datetime import datetime
from enum import Enum

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.syntax import Syntax


class ToolOperationType(Enum):
    """Types of tool operations."""
    READ = "read"
    WRITE = "write"
    CREATE = "create"
    DELETE = "delete"
    EXECUTE = "execute"
    SEARCH = "search"


class AgentDelegationState(Enum):
    """Agent delegation states."""
    NOT_DELEGATED = "not_delegated"
    DELEGATED = "delegated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class SimpleToolsDemo:
    """Simple demo of tools visualization without backend dependencies."""
    
    def __init__(self):
        self.console = Console()
        self.agent_delegations = {}
        self.tool_operations = []
        self.active_operation = None
        self.file_changes_live = None
    
    def demo_tools_and_delegation(self):
        """Demonstrate dynamic tool visualization and delegation tracking."""
        self.console.print("\n" + "="*80)
        self.console.print("🔧 MindFlow Tools & Delegation Demo")
        self.console.print("="*80)
        self.console.print()
        
        # Simulate user request
        self.console.print("[bold blue]User:[/] Create a secure authentication system with file-based storage")
        self.console.print()
        
        # 1. Orchestrator analysis
        self.console.print("🧠 [bold gold3]ORCHESTRATOR STARTS ANALYSIS[/]")
        time.sleep(1)
        
        self._demo_orchestrator_thinking()
        
        # 2. Orchestrator delegates to CODER
        self._demo_orchestrator_decision()
        
        # 3. Agent delegation starts
        self._demo_agent_delegation_start("CODER", "ORCHESTRATOR", "Create secure authentication system")
        
        # 4. Tool operations
        self._demo_tool_read_file("/app/config/settings.py")
        self._demo_tool_create_file("/app/auth/models.py")
        self._demo_tool_write_file("/app/config/settings.py")
        self._demo_tool_execute_command("python -m pytest tests/test_auth.py")
        
        # 5. Agent delegation completes
        self._demo_agent_delegation_complete("CODER")
        
        # 6. Final summary
        self._demo_session_summary()
        
        self._demo_key_features()
    
    def _demo_orchestrator_thinking(self):
        """Demo orchestrator thinking with streaming."""
        with Live(
            Spinner("dots", text=Text("🧠 Analyzing request and planning strategy...", style="bold gold3")),
            console=self.console,
            transient=True,
            refresh_per_second=4
        ) as live:
            time.sleep(1.5)
            live.update(Spinner("dots", text=Text("🧠 Determining optimal tool requirements...", style="gold3")))
            time.sleep(1)
            live.update(Spinner("dots", text=Text("🧠 Planning file structure and security measures...", style="gold3")))
            time.sleep(1)
        
        self.console.print("✅ Analysis complete", style="bold green")
        self.console.print()
    
    def _demo_orchestrator_decision(self):
        """Demo orchestrator decision."""
        self.console.print(Rule(style="gold3"))
        
        decision_content = Text()
        decision_content.append("🎯 ORCHESTRATOR DECISION\n\n", style="bold gold3 underline")
        decision_content.append("🎯 Selected Agent: CODER\n", style="bold green")
        decision_content.append("⚡ Priority: HIGH\n", style="cyan")
        decision_content.append("🧠 Thinking Level: IMPLEMENTATION\n", style="blue")
        decision_content.append("🔧 Tool Scope: FULL_IMPLEMENTATION\n", style="magenta")
        
        self.console.print(Panel(
            decision_content,
            title="🧠 CENTRAL ORCHESTRATOR",
            border_style="gold3",
            padding=(1, 2)
        ))
        self.console.print(Rule(style="gold3"))
        time.sleep(2)
        self.console.print()
    
    def _demo_agent_delegation_start(self, agent_type: str, delegated_by: str, task: str):
        """Demo agent delegation start."""
        delegation_info = {
            "agent_type": agent_type,
            "delegated_by": delegated_by,
            "task": task,
            "state": AgentDelegationState.DELEGATED,
            "start_time": datetime.now(),
            "tool_operations": []
        }
        self.agent_delegations[agent_type] = delegation_info
        
        # Create delegation panel
        delegation_text = Text()
        delegation_text.append(f"👤 {agent_type} DELEGATED\n\n", style="bold green italic")
        delegation_text.append(f"Delegated by: {delegated_by}\n", style="white")
        delegation_text.append(f"Task: {task}\n", style="cyan")
        delegation_text.append(f"Status: 🔄 Executing\n", style="yellow")
        delegation_text.append(f"Started: {delegation_info['start_time'].strftime('%H:%M:%S')}\n", style="dim")
        
        self.console.print(Panel(
            delegation_text,
            title=f"👤 {agent_type.upper()} DELEGATION",
            border_style="green",
            padding=(1, 2)
        ))
        time.sleep(2)
        self.console.print()
    
    def _demo_tool_read_file(self, file_path: str):
        """Demo file read operation."""
        self._start_tool_operation("read_file", "read", file_path, "CODER")
        
        time.sleep(2)
        self._update_tool_operation("Reading configuration file...")
        time.sleep(1)
        
        # Mock file content
        file_content = """# Application Settings
SECRET_KEY = "your-secret-key-here"
DATABASE_URL = "sqlite:///auth.db"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security settings
BCRYPT_ROUNDS = 12
SESSION_TIMEOUT = 3600
"""
        
        self._complete_tool_operation(True, file_content)
        self._show_file_preview(file_path, file_content)
        time.sleep(3)
        self.console.print()
    
    def _demo_tool_create_file(self, file_path: str):
        """Demo file create operation."""
        self._start_tool_operation("write_file", "create", file_path, "CODER")
        
        time.sleep(2)
        self._update_tool_operation("Creating authentication models...")
        time.sleep(1)
        
        # Mock new file content
        new_file_content = """from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import jwt

class User:
    def __init__(self, username: str, email: str, password_hash: str):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = datetime.utcnow()
        self.is_active = True
    
    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def generate_token(self, secret_key: str) -> str:
        payload = {
            'username': self.username,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, secret_key, algorithm='HS256')

class AuthManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.users = {}  # In-memory storage for demo
    
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def create_user(self, username: str, email: str, password: str) -> User:
        password_hash = self.hash_password(password)
        user = User(username, email, password_hash)
        self.users[username] = user
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username)
        if user and user.verify_password(password):
            return user
        return None
"""
        
        self._complete_tool_operation(True, new_file_content)
        self._show_file_preview(file_path, new_file_content)
        time.sleep(3)
        self.console.print()
    
    def _demo_tool_write_file(self, file_path: str):
        """Demo file write operation with diff."""
        self._start_tool_operation("write_file", "write", file_path, "CODER")
        
        time.sleep(2)
        self._update_tool_operation("Updating configuration with new auth settings...")
        time.sleep(1)
        
        # Mock modified content
        old_content = """# Application Settings
SECRET_KEY = "your-secret-key-here"
DATABASE_URL = "sqlite:///auth.db"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security settings
BCRYPT_ROUNDS = 12
SESSION_TIMEOUT = 3600
"""
        
        new_content = """# Application Settings
SECRET_KEY = "your-secret-key-here"
DATABASE_URL = "sqlite:///auth.db"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security settings
BCRYPT_ROUNDS = 12
SESSION_TIMEOUT = 3600

# Authentication settings
AUTH_ENABLED = True
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes
PASSWORD_MIN_LENGTH = 8
REQUIRE_SPECIAL_CHARS = True
"""
        
        self._complete_tool_operation(True, new_content)
        self._show_file_diff(file_path, old_content, new_content)
        time.sleep(3)
        self.console.print()
    
    def _demo_tool_execute_command(self, command: str):
        """Demo command execution."""
        self._start_tool_operation("execute_command", "execute", command, "CODER")
        
        time.sleep(2)
        self._update_tool_operation("Running authentication tests...")
        time.sleep(2)
        
        # Mock execution output
        execution_output = """✅ All tests passed (5/5)
   test_user_creation.py: PASS
   test_password_verification.py: PASS
   test_token_generation.py: PASS
   test_authentication_flow.py: PASS
   test_security_validations.py: PASS"""
        
        self._complete_tool_operation(True, execution_output)
        
        # Show execution results
        self.console.print(Panel(
            Text(execution_output, style="green"),
            title=f"⚡ Command Results: {command}",
            border_style="magenta",
            padding=(1, 1)
        ))
        time.sleep(3)
        self.console.print()
    
    def _demo_agent_delegation_complete(self, agent_type: str):
        """Demo agent delegation completion."""
        if agent_type not in self.agent_delegations:
            return
        
        delegation_info = self.agent_delegations[agent_type]
        delegation_info["end_time"] = datetime.now()
        delegation_info["state"] = AgentDelegationState.COMPLETED
        
        execution_time = delegation_info["end_time"] - delegation_info["start_time"]
        
        completion_text = Text()
        completion_text.append(f"👤 {agent_type} TASK COMPLETE\n\n", style="bold green italic")
        completion_text.append(f"Status: ✅ Success\n", style="bold green")
        completion_text.append(f"Execution Time: {execution_time.total_seconds():.2f}s\n", style="white")
        completion_text.append(f"Tool Operations: {len(delegation_info['tool_operations'])}\n", style="cyan")
        completion_text.append(f"Completed: {delegation_info['end_time'].strftime('%H:%M:%S')}\n", style="dim")
        
        self.console.print(Panel(
            completion_text,
            title=f"👤 {agent_type.upper()} COMPLETION",
            border_style="green",
            padding=(1, 2)
        ))
        
        # Show tool operations summary
        if delegation_info["tool_operations"]:
            self._show_tool_operations_summary(agent_type, delegation_info["tool_operations"])
        
        time.sleep(2)
        self.console.print()
    
    def _start_tool_operation(self, tool_name: str, operation_type: str, file_path: str, agent_type: str):
        """Start a tool operation with live tracking."""
        operation = {
            "tool_name": tool_name,
            "operation_type": operation_type,
            "file_path": file_path,
            "agent_type": agent_type,
            "start_time": datetime.now()
        }
        self.active_operation = operation
        
        # Add to delegation tracking
        if agent_type in self.agent_delegations:
            self.agent_delegations[agent_type]["current_operation"] = operation
            self.agent_delegations[agent_type]["tool_operations"].append(operation)
        
        # Get operation icon and color
        operation_icons = {
            ToolOperationType.READ: ("📖", "blue"),
            ToolOperationType.WRITE: ("✏️", "green"),
            ToolOperationType.CREATE: ("📝", "yellow"),
            ToolOperationType.DELETE: ("🗑️", "red"),
            ToolOperationType.EXECUTE: ("⚡", "magenta"),
            ToolOperationType.SEARCH: ("🔍", "cyan")
        }
        
        op_type = ToolOperationType(operation_type.lower())
        icon, color = operation_icons.get(op_type, ("🔧", "white"))
        
        # Create live operation display
        operation_text = Text(f"{icon} {agent_type} {operation_type.upper()}: {file_path}", style=color)
        spinner = Spinner("dots", text=operation_text, style=color)
        
        self.file_changes_live = Live(
            spinner,
            console=self.console,
            transient=True,
            refresh_per_second=4
        )
        self.file_changes_live.start()
    
    def _update_tool_operation(self, update_message: str):
        """Update the current tool operation."""
        if self.file_changes_live and self.active_operation:
            operation = self.active_operation
            op_type = ToolOperationType(operation["operation_type"].lower())
            
            operation_icons = {
                ToolOperationType.READ: ("📖", "blue"),
                ToolOperationType.WRITE: ("✏️", "green"),
                ToolOperationType.CREATE: ("📝", "yellow"),
                ToolOperationType.DELETE: ("🗑️", "red"),
                ToolOperationType.EXECUTE: ("⚡", "magenta"),
                ToolOperationType.SEARCH: ("🔍", "cyan")
            }
            
            icon, color = operation_icons.get(op_type, ("🔧", "white"))
            operation_text = Text(f"{icon} {operation['agent_type']} {op_type.value.upper()}: {operation['file_path']} - {update_message}", style=color)
            spinner = Spinner("dots", text=operation_text, style=color)
            
            self.file_changes_live.update(spinner)
    
    def _complete_tool_operation(self, success: bool, content: str = ""):
        """Complete the current tool operation."""
        if not self.active_operation:
            return
        
        operation = self.active_operation
        operation["success"] = success
        operation["content"] = content
        operation["end_time"] = datetime.now()
        
        # Stop live display
        if self.file_changes_live:
            self.file_changes_live.stop()
            self.file_changes_live = None
        
        # Show operation result
        op_type = ToolOperationType(operation["operation_type"].lower())
        operation_icons = {
            ToolOperationType.READ: ("📖", "blue"),
            ToolOperationType.WRITE: ("✏️", "green"),
            ToolOperationType.CREATE: ("📝", "yellow"),
            ToolOperationType.DELETE: ("🗑️", "red"),
            ToolOperationType.EXECUTE: ("⚡", "magenta"),
            ToolOperationType.SEARCH: ("🔍", "cyan")
        }
        
        icon, color = operation_icons.get(op_type, ("🔧", "white"))
        
        if success:
            status_icon = "✅"
            status_color = "green"
            self.console.print(Text(f"{status_icon} {icon} {operation['agent_type']} {op_type.value.upper()} COMPLETE: {operation['file_path']}", style=status_color))
        else:
            status_icon = "❌"
            status_color = "red"
            self.console.print(Text(f"{status_icon} {icon} {operation['agent_type']} {op_type.value.upper()} FAILED: {operation['file_path']}", style=status_color))
        
        # Clear active operation
        self.active_operation = None
    
    def _show_file_preview(self, file_path: str, content: str):
        """Show file content preview."""
        max_lines = 20
        max_chars = 1000
        
        lines = content.split('\n')
        preview_lines = lines[:max_lines]
        preview_content = '\n'.join(preview_lines)
        
        if len(preview_content) > max_chars:
            preview_content = preview_content[:max_chars] + "..."
        
        if len(lines) > max_lines:
            preview_content += f"\n... ({len(lines) - max_lines} more lines)"
        
        # Determine file type for syntax highlighting
        file_extension = file_path.split('.')[-1].lower() if '.' in file_path else ''
        syntax_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown',
            'yaml': 'yaml',
            'yml': 'yaml',
            'sql': 'sql'
        }
        
        lexer = syntax_map.get(file_extension, 'text')
        
        try:
            syntax = Syntax(preview_content, lexer, theme="monokai", line_numbers=True)
        except:
            syntax = Text(preview_content, style="dim")
        
        self.console.print(Panel(
            syntax,
            title=f"📖 File Preview: {file_path}",
            border_style="blue",
            padding=(1, 1)
        ))
    
    def _show_file_diff(self, file_path: str, old_content: str, new_content: str):
        """Show file diff for write operations."""
        diff_text = Text()
        
        if old_content:
            diff_text.append("─" * 40 + " OLD CONTENT " + "─" * 40 + "\n", style="dim red")
            diff_text.append(Text(old_content[:500] + ("..." if len(old_content) > 500 else ""), style="red"))
            diff_text.append("\n")
        
        diff_text.append("─" * 40 + " NEW CONTENT " + "─" * 40 + "\n", style="dim green")
        diff_text.append(Text(new_content[:500] + ("..." if len(new_content) > 500 else ""), style="green"))
        
        self.console.print(Panel(
            diff_text,
            title=f"✏️ File Changes: {file_path}",
            border_style="green",
            padding=(1, 1)
        ))
    
    def _show_tool_operations_summary(self, agent_type: str, operations: list):
        """Show tool operations summary."""
        if not operations:
            return
        
        table = Table(title=f"🔧 {agent_type} Tool Operations Summary", show_header=True, header_style="bold cyan")
        table.add_column("Operation", style="bold", no_wrap=True)
        table.add_column("File", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Size", style="dim", no_wrap=True)
        
        for op in operations:
            operation_icons = {
                ToolOperationType.READ: "📖",
                ToolOperationType.WRITE: "✏️",
                ToolOperationType.CREATE: "📝",
                ToolOperationType.DELETE: "🗑️",
                ToolOperationType.EXECUTE: "⚡",
                ToolOperationType.SEARCH: "🔍"
            }
            
            op_type = ToolOperationType(op["operation_type"].lower())
            icon = operation_icons.get(op_type, "🔧")
            
            status = "✅ Success" if op["success"] else "❌ Failed"
            status_style = "green" if op["success"] else "red"
            
            size = f"{len(op['content'])} chars" if op.get("content") else "0 chars"
            
            table.add_row(
                f"{icon} {op_type.value.upper()}",
                op["file_path"],
                Text(status, style=status_style),
                size
            )
        
        self.console.print(table)
    
    def _demo_session_summary(self):
        """Demo session summary."""
        table = Table(title="📊 Session Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="bold", no_wrap=True)
        table.add_column("Value", style="white")
        
        table.add_row("Agents Used", "🎯 ORQ → 👤 CODER")
        table.add_row("Total Messages", "12")
        table.add_row("Orchestrator Decisions", "1")
        table.add_row("Tool Operations", "4")
        table.add_row("Execution Time", "25.8s")
        table.add_row("Task Complexity", "HIGH")
        
        self.console.print(table)
        time.sleep(2)
    
    def _demo_key_features(self):
        """Show key features demonstrated."""
        self.console.print("\n" + "="*80)
        self.console.print("✅ [bold green]Tools & Delegation Demo Complete[/]")
        self.console.print("="*80)
        self.console.print()
        
        self.console.print("[bold]Key Features Demonstrated:[/]")
        self.console.print("• 🎯 [gold3]Agent delegation tracking[/] with start/end times")
        self.console.print("• 🔧 [blue]Dynamic tool operations[/] with live spinners")
        self.console.print("• 📖 [blue]File content preview[/] with syntax highlighting")
        self.console.print("• ✏️ [green]File diff visualization[/] for write operations")
        self.console.print("• ⚡ [magenta]Command execution[/] with output display")
        self.console.print("• 📊 [cyan]Tool operations summary[/] with statistics")
        self.console.print("• ⏱️ [white]Execution time tracking[/] for each delegation")
        self.console.print()
        
        self.console.print("[bold]Tool Operation Types:[/]")
        self.console.print("• 📖 READ - File content preview with syntax highlighting")
        self.console.print("• ✏️ WRITE - File diff showing old vs new content")
        self.console.print("• 📝 CREATE - New file creation with content preview")
        self.console.print("• ⚡ EXECUTE - Command execution with output")
        self.console.print("• 🔍 SEARCH - Search operations with results")
        self.console.print("• 🗑️ DELETE - File deletion with confirmation")
        self.console.print()
        
        self.console.print("[bold]Delegation States:[/]")
        self.console.print("• 🔄 DELEGATED - Agent receives task from orchestrator")
        self.console.print("• ⚡ EXECUTING - Agent actively working with tools")
        self.console.print("• ✅ COMPLETED - Task finished successfully")
        self.console.print("• ❌ FAILED - Task failed with error details")
        self.console.print()
        
        self.console.print("[bold]Dynamic Visualization:[/]")
        self.console.print("• Live spinners during tool operations")
        self.console.print("• Real-time progress updates")
        self.console.print("• Automatic file content preview")
        self.console.print("• Color-coded operation types")
        self.console.print("• Comprehensive operation summaries")


def main():
    """Run the demo."""
    demo = SimpleToolsDemo()
    demo.demo_tools_and_delegation()


if __name__ == "__main__":
    main()
