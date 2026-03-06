#!/usr/bin/env python3
"""Integration test for backend corrections with Vertex AI thinking/text support."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

# Import response parser from proper module
from mindflow_backend.runtime.utils.response_parser import extract_ai_message_content, normalize_response_for_json

# Import providers from proper module
from mindflow_backend.runtime.providers import providers


class MockAIMessage:
    """Mock AIMessage object for testing."""
    
    def __init__(self, content):
        self.content = content


async def test_intelligent_router_simulation():
    """Test IntelligentRouter-like JSON parsing with Vertex AI response."""
    print("=== Testing IntelligentRouter Integration ===\n")
    
    try:
        # Create a Vertex AI model
        model = providers.get_model_for_provider("vertexai", "gemini-3-flash-preview")
        print("✓ Created Vertex AI model")
        
        # Send a message that should return JSON
        json_message = [{
            "role": "user", 
            "content": 'Respond with JSON: {"status": "ok", "message": "test successful"}'
        }]
        
        response = await model.ainvoke(json_message)
        print("✓ Received response from Vertex AI")
        
        # Test the new normalize_response_for_json function
        normalized_text = normalize_response_for_json(response)
        print(f"✓ Normalized text: {normalized_text}")
        
        # Try to parse as JSON
        import json
        try:
            parsed = json.loads(normalized_text)
            print(f"✓ Successfully parsed JSON: {parsed}")
            return True
        except json.JSONDecodeError as e:
            print(f"⚠ JSON parsing failed: {e}")
            print(f"   This might be expected if the model didn't return pure JSON")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_orchestrator_simulation():
    """Test Orchestrator-like thinking/text separation."""
    print("\n=== Testing Orchestrator Integration ===\n")
    
    try:
        # Create a Vertex AI model
        model = providers.get_model_for_provider("vertexai", "gemini-3-flash-preview")
        print("✓ Created Vertex AI model")
        
        # Send a message that should trigger thinking
        thinking_message = [{
            "role": "user", 
            "content": "Think step by step: What is 2+2? Show your reasoning then give the answer."
        }]
        
        response = await model.ainvoke(thinking_message)
        print("✓ Received response from Vertex AI")
        
        # Test the new extract_ai_message_content function
        content = extract_ai_message_content(response, include_thinking=True)
        print(f"✓ Extracted text: '{content['text']}'")
        print(f"✓ Extracted thinking: '{content['thinking'][:100]}...'")  # First 100 chars
        
        # Validate separation
        if content['text'] and content['thinking']:
            print("✓ Successfully separated thinking and text")
            return True
        elif content['text']:
            print("✓ Got text (thinking might be empty)")
            return True
        else:
            print("✗ No content extracted")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_backward_compatibility():
    """Test that the new functions work with simple strings."""
    print("\n=== Testing Backward Compatibility ===\n")
    
    # Test with simple string (like from other providers)
    simple_response = "Simple text response"
    
    # Test all functions
    text_only = normalize_response_for_json(simple_response)
    content = extract_ai_message_content(simple_response, include_thinking=True)
    
    print(f"✓ Simple string normalized: '{text_only}'")
    print(f"✓ Simple string extracted: '{content['text']}'")
    print(f"✓ Simple string thinking: '{content['thinking']}'")
    
    # Validate
    if text_only == simple_response and content['text'] == simple_response:
        print("✓ Backward compatibility maintained")
        return True
    else:
        print("✗ Backward compatibility broken")
        return False


async def main():
    """Run all integration tests."""
    print("=== Backend Integration Tests ===")
    print("Testing Vertex AI thinking/text support in MindFlow backend\n")
    
    # Check environment
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("⚠ WARNING: No authentication found")
        print("  Some tests may fail\n")
    
    # Run tests
    test1_result = await test_intelligent_router_simulation()
    test2_result = await test_orchestrator_simulation()
    test3_result = await test_backward_compatibility()
    
    print(f"\n=== Test Results ===")
    print(f"IntelligentRouter Integration: {'PASSED' if test1_result else 'FAILED'}")
    print(f"Orchestrator Integration: {'PASSED' if test2_result else 'FAILED'}")
    print(f"Backward Compatibility: {'PASSED' if test3_result else 'FAILED'}")
    
    if test1_result and test2_result and test3_result:
        print("\n🎉 All backend integration tests PASSED!")
        print("✅ Vertex AI thinking/text support is working correctly")
        return 0
    else:
        print("\n❌ Some backend integration tests FAILED.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
