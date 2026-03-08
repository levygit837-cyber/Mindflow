#!/usr/bin/env python3
"""Demo of enhanced Orchestrator UI/UX with visual differentiation."""

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


def demo_orchestrator_flow():
    """Demonstrate the enhanced orchestrator UI/UX flow."""
    console = Console()
    renderer = OrchestratorStreamRenderer(console)
    
    console.print("\n" + "="*80)
    console.print("🎯 MindFlow Orchestrator - Enhanced UI/UX Demo")
    console.print("="*80)
    console.print()
    
    # Simulate user request
    console.print("[bold blue]User:[/] Create a secure REST API for user authentication")
    console.print()
    
    # 1. Orchestrator starts thinking
    console.print("🧠 [bold gold3]ORCHESTRATOR STARTS ANALYSIS[/]")
    time.sleep(1)
    
    renderer.render(create_mock_event("orchestrator_thinking_start", ""))
    time.sleep(1.5)
    
    renderer.render(create_mock_event("orchestrator_thinking", "Analyzing user request for authentication system..."))
    time.sleep(1)
    
    renderer.render(create_mock_event("orchestrator_thinking", "Evaluating complexity and required expertise..."))
    time.sleep(1)
    
    renderer.render(create_mock_event("orchestrator_thinking", "Determining optimal agent selection strategy..."))
    time.sleep(1)
    
    renderer.render(create_mock_event("orchestrator_thinking_end", ""))
    
    # 2. Orchestrator enters reflection mode for delegation
    console.print()
    renderer.render(create_mock_event("reflection_mode_start", ""))
    time.sleep(1)
    
    renderer.render(create_mock_event("thought", "This task requires security expertise. I should delegate to ANALYST first for security analysis, then CODER for implementation."))
    time.sleep(2)
    
    renderer.render(create_mock_event("reflection_mode_end", ""))
    
    # 3. Orchestrator makes decision with central figure emphasis
    console.print()
    decision_data = {
        "agent": "ANALYST",
        "priority": "HIGH",
        "thinking_level": "STRATEGIC",
        "tool_scope": "SECURITY_ANALYSIS",
        "thinking_mode": "DECOMPOSITION"
    }
    renderer.render(create_mock_event("orchestrator_decision", json.dumps(decision_data)))
    time.sleep(2)
    
    # 4. Orchestrator shows its step progression
    console.print()
    renderer.render(create_mock_event("orchestrator_step", json.dumps({
        "description": "Task decomposition completed",
        "step_number": 1,
        "total_steps": 3
    })))
    time.sleep(1)
    
    # 5. Specialist activation (Core Specialist)
    console.print()
    specialist_data = {
        "agent_type": "ANALYST",
        "is_core": True
    }
    renderer.render(create_mock_event("specialist_activation", json.dumps(specialist_data)))
    time.sleep(2)
    
    # 6. Specialist thinking
    console.print()
    renderer.render(create_mock_event("specialist_thinking", json.dumps({
        "agent_type": "ANALYST",
        "thought": "Analyzing security requirements for authentication system...",
        "is_core": True
    })))
    time.sleep(2)
    
    renderer.render(create_mock_event("specialist_thinking", json.dumps({
        "agent_type": "ANALYST", 
        "thought": "Evaluating OWASP best practices and security patterns...",
        "is_core": True
    })))
    time.sleep(2)
    
    # 7. Specialist step execution
    console.print()
    renderer.render(create_mock_event("agent_step", json.dumps({
        "agent_type": "ANALYST",
        "description": "Security vulnerability assessment",
        "step_number": 1,
        "is_core": True
    })))
    time.sleep(1.5)
    
    renderer.render(create_mock_event("agent_step", json.dumps({
        "agent_type": "ANALYST",
        "description": "Authentication pattern analysis", 
        "step_number": 2,
        "is_core": True
    })))
    time.sleep(1.5)
    
    # 8. Specialist response
    console.print()
    renderer.render(create_mock_event("response", 
        "Based on security analysis, I recommend implementing JWT-based authentication with the following security measures:\n\n1. Password hashing with bcrypt\n2. JWT token expiration and refresh\n3. Rate limiting on authentication endpoints\n4. Input validation and sanitization\n5. HTTPS enforcement\n\nThe system should follow OWASP authentication guidelines and include proper error handling to prevent information leakage.",
        {"agent": "ANALYST", "provider": "openai", "model": "gpt-4"}
    ))
    time.sleep(3)
    
    # 9. Orchestrator continues with next step
    console.print()
    renderer.render(create_mock_event("orchestrator_step", json.dumps({
        "description": "Security analysis complete, proceeding to implementation",
        "step_number": 2,
        "total_steps": 3
    })))
    time.sleep(1)
    
    # 10. Orchestrator delegates to CODER
    console.print()
    coder_decision = {
        "agent": "CODER",
        "priority": "HIGH", 
        "thinking_level": "IMPLEMENTATION",
        "tool_scope": "FULL_IMPLEMENTATION",
        "thinking_mode": "STANDARD"
    }
    renderer.render(create_mock_event("orchestrator_decision", json.dumps(coder_decision)))
    time.sleep(2)
    
    # 11. CODER activation (Specialist)
    console.print()
    coder_data = {
        "agent_type": "CODER",
        "is_core": False
    }
    renderer.render(create_mock_event("specialist_activation", json.dumps(coder_data)))
    time.sleep(2)
    
    # 12. CODER thinking and implementation
    console.print()
    renderer.render(create_mock_event("specialist_thinking", json.dumps({
        "agent_type": "CODER",
        "thought": "Implementing secure authentication API based on analyst recommendations...",
        "is_core": False
    })))
    time.sleep(2)
    
    renderer.render(create_mock_event("agent_step", json.dumps({
        "agent_type": "CODER",
        "description": "Setting up FastAPI application structure",
        "step_number": 1,
        "is_core": False
    })))
    time.sleep(1.5)
    
    # 13. CODER response
    console.print()
    renderer.render(create_mock_event("response",
        "I'll implement a secure authentication API with the following structure:\n\n```python\nfrom fastapi import FastAPI, HTTPException, Depends\nfrom fastapi.security import HTTPBearer\nfrom passlib.context import CryptContext\nimport jwt\nfrom datetime import datetime, timedelta\n\nclass AuthManager:\n    def __init__(self):\n        self.pwd_context = CryptContext(schemes=[\"bcrypt\"], deprecated=\"auto\")\n        self.secret_key = \"your-secret-key\"\n        self.algorithm = \"HS256\"\n\n    def hash_password(self, password: str) -> str:\n        return self.pwd_context.hash(password)\n\n    def verify_password(self, plain_password: str, hashed_password: str) -> bool:\n        return self.pwd_context.verify(plain_password, hashed_password)\n\n    def create_access_token(self, data: dict, expires_delta: timedelta = None):\n        to_encode = data.copy()\n        if expires_delta:\n            expire = datetime.utcnow() + expires_delta\n        else:\n            expire = datetime.utcnow() + timedelta(minutes=15)\n        to_encode.update({\"exp\": expire})\n        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)\n        return encoded_jwt\n```\n\nThis implementation includes secure password hashing, JWT token management, and follows the security recommendations provided by the ANALYST.",
        {"agent": "CODER", "provider": "openai", "model": "gpt-4"}
    ))
    time.sleep(3)
    
    # 14. Orchestrator final step
    console.print()
    renderer.render(create_mock_event("orchestrator_step", json.dumps({
        "description": "Implementation complete, final validation",
        "step_number": 3,
        "total_steps": 3
    })))
    time.sleep(1)
    
    # 15. Final summary
    console.print()
    summary_data = {
        "agents_used": ["ORCHESTRATOR", "ANALYST", "CODER"],
        "message_count": 15,
        "decision_count": 2,
        "total_time": 45.2,
        "events": [
            {"timestamp": "12:45:01", "action": "Orchestrator analysis started"},
            {"timestamp": "12:45:15", "action": "ANALYST core specialist activated"},
            {"timestamp": "12:45:32", "action": "CODER specialist activated"},
            {"timestamp": "12:45:45", "action": "Task completed successfully"}
        ]
    }
    renderer.render(create_mock_event("session_summary", json.dumps(summary_data)))
    
    console.print("\n" + "="*80)
    console.print("✅ [bold green]Demo Complete - Enhanced Orchestrator UI/UX[/]")
    console.print("="*80)
    console.print()
    
    console.print("[bold]Key Features Demonstrated:[/]")
    console.print("• 🎯 [gold3]Orchestrator[/] as central figure with gold styling")
    console.print("• ⭐ [green]Core Specialists[/] with enhanced visual emphasis") 
    console.print("• 👤 [green]Specialists[/] with distinct but less prominent styling")
    console.print("• 🧠 [gold3]Streaming thinking[/] process for orchestrator")
    console.print("• 🔄 [cyan]Reflection mode[/] for delegation decisions")
    console.print("• 📊 [gold3]Progress tracking[/] for orchestrator steps")
    console.print("• 🎨 [white]Visual hierarchy[/] showing agent relationships")


def main():
    """Run the demo."""
    demo_orchestrator_flow()


if __name__ == "__main__":
    main()
