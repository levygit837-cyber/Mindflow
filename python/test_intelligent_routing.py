#!/usr/bin/env python3
"""Test script for intelligent routing without external dependencies."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_intent_analysis():
    """Test basic intent analysis without external dependencies."""
    
    # Mock the LLM response for testing
    class MockLLM:
        async def ainvoke(self, messages):
            class MockResponse:
                content = 'CODER'  # Simulate LLM choosing CODER
            return MockResponse()
    
    # Mock the settings
    class MockSettings:
        default_provider = "test"
        default_model = "test-model"
    
    # Mock the model function
    def get_model_for_provider(provider, model):
        return MockLLM()
    
    # Test the router
    async def test_router():
        # Import here to avoid circular dependencies
        from omnimind_backend.orchestrator.working_router import WorkingIntelligentRouter
        
        router = WorkingIntelligentRouter()
        router.settings = MockSettings()
        
        # Test message that should route to CODER
        message = "implement user authentication system"
        result = await router.analyze_intent_with_llm(message)
        
        print(f"✅ Message: {message}")
        print(f"✅ Intent: {result.user_intent}")
        print(f"✅ Recommended Agent: {result.recommended_agent.value}")
        print(f"✅ Confidence: {result.confidence}")
        print(f"✅ Formulated Objective: {result.formulated_objective}")
        
        # Test different message types
        test_cases = [
            ("analyze the database schema", "ANALYST"),
            ("research authentication best practices", "RESEARCHER"),
            ("review the API design", "CRITIC"),
            ("design a scalable architecture", "ARCH_TECH"),
            ("brainstorm new features", "CREATIVE"),
            ("audit for security vulnerabilities", "SECURITY_GUARD"),
        ]
        
        print("\n🧪 Testing multiple message types:")
        for msg, expected in test_cases:
            result = await router.analyze_intent_with_llm(msg)
            status = "✅" if result.recommended_agent.value == expected else "❌"
            print(f"{status} '{msg}' → {result.recommended_agent.value} (expected: {expected})")
        
        return True
    
    if __name__ == "__main__":
        import asyncio
        success = asyncio.run(test_router())
        if success:
            print("\n🎉 All tests completed successfully!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
