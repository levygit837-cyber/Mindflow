"""Tests for response parsing utilities."""

import pytest
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


class TestResponseParser:
    """Test response parsing functions."""

    def test_extract_ai_message_content_simple_string(self):
        """Test extraction from simple string."""
        result = extract_ai_message_content("Hello world")
        
        assert result["text"] == "Hello world"
        assert result["thinking"] == ""

    def test_extract_ai_message_content_structured(self):
        """Test extraction from structured Vertex AI content."""
        content = [
            {"type": "thinking", "thinking": "I need to analyze this request."},
            {"type": "text", "text": "Here is my response."}
        ]
        message = MockAIMessage(content)
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == "Here is my response."
        assert result["thinking"] == "I need to analyze this request."

    def test_extract_ai_message_content_text_only(self):
        """Test extraction when only text is present."""
        content = [
            {"type": "text", "text": "Simple response only."}
        ]
        message = MockAIMessage(content)
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == "Simple response only."
        assert result["thinking"] == ""

    def test_extract_ai_message_content_thinking_only(self):
        """Test extraction when only thinking is present."""
        content = [
            {"type": "thinking", "thinking": "Just thinking here."}
        ]
        message = MockAIMessage(content)
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == ""
        assert result["thinking"] == "Just thinking here."

    def test_extract_ai_message_content_multiple_parts(self):
        """Test extraction with multiple text and thinking parts."""
        content = [
            {"type": "thinking", "thinking": "First thought."},
            {"type": "text", "text": "First response."},
            {"type": "thinking", "thinking": "Second thought."},
            {"type": "text", "text": "Second response."}
        ]
        message = MockAIMessage(content)
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == "First response. Second response."
        assert result["thinking"] == "First thought. Second thought."

    def test_extract_ai_message_content_without_thinking_flag(self):
        """Test extraction without including thinking."""
        content = [
            {"type": "thinking", "thinking": "Hidden thinking."},
            {"type": "text", "text": "Visible text."}
        ]
        message = MockAIMessage(content)
        
        result = extract_ai_message_content(message, include_thinking=False)
        
        assert result["text"] == "Visible text."
        assert "thinking" not in result

    def test_extract_ai_message_content_string_content(self):
        """Test extraction when content is a string."""
        message = MockAIMessage("Direct string content")
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == "Direct string content"
        assert result["thinking"] == ""

    def test_extract_ai_message_content_no_content_attribute(self):
        """Test extraction from object without content attribute."""
        message = "Plain string without content"
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == "Plain string without content"
        assert result["thinking"] == ""

    def test_extract_text_only(self):
        """Test text-only extraction."""
        content = [
            {"type": "thinking", "thinking": "Hidden."},
            {"type": "text", "text": "Visible."}
        ]
        message = MockAIMessage(content)
        
        result = extract_text_only(message)
        
        assert result == "Visible."

    def test_extract_thinking_only(self):
        """Test thinking-only extraction."""
        content = [
            {"type": "thinking", "thinking": "Hidden thinking."},
            {"type": "text", "text": "Visible text."}
        ]
        message = MockAIMessage(content)
        
        result = extract_thinking_only(message)
        
        assert result == "Hidden thinking."

    def test_has_thinking_content_true(self):
        """Test thinking detection when present."""
        content = [
            {"type": "thinking", "thinking": "Some thinking."},
            {"type": "text", "text": "Some text."}
        ]
        message = MockAIMessage(content)
        
        result = has_thinking_content(message)
        
        assert result is True

    def test_has_thinking_content_false(self):
        """Test thinking detection when absent."""
        content = [
            {"type": "text", "text": "Just text."}
        ]
        message = MockAIMessage(content)
        
        result = has_thinking_content(message)
        
        assert result is False

    def test_has_thinking_content_no_content(self):
        """Test thinking detection without content attribute."""
        message = "Plain string"
        
        result = has_thinking_content(message)
        
        assert result is False

    def test_normalize_response_for_json(self):
        """Test JSON normalization."""
        content = [
            {"type": "thinking", "thinking": "Hidden."},
            {"type": "text", "text": '{"key": "value"}'}
        ]
        message = MockAIMessage(content)
        
        result = normalize_response_for_json(message)
        
        assert result == '{"key": "value"}'

    def test_extract_ai_message_content_empty_content(self):
        """Test extraction with empty content."""
        message = MockAIMessage([])
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == ""
        assert result["thinking"] == ""

    def test_extract_ai_message_content_mixed_types(self):
        """Test extraction with mixed content types."""
        content = [
            {"type": "text", "text": "Structured text"},
            "Direct string content",
            {"type": "thinking", "thinking": "Structured thinking"}
        ]
        message = MockAIMessage(content)
        
        result = extract_ai_message_content(message, include_thinking=True)
        
        assert result["text"] == "Structured text Direct string content"
        assert result["thinking"] == "Structured thinking"
