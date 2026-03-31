#!/usr/bin/env python3
"""Simple test script for Vertex AI model integration."""

import asyncio
import os
import sys
import time

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

async def test_vertex_model():
    """Test basic Vertex AI model functionality."""
    try:
        # Import the function directly
        from mindflow_backend.runtime.providers.providers import get_model_for_provider
        
        print("✓ Successfully imported get_model_for_provider")
        
        # Create model instance
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        print("✓ Successfully created Vertex AI model instance")
        
        # Test basic message
        message = [{"role": "user", "content": "Hello! Please respond with 'Vertex AI is working'"}]
        
        print("Sending test message...")
        start_time = time.time()
        response = await model.ainvoke(message)
        response_time = time.time() - start_time
        
        print(f"✓ Response received in {response_time:.2f}s")
        print(f"Response: {response}")
        
        # Validate response
        if response is None:
            print("✗ ERROR: Response is None")
            return False
            
        if not isinstance(response, str):
            print(f"✗ ERROR: Response is not a string, got {type(response)}")
            return False
            
        if len(response.strip()) == 0:
            print("✗ ERROR: Response is empty")
            return False
            
        if response_time > 30.0:
            print(f"✗ ERROR: Response took too long: {response_time}s")
            return False
        
        # Check if response contains expected content
        response_lower = response.lower()
        if any(word in response_lower for word in ["vertex", "working", "hello"]):
            print("✓ Response contains expected content")
        else:
            print(f"⚠ WARNING: Unexpected response content: {response}")
        
        print("✓ Vertex AI model test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        return False

async def test_vertex_question():
    """Test Vertex AI question answering."""
    try:
        from mindflow_backend.runtime.providers.providers import get_model_for_provider
        
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        # Ask a factual question
        message = [{"role": "user", "content": "What is 2 + 2? Answer with just the number."}]
        
        print("Testing question answering...")
        response = await model.ainvoke(message)
        print(f"Question response: {response}")
        
        # Validate response
        if "4" in response:
            print("✓ Question answering test PASSED")
            return True
        else:
            print(f"✗ Expected '4' in response, got: {response}")
            return False
            
    except Exception as e:
        print(f"✗ ERROR in question test: {type(e).__name__}: {e}")
        return False

async def main():
    """Run all tests."""
    print("=== Vertex AI Model Integration Test ===\n")
    
    # Check environment
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("⚠ WARNING: No GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS found")
        print("  Tests may fail due to missing authentication\n")
    
    # Run tests
    test1_result = await test_vertex_model()
    print()
    test2_result = await test_vertex_question()
    
    print("\n=== Test Results ===")
    print(f"Basic Response Test: {'PASSED' if test1_result else 'FAILED'}")
    print(f"Question Test: {'PASSED' if test2_result else 'FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests PASSED! Vertex AI model is working correctly.")
        return 0
    else:
        print("\n❌ Some tests FAILED. Check configuration and try again.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
