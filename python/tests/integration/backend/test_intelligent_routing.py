#!/usr/bin/env python3
"""Test script for intelligent routing without external dependencies."""

import sys
import os

# Add project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

def test_intent_analysis():
    """Test basic intent analysis without external dependencies."""
    
    # Mock LLM response for testing
    class MockLLM:
        async def ainvoke(self, messages):
            class MockResponse:
                content = 'CODER'  # Simulate LLM choosing CODER
            return MockResponse()
    
    # Mock settings
    class MockSettings:
        default_provider = 'test'
        default_model = 'test-model'
    
    # Test intelligent router directly
    from mindflow_backend.orchestrator.intelligent_router import get_intelligent_router
    
    router = get_intelligent_router()
    router.settings = MockSettings()
    router.get_model_for_provider = lambda p, m: MockLLM()
    
    # Test the intent analysis
    import asyncio
    
    async def run_test():
        result = await router.analyze_intent_with_llm("Implement a new feature")
        print(f"Intent: {result.user_intent}")
        print(f"Agent: {result.recommended_agent}")
        print(f"Confidence: {result.confidence}")
        print("✅ Intelligent routing test passed")
    
    asyncio.run(run_test())

if __name__ == "__main__":
    test_intent_analysis()
