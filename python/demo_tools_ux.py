#!/usr/bin/env python3
"""Demo of dynamic tool visualization and agent delegation tracking."""

import sys
import time
import json
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

from rich.console import Console
from mindflow_cli.render.orchestrator_stream import OrchestratorStreamRenderer
from mindflow_backend.schemas.agent import StreamEvent


def create_mock_event(event_type: str, data: Any, meta: Dict[str, Any] = None) -> StreamEvent:
    """Create a mock stream event for testing."""
    return StreamEvent(type=event_type, data=data, meta=meta or {})


def demo_tools_and_delegation():
    """Demonstrate dynamic tool visualization and delegation tracking."""
    console = Console()
    renderer = OrchestratorStreamRenderer(console)
    
    console.print("\n" + "="*80)
    console.print("🔧 MindFlow Tools & Delegation Demo")
    console.print("="*80)
    console.print()
    
    # Simulate user request
    console.print("[bold blue]User:[/] Create a secure authentication system with file-based storage")
    console.print()
    
    # 1. Orchestrator analysis
    console.print("🧠 [bold gold3]ORCHESTRATOR STARTS ANALYSIS[/]")
    time.sleep(1)
    
    renderer.render(create_mock_event("orchestrator_thinking_start", ""))
    time.sleep(1.5)
    
    renderer.render(create_mock_event("orchestrator_thinking", "Analyzing authentication requirements..."))
    time.sleep(1)
    
    renderer.render(create_mock_event("orchestrator_thinking", "Determining file structure and security needs..."))
    time.sleep(1)
    
    renderer.render(create_mock_event("orchestrator_thinking_end", ""))
    
    # 2. Orchestrator delegates to CODER
    console.print()
    decision_data = {
        "agent": "CODER",
        "priority": "HIGH",
        "thinking_level": "IMPLEMENTATION",
        "tool_scope": "FULL_IMPLEMENTATION"
    }
    renderer.render(create_mock_event("orchestrator_decision", json.dumps(decision_data)))
    time.sleep(2)
    
    # 3. Agent delegation starts
    console.print()
    delegation_data = {
        "agent_type": "CODER",
        "delegated_by": "ORCHESTRATOR",
        "task": "Create secure authentication system with file-based storage"
    }
    renderer.render(create_mock_event("agent_delegation_start", json.dumps(delegation_data)))
    time.sleep(2)
    
    # 4. CODER starts working with tools
    console.print()
    renderer.render(create_mock_event("specialist_activation", json.dumps({
        "agent_type": "CODER",
        "is_core": False
    })))
    time.sleep(2)
    
    # 5. Tool operation - Read existing files
    console.print()
    tool_start_data = {
        "tool_name": "read_file",
        "operation_type": "read",
        "file_path": "/app/config/settings.py",
        "agent_type": "CODER"
    }
    renderer.render(create_mock_event("tool_operation_start", json.dumps(tool_start_data)))
    time.sleep(2)
    
    # Update tool operation
    renderer.render(create_mock_event("tool_operation_update", json.dumps({
        "update": "Reading configuration file..."
    })))
    time.sleep(1)
    
    # Complete tool operation with content
    file_content = """# Application Settings
SECRET_KEY = "your-secret-key-here"
DATABASE_URL = "sqlite:///auth.db"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security settings
BCRYPT_ROUNDS = 12
SESSION_TIMEOUT = 3600
"""
    
    tool_complete_data = {
        "success": True,
        "content": file_content
    }
    renderer.render(create_mock_event("tool_operation_complete", json.dumps(tool_complete_data)))
    time.sleep(3)
    
    # 6. Tool operation - Create new file
    console.print()
    tool_create_data = {
        "tool_name": "write_file",
        "operation_type": "create",
        "file_path": "/app/auth/models.py",
        "agent_type": "CODER"
    }
    renderer.render(create_mock_event("tool_operation_start", json.dumps(tool_create_data)))
    time.sleep(2)
    
    renderer.render(create_mock_event("tool_operation_update", json.dumps({
        "update": "Creating authentication models..."
    })))
    time.sleep(1)
    
    # Complete with new content
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
    
    tool_create_complete = {
        "success": True,
        "content": new_file_content
    }
    renderer.render(create_mock_event("tool_operation_complete", json.dumps(tool_create_complete)))
    time.sleep(3)
    
    # 7. Tool operation - Modify existing file
    console.print()
    tool_modify_data = {
        "tool_name": "write_file",
        "operation_type": "write",
        "file_path": "/app/config/settings.py",
        "agent_type": "CODER"
    }
    renderer.render(create_mock_event("tool_operation_start", json.dumps(tool_modify_data)))
    time.sleep(2)
    
    renderer.render(create_mock_event("tool_operation_update", json.dumps({
        "update": "Updating configuration with new auth settings..."
    })))
    time.sleep(1)
    
    # Complete with modified content (diff)
    modified_content = """# Application Settings
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
    
    tool_modify_complete = {
        "success": True,
        "content": modified_content
    }
    renderer.render(create_mock_event("tool_operation_complete", json.dumps(tool_modify_complete)))
    time.sleep(3)
    
    # 8. Tool operation - Execute command
    console.print()
    tool_exec_data = {
        "tool_name": "execute_command",
        "operation_type": "execute",
        "file_path": "python -m pytest tests/test_auth.py",
        "agent_type": "CODER"
    }
    renderer.render(create_mock_event("tool_operation_start", json.dumps(tool_exec_data)))
    time.sleep(2)
    
    renderer.render(create_mock_event("tool_operation_update", json.dumps({
        "update": "Running authentication tests..."
    })))
    time.sleep(2)
    
    tool_exec_complete = {
        "success": True,
        "content": "✅ All tests passed (5/5)\n   test_user_creation.py: PASS\n   test_password_verification.py: PASS\n   test_token_generation.py: PASS\n   test_authentication_flow.py: PASS\n   test_security_validations.py: PASS"
    }
    renderer.render(create_mock_event("tool_operation_complete", json.dumps(tool_exec_complete)))
    time.sleep(3)
    
    # 9. Agent delegation completes
    console.print()
    delegation_complete_data = {
        "agent_type": "CODER",
        "success": True
    }
    renderer.render(create_mock_event("agent_delegation_complete", json.dumps(delegation_complete_data)))
    time.sleep(2)
    
    # 10. Final summary
    console.print()
    summary_data = {
        "agents_used": ["ORCHESTRATOR", "CODER"],
        "message_count": 12,
        "decision_count": 1,
        "total_time": 25.8,
        "events": [
            {"timestamp": "14:32:01", "action": "Orchestrator analysis started"},
            {"timestamp": "14:32:05", "action": "CODER delegated task"},
            {"timestamp": "14:32:07", "action": "Read settings.py (423 bytes)"},
            {"timestamp": "14:32:12", "action": "Created models.py (1,247 bytes)"},
            {"timestamp": "14:32:18", "action": "Modified settings.py (+156 bytes)"},
            {"timestamp": "14:32:23", "action": "Executed tests - All passed"},
            {"timestamp": "14:32:26", "action": "Task completed successfully"}
        ]
    }
    renderer.render(create_mock_event("session_summary", json.dumps(summary_data)))
    
    console.print("\n" + "="*80)
    console.print("✅ [bold green]Tools & Delegation Demo Complete[/]")
    console.print("="*80)
    console.print()
    
    console.print("[bold]Key Features Demonstrated:[/]")
    console.print("• 🎯 [gold3]Agent delegation tracking[/] with start/end times")
    console.print("• 🔧 [blue]Dynamic tool operations[/] with live spinners")
    console.print("• 📖 [blue]File content preview[/] with syntax highlighting")
    console.print("• ✏️ [green]File diff visualization[/] for write operations")
    console.print("• ⚡ [magenta]Command execution[/] with output display")
    console.print("• 📊 [cyan]Tool operations summary[/] with statistics")
    console.print("• ⏱️ [white]Execution time tracking[/] for each delegation")
    console.print()
    
    console.print("[bold]Tool Operation Types:[/]")
    console.print("• 📖 READ - File content preview with syntax highlighting")
    console.print("• ✏️ WRITE - File diff showing old vs new content")
    console.print("• 📝 CREATE - New file creation with content preview")
    console.print("• ⚡ EXECUTE - Command execution with output")
    console.print("• 🔍 SEARCH - Search operations with results")
    console.print("• 🗑️ DELETE - File deletion with confirmation")
    console.print()
    
    console.print("[bold]Delegation States:[/]")
    console.print("• 🔄 DELEGATED - Agent receives task from orchestrator")
    console.print("• ⚡ EXECUTING - Agent actively working with tools")
    console.print("• ✅ COMPLETED - Task finished successfully")
    console.print("• ❌ FAILED - Task failed with error details")
    console.print()
    
    console.print("[bold]Dynamic Visualization:[/]")
    console.print("• Live spinners during tool operations")
    console.print("• Real-time progress updates")
    console.print("• Automatic file content preview")
    console.print("• Color-coded operation types")
    console.print("• Comprehensive operation summaries")


def main():
    """Run the demo."""
    demo_tools_and_delegation()


if __name__ == "__main__":
    main()
