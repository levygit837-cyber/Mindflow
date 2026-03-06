"""Integration tests for Vertex AI model.

Tests real communication with Vertex AI to validate that the model
is receiving messages and responding correctly.
"""

import time
import pytest
from mindflow_backend.runtime.providers.providers import get_model_for_provider


class TestVertexModelIntegration:
    """Test Vertex AI model integration."""

    @pytest.mark.asyncio
    @pytest.mark.live
    async def test_vertex_model_basic_response(self) -> None:
        """Test basic message sending and response."""
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        # Send a simple message
        message = [{"role": "user", "content": "Hello! Please respond with 'Vertex AI is working'"}]
        
        start_time = time.time()
        response = await model.ainvoke(message)
        response_time = time.time() - start_time
        
        # Validate response
        assert response is not None
        assert hasattr(response, 'content'), "Response should have content attribute"
        
        # Extract text from AIMessage content
        content = response.content
        assert isinstance(content, list), "Content should be a list"
        assert len(content) > 0, "Content should not be empty"
        
        # Extract text parts
        text_parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get('type') == 'text' and 'text' in part:
                    text_parts.append(part['text'])
                elif part.get('type') == 'thinking' and 'thinking' in part:
                    text_parts.append(part['thinking'])
        
        full_text = " ".join(text_parts)
        assert len(full_text.strip()) > 0, "Extracted text should not be empty"
        assert response_time < 30.0, f"Response took too long: {response_time}s"
        
        # Check if response contains expected content
        response_lower = full_text.lower()
        assert any(word in response_lower for word in ["vertex", "working", "hello"]), f"Unexpected response: {full_text}"

    @pytest.mark.asyncio
    @pytest.mark.live
    async def test_vertex_model_question_answering(self) -> None:
        """Test model's ability to answer questions."""
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        # Ask a factual question
        message = [{"role": "user", "content": "What is 2 + 2? Answer with just the number."}]
        
        response = await model.ainvoke(message)
        
        # Validate response
        assert response is not None
        assert hasattr(response, 'content')
        
        # Extract text
        content = response.content
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'text' and 'text' in part:
                text_parts.append(part['text'])
        
        full_text = " ".join(text_parts)
        assert "4" in full_text, f"Expected '4' in response, got: {full_text}"

    @pytest.mark.asyncio
    @pytest.mark.live
    async def test_vertex_model_streaming_response(self) -> None:
        """Test streaming response functionality."""
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        message = [{"role": "user", "content": "Count from 1 to 3, one number per line."}]
        
        # Collect streaming chunks
        chunks = []
        start_time = time.time()
        
        async for chunk in model.astream(message):
            chunks.append(chunk)
            if len(chunks) > 10:  # Prevent infinite loops
                break
                
        response_time = time.time() - start_time
        
        # Validate streaming
        assert len(chunks) > 0, "No chunks received from streaming"
        assert response_time < 30.0, f"Streaming took too long: {response_time}s"
        
        # Validate we got some content
        has_content = False
        for chunk in chunks:
            if hasattr(chunk, 'content') and chunk.content:
                has_content = True
                break
        
        assert has_content, "Streaming should produce content"

    @pytest.mark.asyncio
    @pytest.mark.live
    async def test_vertex_model_error_handling(self) -> None:
        """Test model behavior with invalid input."""
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        # Send empty message
        empty_message = [{"role": "user", "content": ""}]
        
        try:
            response = await model.ainvoke(empty_message)
            # Model might handle empty messages gracefully
            assert response is not None
        except Exception as e:
            # Or it might raise an error, which is also acceptable
            assert any(keyword in str(e).lower() for keyword in ["empty", "content", "message"]), f"Unexpected error: {e}"

    @pytest.mark.asyncio
    @pytest.mark.live
    async def test_vertex_model_json_response(self) -> None:
        """Test model's ability to respond with structured data."""
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        message = [{
            "role": "user", 
            "content": "Respond with a JSON object containing: {\"status\": \"ok\", \"model\": \"vertex\"}"
        }]
        
        response = await model.ainvoke(message)
        
        # Validate response contains JSON-like structure
        assert response is not None
        assert hasattr(response, 'content')
        
        # Extract text
        content = response.content
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'text' and 'text' in part:
                text_parts.append(part['text'])
        
        full_text = " ".join(text_parts)
        assert any(keyword in full_text.lower() for keyword in ["status", "ok", "vertex", "json"]), f"Expected JSON-like response: {full_text}"

    @pytest.mark.asyncio
    @pytest.mark.live
    async def test_vertex_model_conversation_context(self) -> None:
        """Test model's ability to maintain conversation context."""
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        # Start a conversation
        messages = [
            {"role": "user", "content": "My favorite color is blue. Remember this."},
            {"role": "assistant", "content": "I'll remember that your favorite color is blue."},
            {"role": "user", "content": "What is my favorite color?"}
        ]
        
        response = await model.ainvoke(messages)
        
        # Validate context retention
        assert response is not None
        assert hasattr(response, 'content')
        
        # Extract text
        content = response.content
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'text' and 'text' in part:
                text_parts.append(part['text'])
        
        full_text = " ".join(text_parts)
        assert "blue" in full_text.lower(), f"Model didn't remember context: {full_text}"

    @pytest.mark.asyncio
    @pytest.mark.live
    async def test_vertex_model_performance_metrics(self) -> None:
        """Test basic performance metrics."""
        model = get_model_for_provider("vertexai", "gemini-3-flash-preview")
        
        message = [{"role": "user", "content": "Say 'performance test'"}]
        
        # Measure multiple response times
        response_times = []
        for i in range(3):
            start_time = time.time()
            response = await model.ainvoke(message)
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            # Validate each response
            assert response is not None
            assert hasattr(response, 'content')
            
            # Extract text to ensure we got a response
            content = response.content
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text' and 'text' in part:
                    text_parts.append(part['text'])
            
            full_text = " ".join(text_parts)
            assert len(full_text.strip()) > 0, f"Response {i+1} was empty"
        
        # Calculate average
        avg_time = sum(response_times) / len(response_times)
        
        # Performance assertions
        assert avg_time < 15.0, f"Average response time too high: {avg_time}s"
        assert all(t < 30.0 for t in response_times), f"Response time exceeded limit: {max(response_times)}s"
