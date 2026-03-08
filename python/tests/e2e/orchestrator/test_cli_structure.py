#!/usr/bin/env python3
"""Test CLI structure without heavy dependencies."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

def test_cli_imports():
    """Test that CLI modules can be imported."""
    print("=== Testing CLI Imports ===\n")
    
    try:
        # Test app import
        from mindflow_cli.app import app
        print("✅ Main app import successful")
        
        # Test command imports
        from mindflow_cli.commands.start import register_start_commands
        print("✅ Start commands import successful")
        
        from mindflow_cli.commands.test_orchestrator import register_test_orchestrator_commands
        print("✅ Test orchestrator commands import successful")
        
        from mindflow_cli.commands.chat import register_chat_commands
        print("✅ Chat commands import successful")
        
        # Test renderer imports
        from mindflow_cli.render.chat_stream import ChatStreamRenderer
        print("✅ Chat stream renderer import successful")
        
        from mindflow_cli.render.orchestrator_stream import OrchestratorStreamRenderer
        print("✅ Orchestrator stream renderer import successful")
        
        # Test client import
        from mindflow_cli.client import MindFlowCliClient
        print("✅ CLI client import successful")
        
        print("\n✅ All CLI imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_command_structure():
    """Test that CLI commands are properly structured."""
    print("\n=== Testing CLI Command Structure ===\n")
    
    try:
        import typer
        from rich.console import Console
        
        # Test creating app
        app = typer.Typer(help="Test MindFlow CLI")
        print("✅ Typer app creation successful")
        
        # Test registering commands
        from mindflow_cli.commands.start import register_start_commands
        from mindflow_cli.commands.test_orchestrator import register_test_orchestrator_commands
        
        register_start_commands(app)
        print("✅ Start commands registration successful")
        
        register_test_orchestrator_commands(app)
        print("✅ Test orchestrator commands registration successful")
        
        # Test console creation
        console = Console()
        print("✅ Rich console creation successful")
        
        # Test renderer creation
        from mindflow_cli.render.orchestrator_stream import OrchestratorStreamRenderer
        renderer = OrchestratorStreamRenderer(console)
        print("✅ Orchestrator renderer creation successful")
        
        # Test client creation
        from mindflow_cli.client import MindFlowCliClient
        client = MindFlowCliClient("http://localhost:8000")
        print("✅ CLI client creation successful")
        
        print("\n✅ All CLI structure tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_renderer_functionality():
    """Test renderer functionality without backend."""
    print("\n=== Testing Renderer Functionality ===\n")
    
    try:
        from rich.console import Console
        from mindflow_cli.render.orchestrator_stream import OrchestratorStreamRenderer
        from mindflow_backend.schemas.agent import StreamEvent
        
        # Create console and renderer
        console = Console()
        renderer = OrchestratorStreamRenderer(console)
        print("✅ Renderer creation successful")
        
        # Test mock events
        test_events = [
            StreamEvent(type="thought", data="Analyzing user request..."),
            StreamEvent(type="agent_step", data="Routing to appropriate agent..."),
            StreamEvent(type="response", data="Hello! I'm helping you with your request."),
            StreamEvent(type="done", data="Task completed successfully"),
        ]
        
        for event in test_events:
            renderer.render(event)
            print(f"✅ Rendered event: {event.type}")
        
        print("\n✅ All renderer functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Renderer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_client_functionality():
    """Test client functionality without backend."""
    print("\n=== Testing Client Functionality ===\n")
    
    try:
        from mindflow_cli.client import MindFlowCliClient
        
        # Test client creation
        client = MindFlowCliClient("http://localhost:8000")
        print("✅ Client creation successful")
        
        # Test URL generation
        url = client._url("/test")
        expected = "http://localhost:8000/test"
        assert url == expected, f"Expected {expected}, got {url}"
        print("✅ URL generation successful")
        
        # Test base URL handling
        client_with_trailing = MindFlowCliClient("http://localhost:8000/")
        url2 = client_with_trailing._url("/test")
        assert url2 == expected, f"Expected {expected}, got {url2}"
        print("✅ Base URL handling successful")
        
        print("\n✅ All client functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all CLI structure tests."""
    print("="*60)
    print("🧪 MindFlow CLI Structure Tests")
    print("="*60)
    
    # Run tests
    import_success = test_cli_imports()
    structure_success = test_cli_command_structure()
    renderer_success = test_renderer_functionality()
    client_success = test_client_functionality()
    
    # Summary
    print("\n" + "="*60)
    print("🏁 Test Results")
    print("="*60)
    print(f"CLI Imports: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"Command Structure: {'✅ PASS' if structure_success else '❌ FAIL'}")
    print(f"Renderer Functionality: {'✅ PASS' if renderer_success else '❌ FAIL'}")
    print(f"Client Functionality: {'✅ PASS' if client_success else '❌ FAIL'}")
    
    all_passed = import_success and structure_success and renderer_success and client_success
    
    if all_passed:
        print("\n🎉 All CLI structure tests passed!")
        print("\nThe CLI implementation is structurally sound.")
        print("\nNext steps:")
        print("1. Start the backend server")
        print("2. Run: mindflow start --mode interactive")
        print("3. Run: mindflow test orchestrator --message 'Create a Python function'")
    else:
        print("\n❌ Some CLI structure tests failed.")
        print("Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
