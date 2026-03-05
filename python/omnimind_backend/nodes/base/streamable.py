"""Streamable node mixin for nodes that support streaming output."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Optional

from omnimind_backend.nodes.base.node import BaseNode


class StreamableNode:
    """Mixin for nodes that support streaming output."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._streaming_enabled = True
        self._chunk_size = 1024
        self._stream_buffer: list[str] = []
    
    def enable_streaming(self, enabled: bool = True) -> None:
        """Enable or disable streaming."""
        self._streaming_enabled = enabled
        self.config.enable_streaming = enabled
    
    def is_streaming_enabled(self) -> bool:
        """Check if streaming is enabled."""
        return self._streaming_enabled and self.config.enable_streaming
    
    def set_chunk_size(self, size: int) -> None:
        """Set the chunk size for streaming."""
        self._chunk_size = max(1, size)
    
    async def stream_execute(
        self, 
        state: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the node and yield streaming results."""
        if not self.is_streaming_enabled():
            # Fall back to non-streaming execution
            result = await self.execute(state)
            yield result
            return
        
        # Default streaming implementation
        async for chunk in self._stream_execution(state):
            yield chunk
    
    async def _stream_execution(
        self, 
        state: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Override this method for custom streaming logic."""
        # Default: execute normally and yield result
        result = await self.execute(state)
        yield result
    
    async def _emit_chunk(
        self, 
        chunk: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Emit a streaming chunk."""
        chunk_data = {
            "node_id": self.node_id,
            "chunk": chunk,
            "is_final": False,
            "timestamp": self._get_timestamp(),
        }
        
        if metadata:
            chunk_data["metadata"] = metadata
        
        return chunk_data
    
    async def _emit_final_chunk(
        self, 
        final_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Emit the final streaming chunk."""
        return {
            "node_id": self.node_id,
            "chunk": "",
            "is_final": True,
            "result": final_result,
            "timestamp": self._get_timestamp(),
        }
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def add_to_buffer(self, chunk: str) -> None:
        """Add content to the streaming buffer."""
        self._stream_buffer.append(chunk)
    
    def get_buffer_content(self) -> str:
        """Get all content from the buffer."""
        return "".join(self._stream_buffer)
    
    def clear_buffer(self) -> None:
        """Clear the streaming buffer."""
        self._stream_buffer.clear()


class LLMStreamNode(StreamableNode, BaseNode):
    """Example streaming node for LLM interactions."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.category = self.category or "LLM_INVOKE"
    
    async def _stream_execution(
        self, 
        state: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream LLM response chunks."""
        # Get LLM response (this would be the actual LLM call)
        full_response = await self._get_llm_response(state)
        
        # Stream the response in chunks
        for i in range(0, len(full_response), self._chunk_size):
            chunk = full_response[i:i + self._chunk_size]
            
            chunk_data = await self._emit_chunk(chunk, {
                "chunk_index": i // self._chunk_size,
                "total_length": len(full_response),
            })
            
            yield chunk_data
        
        # Emit final result
        final_result = {
            "response": full_response,
            "node_id": self.node_id,
            "streaming_complete": True,
        }
        
        yield await self._emit_final_chunk(final_result)
    
    async def _get_llm_response(self, state: Dict[str, Any]) -> str:
        """Get the full LLM response (to be implemented by subclasses)."""
        # This is a placeholder - actual implementation would call the LLM
        message = state.get("message", "")
        return f"LLM response to: {message}"
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Non-streaming execution fallback."""
        full_response = await self._get_llm_response(state)
        
        return {
            "response": full_response,
            "node_id": self.node_id,
            "streaming_used": False,
        }
    
    def validate_inputs(self, state: Dict[str, Any]) -> list[str]:
        """Validate inputs for LLM node."""
        errors = []
        
        if "message" not in state:
            errors.append("Missing required input: message")
        
        return errors


class ToolStreamNode(StreamableNode, BaseNode):
    """Example streaming node for tool execution."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.category = self.category or "TOOL_EXECUTION"
    
    async def _stream_execution(
        self, 
        state: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream tool execution progress."""
        # Emit start chunk
        yield await self._emit_chunk("Starting tool execution...", {
            "status": "started",
        })
        
        # Execute the tool (placeholder implementation)
        result = await self._execute_tool(state)
        
        # Emit progress chunks
        yield await self._emit_chunk("Tool executing...", {
            "status": "executing",
        })
        
        # Emit completion
        yield await self._emit_chunk("Tool execution completed.", {
            "status": "completed",
        })
        
        # Emit final result
        final_result = {
            "tool_result": result,
            "node_id": self.node_id,
            "execution_complete": True,
        }
        
        yield await self._emit_final_chunk(final_result)
    
    async def _execute_tool(self, state: Dict[str, Any]) -> str:
        """Execute the tool (to be implemented by subclasses)."""
        # Placeholder implementation
        return "Tool execution result"
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Non-streaming execution fallback."""
        result = await self._execute_tool(state)
        
        return {
            "tool_result": result,
            "node_id": self.node_id,
            "streaming_used": False,
        }
    
    def validate_inputs(self, state: Dict[str, Any]) -> list[str]:
        """Validate inputs for tool node."""
        errors = []
        
        # Add tool-specific validation here
        if "tool_name" not in state and "tool" not in state:
            errors.append("Missing required input: tool_name or tool")
        
        return errors
