"""Stream Node - Handles streaming data in I/O pipelines.

This node manages data streams including input streams, output streams,
and bidirectional streams with buffering and backpressure handling.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import AsyncIterator, Callable
from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.stateful import StatefulNode


class StreamNode(StatefulNode, BaseNode):
    """Node that handles streaming data operations.
    
    This node supports various stream operations:
    - Stream input: Read from input stream
    - Stream output: Write to output stream
    - Transform stream: Transform data while streaming
    - Filter stream: Filter data while streaming
    - Buffer stream: Buffer and batch stream data
    """
    
    def __init__(
        self,
        node_id: str = "stream",
        stream_type: str = "passthrough",  # passthrough, buffer, transform, filter, split, merge
        input_stream: AsyncIterator | None = None,
        output_stream: Callable[[Any], None] | None = None,
        transform_function: Callable[[Any], Any] | None = None,
        filter_condition: Callable[[Any], bool] | None = None,
        buffer_size: int = 1000,
        flush_interval: float = 1.0,
        batch_size: int | None = None,
        backpressure_limit: int | None = None,
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.IO,
            category=NodeCategory.IO_STREAM,
            description=description or f"{stream_type} stream"
        )
        
        self.stream_type = stream_type.lower()
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.transform_function = transform_function
        self.filter_condition = filter_condition
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.backpressure_limit = backpressure_limit
        
        # Required inputs
        self.config.required_inputs = {"input_stream"}
        self.config.outputs = {"result", "stream_data", "metadata"}
        
        # Internal state
        self._buffer = deque(maxlen=self.buffer_size)
        self._stream_stats = {
            "items_processed": 0,
            "items_filtered": 0,
            "items_output": 0,
            "bytes_processed": 0,
            "start_time": None,
            "last_flush": None
        }
        self._running = False
        self._paused = False
    
    async def initialize(self) -> None:
        """Initialize the stream node."""
        await super().initialize()
        self._stream_stats["start_time"] = time.time()
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the stream operation based on configured type."""
        input_stream = state.get("input_stream", self.input_stream)
        
        if not input_stream:
            raise ValueError("Input stream is required for stream operations")
        
        try:
            self._running = True
            self._paused = False
            
            if self.stream_type == "passthrough":
                result = await self._execute_passthrough_stream(input_stream)
            elif self.stream_type == "buffer":
                result = await self._execute_buffer_stream(input_stream)
            elif self.stream_type == "transform":
                result = await self._execute_transform_stream(input_stream)
            elif self.stream_type == "filter":
                result = await self._execute_filter_stream(input_stream)
            elif self.stream_type == "split":
                result = await self._execute_split_stream(input_stream)
            elif self.stream_type == "merge":
                result = await self._execute_merge_stream(input_stream)
            else:
                raise ValueError(f"Unsupported stream type: {self.stream_type}")
            
            return {
                "result": result,
                "stream_data": result,
                "metadata": {
                    "stream_type": self.stream_type,
                    "items_processed": self._stream_stats["items_processed"],
                    "items_filtered": self._stream_stats["items_filtered"],
                    "items_output": self._stream_stats["items_output"],
                    "bytes_processed": self._stream_stats["bytes_processed"],
                    "runtime": time.time() - self._stream_stats["start_time"]
                }
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("stream_node_execution_failed", 
                       stream_type=self.stream_type, 
                       error=str(e))
            
            return {
                "result": None,
                "stream_data": None,
                "error": str(e),
                "metadata": {"stream_type": self.stream_type, "status": "error"}
            }
    
    async def _execute_passthrough_stream(self, input_stream: AsyncIterator) -> AsyncIterator:
        """Execute passthrough stream (direct forwarding)."""
        async for item in input_stream:
            if not self._paused:
                self._stream_stats["items_processed"] += 1
                yield item
                await self._output_to_stream(item)
    
    async def _execute_buffer_stream(self, input_stream: AsyncIterator) -> AsyncIterator:
        """Execute buffered stream operations."""
        async for item in input_stream:
            if not self._paused:
                self._buffer.append(item)
                self._stream_stats["items_processed"] += 1
                
                # Flush buffer when full or interval reached
                if (len(self._buffer) >= self.buffer_size or 
                    time.time() - self._stream_stats.get("last_flush", 0) >= self.flush_interval):
                    
                    await self._flush_buffer()
                    self._stream_stats["last_flush"] = time.time()
    
    async def _execute_transform_stream(self, input_stream: AsyncIterator) -> AsyncIterator:
        """Execute transform stream operations."""
        if not self.transform_function:
            # Fallback to passthrough
            async for item in input_stream:
                if not self._paused:
                    self._stream_stats["items_processed"] += 1
                    yield item
                    await self._output_to_stream(item)
            return
        
        async for item in input_stream:
            if not self._paused:
                self._stream_stats["items_processed"] += 1
                
                try:
                    transformed_item = self.transform_function(item)
                    yield transformed_item
                    await self._output_to_stream(transformed_item)
                except Exception:
                    # Log transformation error but continue
                    self._stream_stats["items_filtered"] += 1
                    continue
    
    async def _execute_filter_stream(self, input_stream: AsyncIterator) -> AsyncIterator:
        """Execute filter stream operations."""
        if not self.filter_condition:
            # Fallback to passthrough
            async for item in input_stream:
                if not self._paused:
                    self._stream_stats["items_processed"] += 1
                    yield item
                    await self._output_to_stream(item)
            return
        
        async for item in input_stream:
            if not self._paused:
                self._stream_stats["items_processed"] += 1
                
                try:
                    if self.filter_condition(item):
                        yield item
                        await self._output_to_stream(item)
                    else:
                        self._stream_stats["items_filtered"] += 1
                        continue
                except Exception:
                    # Log filter error but continue
                    self._stream_stats["items_filtered"] += 1
                    continue
    
    async def _execute_split_stream(self, input_stream: AsyncIterator) -> AsyncIterator:
        """Execute split stream operations."""
        if not self.batch_size:
            # Fallback to individual items
            async for item in input_stream:
                if not self._paused:
                    self._stream_stats["items_processed"] += 1
                    yield item
                    await self._output_to_stream(item)
            return
        
        batch = []
        batch_count = 0
        
        async for item in input_stream:
            if not self._paused:
                batch.append(item)
                batch_count += 1
                self._stream_stats["items_processed"] += 1
                
                if batch_count >= self.batch_size:
                    yield batch
                    batch = []
                    batch_count = 0
        
        # Process remaining items
        if batch:
            yield batch
    
    async def _execute_merge_stream(self, input_stream: AsyncIterator) -> AsyncIterator:
        """Execute merge stream operations."""
        # This would merge multiple input streams
        # For now, treat as passthrough
        async for item in input_stream:
            if not self._paused:
                self._stream_stats["items_processed"] += 1
                yield item
                await self._output_to_stream(item)
    
    async def _output_to_stream(self, item: Any) -> None:
        """Output item to the configured output stream."""
        if self.output_stream:
            await self.output_stream(item)
            self._stream_stats["items_output"] += 1
    
    async def _flush_buffer(self) -> None:
        """Flush the internal buffer to output stream."""
        if not self._buffer:
            return
        
        flush_count = len(self._buffer)
        
        for item in self._buffer:
            await self._output_to_stream(item)
            self._stream_stats["items_output"] += 1
        
        self._buffer.clear()
    
    def pause_stream(self) -> None:
        """Pause the stream processing."""
        self._paused = True
    
    def resume_stream(self) -> None:
        """Resume the stream processing."""
        self._paused = False
    
    def get_stream_stats(self) -> dict[str, Any]:
        """Get current stream statistics."""
        current_time = time.time()
        runtime = current_time - self._stream_stats.get("start_time", current_time)
        
        return {
            **self._stream_stats,
            "runtime": runtime,
            "buffer_size": len(self._buffer),
            "is_running": self._running,
            "is_paused": self._paused,
            "items_per_second": self._stream_stats["items_processed"] / runtime if runtime > 0 else 0
        }
    
    def set_transform_function(self, transform_function: Callable[[Any], Any]) -> None:
        """Set the transform function."""
        self.stream_type = "transform"
        self.transform_function = transform_function
    
    def set_filter_condition(self, filter_condition: Callable[[Any], bool]) -> None:
        """Set the filter condition."""
        self.stream_type = "filter"
        self.filter_condition = filter_condition
    
    def set_buffer_size(self, buffer_size: int) -> None:
        """Set the buffer size."""
        self.buffer_size = buffer_size
        self._buffer = deque(maxlen=buffer_size)
    
    def set_output_stream(self, output_stream: Callable[[Any], None]) -> None:
        """Set the output stream destination."""
        self.output_stream = output_stream
    
    async def cleanup(self) -> None:
        """Cleanup stream node resources."""
        self._running = False
        self._paused = False
        self._buffer.clear()
        self._stream_stats = {
            "items_processed": 0,
            "items_filtered": 0,
            "items_output": 0,
            "bytes_processed": 0,
            "start_time": None,
            "last_flush": None
        }
        
        await super().cleanup()


class BatchStreamNode(StreamNode):
    """Specialized node for batched stream processing."""
    
    def __init__(
        self,
        node_id: str = "batch_stream",
        batch_size: int = 100,
        batch_timeout: float = 5.0,
        description: str = "Batched stream processing"
    ) -> None:
        super().__init__(
            node_id=node_id,
            stream_type="buffer",
            batch_size=batch_size,
            description=description
        )
        
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute batched stream processing with timeout."""
        input_stream = state.get("input_stream", self.input_stream)
        
        if not input_stream:
            raise ValueError("Input stream is required for batch stream processing")
        
        batch = []
        batch_start_time = time.time()
        
        async for item in input_stream:
            if not self._paused:
                batch.append(item)
                self._stream_stats["items_processed"] += 1
                
                # Check if batch is full or timeout reached
                if (len(batch) >= self.batch_size or 
                    time.time() - batch_start_time >= self.batch_timeout):
                    
                    yield batch
                    batch = []
                    batch_start_time = time.time()
        
        # Process remaining items
        if batch:
            yield batch


class SplitStreamNode(StreamNode):
    """Specialized node for splitting streams into multiple outputs."""
    
    def __init__(
        self,
        split_function: Callable[[Any], list[Any]],
        output_streams: list[Callable[[Any], None]],
        node_id: str = "split_stream",
        description: str = "Split stream processing"
    ) -> None:
        super().__init__(
            node_id=node_id,
            stream_type="split",
            description=description
        )
        
        self.split_function = split_function
        self.output_streams = output_streams
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute split stream processing."""
        input_stream = state.get("input_stream", self.input_stream)
        
        if not input_stream or not self.split_function or not self.output_streams:
            raise ValueError("Input stream, split function, and output streams are required")
        
        async for item in input_stream:
            if not self._paused:
                self._stream_stats["items_processed"] += 1
                
                try:
                    split_items = self.split_function(item)
                    
                    # Send to each output stream
                    for i, split_item in enumerate(split_items):
                        if i < len(self.output_streams):
                            await self.output_streams[i](split_item)
                
                except Exception:
                    # Log split error but continue
                    self._stream_stats["items_filtered"] += 1
                    continue
        
        return {
            "result": None,
            "stream_data": None,
            "metadata": {
                "stream_type": "split",
                "output_streams": len(self.output_streams),
                "items_processed": self._stream_stats["items_processed"]
            }
        }
