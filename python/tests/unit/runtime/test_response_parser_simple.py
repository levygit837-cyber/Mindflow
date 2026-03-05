#!/usr/bin/env python3
"""Simple test for response parser utilities."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/OmniMind/python')

# Import from proper module
from omnimind_backend.runtime.utils.response_parser import (
    extract_ai_message_content,
    extract_text_only,
    extract_thinking_only,
    has_thinking_content,
    normalize_response_for_json,
)


class MockAIMessage:
    """Mock AIMessage object for testing."""
    
    def __init__(self, content):
        self.content = content


def test_response_parser():
    """Test the response parser functions."""
    print("=== Testing Response Parser ===\n")
    
    # Test 1: Simple string
    print("Test 1: Simple string")
    result = extract_ai_message_content("Hello world")
    print(f"  Text: '{result['text']}'")
    print(f"  Thinking: '{result['thinking']}'")
    assert result["text"] == "Hello world"
    assert result["thinking"] == ""
    print("  ✓ PASSED\n")
    
    # Test 2: Structured Vertex AI content
    print("Test 2: Structured Vertex AI content")
    content = [
        {"type": "thinking", "thinking": "I need to analyze this request."},
        {"type": "text", "text": "Here is my response."}
    ]
    message = MockAIMessage(content)
    
    result = extract_ai_message_content(message, include_thinking=True)
    print(f"  Text: '{result['text']}'")
    print(f"  Thinking: '{result['thinking']}'")
    assert result["text"] == "Here is my response."
    assert result["thinking"] == "I need to analyze this request."
    print("  ✓ PASSED\n")
    
    # Test 3: Text only extraction
    print("Test 3: Text only extraction")
    result = extract_text_only(message)
    print(f"  Text: '{result}'")
    assert result == "Here is my response."
    print("  ✓ PASSED\n")
    
    # Test 4: Thinking only extraction
    print("Test 4: Thinking only extraction")
    result = extract_thinking_only(message)
    print(f"  Thinking: '{result}'")
    assert result == "I need to analyze this request."
    print("  ✓ PASSED\n")
    
    # Test 5: Has thinking detection
    print("Test 5: Has thinking detection")
    result = has_thinking_content(message)
    print(f"  Has thinking: {result}")
    assert result is True
    print("  ✓ PASSED\n")
    
    # Test 6: JSON normalization
    print("Test 6: JSON normalization")
    json_content = [
        {"type": "thinking", "thinking": "Hidden."},
        {"type": "text", "text": '{"key": "value"}'}
    ]
    json_message = MockAIMessage(json_content)
    
    result = normalize_response_for_json(json_message)
    print(f"  Normalized: '{result}'")
    assert result == '{"key": "value"}'
    print("  ✓ PASSED\n")
    
    # Test 7: Multiple parts
    print("Test 7: Multiple parts")
    multi_content = [
        {"type": "thinking", "thinking": "First thought."},
        {"type": "text", "text": "First response."},
        {"type": "thinking", "thinking": "Second thought."},
        {"type": "text", "text": "Second response."}
    ]
    multi_message = MockAIMessage(multi_content)
    
    result = extract_ai_message_content(multi_message, include_thinking=True)
    print(f"  Text: '{result['text']}'")
    print(f"  Thinking: '{result['thinking']}'")
    assert result["text"] == "First response. Second response."
    assert result["thinking"] == "First thought. Second thought."
    print("  ✓ PASSED\n")
    
    print("🎉 All tests PASSED! Response parser is working correctly.")
    return True


if __name__ == "__main__":
    try:
        success = test_response_parser()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
