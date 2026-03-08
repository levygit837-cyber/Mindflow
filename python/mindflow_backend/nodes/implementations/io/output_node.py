"""Output Node - Handles data output in I/O pipelines.

This node manages data output to various destinations including
file output, API output, stream output, and database output.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union
import asyncio

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode


class OutputNode(StatefulNode, BaseNode):
    """Node that handles data output to various destinations.
    
    This node supports various output types:
    - Static output: Output to predefined static destination
    - File output: Write to file system
    - API output: Send to API endpoints
    - Stream output: Write to data streams
    - Database output: Write to database
    - Queue output: Write to message queue
    """
    
    def __init__(
        self,
        node_id: str = "output",
        output_type: str = "static",  # static, file, api, stream, database, queue
        output_data: Optional[Any] = None,
        file_path: Optional[str] = None,
        api_config: Optional[Dict[str, Any]] = None,
        stream_destination: Optional[Callable[[Any], None]] = None,
        database_config: Optional[Dict[str, Any]] = None,
        queue_config: Optional[Dict[str, Any]] = None,
        format_function: Optional[Callable[[Any], str]] = None,
        append_mode: bool = False,
        encoding: str = "utf-8",
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.IO,
            category=NodeCategory.IO_OUTPUT,
            description=description or f"{output_type} output"
        )
        
        self.output_type = output_type.lower()
        self.output_data = output_data
        self.file_path = file_path
        self.api_config = api_config or {}
        self.stream_destination = stream_destination
        self.database_config = database_config or {}
        self.queue_config = queue_config or {}
        self.format_function = format_function
        self.append_mode = append_mode
        self.encoding = encoding
        
        # Required inputs
        self._setup_required_inputs()
        self.config.outputs = {"result", "output_status", "metadata"}
        
        # Internal state
        self._output_count = 0
        self._output_history = []
    
    def _setup_required_inputs(self) -> None:
        """Setup required inputs based on output type."""
        if self.output_type == "static":
            self.config.required_inputs = {"output_data"}
        elif self.output_type == "file":
            self.config.required_inputs = {"output_data", "file_path"}
        elif self.output_type == "api":
            self.config.required_inputs = {"output_data", "endpoint", "method"}
        elif self.output_type == "stream":
            self.config.required_inputs = {"output_data"}
        elif self.output_type == "database":
            self.config.required_inputs = {"output_data", "connection"}
        elif self.output_type == "queue":
            self.config.required_inputs = {"output_data", "queue_name"}
        else:
            self.config.required_inputs = {"output_data"}
    
    async def initialize(self) -> None:
        """Initialize the output node."""
        await super().initialize()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the output operation based on configured type."""
        output_data = state.get("output_data", self.output_data)
        
        try:
            # Format output data if format function provided
            if self.format_function:
                formatted_data = self.format_function(output_data)
            else:
                formatted_data = output_data
            
            # Apply output based on type
            if self.output_type == "static":
                result = await self._execute_static_output(formatted_data, state)
            elif self.output_type == "file":
                result = await self._execute_file_output(formatted_data, state)
            elif self.output_type == "api":
                result = await self._execute_api_output(formatted_data, state)
            elif self.output_type == "stream":
                result = await self._execute_stream_output(formatted_data, state)
            elif self.output_type == "database":
                result = await self._execute_database_output(formatted_data, state)
            elif self.output_type == "queue":
                result = await self._execute_queue_output(formatted_data, state)
            else:
                raise ValueError(f"Unsupported output type: {self.output_type}")
            
            self._output_count += 1
            
            return {
                "result": formatted_data,
                "output_status": "success",
                "metadata": {
                    "output_type": self.output_type,
                    "output_count": self._output_count,
                    "destination": self._get_destination_info()
                }
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("output_node_execution_failed", 
                       output_type=self.output_type, 
                       error=str(e))
            
            return {
                "result": None,
                "output_status": "failed",
                "error": str(e),
                "metadata": {"output_type": self.output_type, "status": "error"}
            }
    
    async def _execute_static_output(self, data: Any, state: Dict[str, Any]) -> Any:
        """Execute static output operation."""
        # Static output just returns the data
        # In a real system, this might update a shared state
        return data
    
    async def _execute_file_output(self, data: Any, state: Dict[str, Any]) -> Any:
        """Execute file output operation."""
        file_path = state.get("file_path", self.file_path)
        
        if not file_path:
            raise ValueError("File path is required for file output")
        
        # Convert data to string if needed
        if isinstance(data, (dict, list)):
            import json
            content = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            content = str(data)
        
        # Write to file
        try:
            mode = 'a' if self.append_mode else 'w'
            with open(file_path, mode, encoding=self.encoding) as file:
                file.write(content)
                file_size = file.tell()
            
            # Add to history
            self._output_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": data,
                "source": "file",
                "file_path": file_path,
                "file_size": file_size,
                "append_mode": self.append_mode,
                "encoding": self.encoding
            })
            
            return data
            
        except IOError as e:
            raise IOError(f"Error writing to file {file_path}: {str(e)}")
    
    async def _execute_api_output(self, data: Any, state: Dict[str, Any]) -> Any:
        """Execute API output operation."""
        endpoint = state.get("endpoint", self.api_config.get("endpoint"))
        method = state.get("method", self.api_config.get("method", "POST"))
        headers = state.get("headers", self.api_config.get("headers", {}))
        
        if not endpoint:
            raise ValueError("API endpoint is required for API output")
        
        try:
            # Make API request
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                if method.upper() == "POST":
                    async with session.post(endpoint, json=data, headers=headers) as response:
                        response_data = await self._process_api_response(response)
                elif method.upper() == "PUT":
                    async with session.put(endpoint, json=data, headers=headers) as response:
                        response_data = await self._process_api_response(response)
                elif method.upper() == "PATCH":
                    async with session.patch(endpoint, json=data, headers=headers) as response:
                        response_data = await self._process_api_response(response)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Add to history
            self._output_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": data,
                "source": "api",
                "endpoint": endpoint,
                "method": method,
                "status": "success"
            })
            
            return data
            
        except Exception as e:
            raise IOError(f"Error calling API {endpoint}: {str(e)}")
    
    async def _process_api_response(self, response) -> Any:
        """Process API response and extract data."""
        if response.status >= 200 and response.status < 300:
            return {"status": "success", "response": response}
        else:
            raise IOError(f"API request failed with status {response.status}")
    
    async def _execute_stream_output(self, data: Any, state: Dict[str, Any]) -> Any:
        """Execute stream output operation."""
        if not self.stream_destination:
            raise ValueError("Stream destination is required for stream output")
        
        try:
            # Send data to stream
            await self.stream_destination(data)
            
            # Add to history
            self._output_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": data,
                "source": "stream",
                "status": "success"
            })
            
            return data
            
        except Exception as e:
            raise IOError(f"Error writing to stream: {str(e)}")
    
    async def _execute_database_output(self, data: Any, state: Dict[str, Any]) -> Any:
        """Execute database output operation."""
        connection_config = state.get("connection", self.database_config.get("connection"))
        
        if not connection_config:
            raise ValueError("Database connection is required for database output")
        
        try:
            # This would integrate with the actual database system
            # For now, simulate database write
            table_name = self.database_config.get("table", "output_data")
            
            # Add to history
            self._output_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": data,
                "source": "database",
                "table": table_name,
                "status": "success"
            })
            
            return data
            
        except Exception as e:
            raise IOError(f"Error writing to database: {str(e)}")
    
    async def _execute_queue_output(self, data: Any, state: Dict[str, Any]) -> Any:
        """Execute queue output operation."""
        queue_name = state.get("queue_name", self.queue_config.get("queue_name"))
        
        if not queue_name:
            raise ValueError("Queue name is required for queue output")
        
        try:
            # This would integrate with the actual message queue system
            # For now, simulate queue write
            import json
            
            message = {
                "data": data,
                "timestamp": asyncio.get_event_loop().time(),
                "source": "output_node"
            }
            
            # Add to history
            self._output_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": data,
                "source": "queue",
                "queue_name": queue_name,
                "status": "success"
            })
            
            return data
            
        except Exception as e:
            raise IOError(f"Error writing to queue {queue_name}: {str(e)}")
    
    def _get_destination_info(self) -> Dict[str, Any]:
        """Get information about the output destination."""
        if self.output_type == "file":
            return {"file_path": self.file_path, "append_mode": self.append_mode}
        elif self.output_type == "api":
            return {"endpoint": self.api_config.get("endpoint"), "method": self.api_config.get("method", "POST")}
        elif self.output_type == "database":
            return {"table": self.database_config.get("table"), "connection": self.database_config.get("connection")}
        elif self.output_type == "queue":
            return {"queue_name": self.queue_config.get("queue_name")}
        else:
            return {}
    
    def get_output_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the output history."""
        return self._output_history[-limit:] if len(self._output_history) > limit else self._output_history
    
    def clear_output_history(self) -> None:
        """Clear the output history."""
        self._output_history = []
    
    def set_output_data(self, output_data: Any) -> None:
        """Set static output data."""
        self.output_type = "static"
        self.output_data = output_data
        self._setup_required_inputs()
    
    def get_output_info(self) -> Dict[str, Any]:
        """Get information about the current output configuration."""
        return {
            "output_type": self.output_type,
            "output_count": self._output_count,
            "destination": self._get_destination_info(),
            "has_format_function": self.format_function is not None,
            "append_mode": self.append_mode,
            "encoding": self.encoding,
            "history_size": len(self._output_history)
        }
    
    async def cleanup(self) -> None:
        """Cleanup output node resources."""
        self._output_count = 0
        self._output_history = []
        
        await super().cleanup()


class StreamOutputNode(OutputNode):
    """Specialized node for streaming data output."""
    
    def __init__(
        self,
        node_id: str = "stream_output",
        stream_destination: Callable[[Any], None],
        buffer_size: int = 1000,
        flush_interval: float = 1.0,
        description: str = "Streaming data output"
    ) -> None:
        super().__init__(
            node_id=node_id,
            output_type="stream",
            stream_destination=stream_destination,
            description=description
        )
        
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute streaming output with buffering."""
        output_data = state.get("output_data")
        buffer = []
        item_count = 0
        
        try:
            # Buffer data and flush periodically
            async for item in output_data if isinstance(output_data, (list, tuple)) else [output_data]:
                buffer.append(item)
                item_count += 1
                
                if len(buffer) >= self.buffer_size:
                    await self.stream_destination(buffer)
                    self._output_history.append({
                        "timestamp": asyncio.get_event_loop().time(),
                        "data": list(buffer),
                        "source": "stream",
                        "buffer_size": len(buffer),
                        "item_count": item_count,
                        "flushed": True
                    })
                    
                    buffer = []
                    
                    # Wait for flush interval
                    await asyncio.sleep(self.flush_interval)
            
            # Flush remaining items
            if buffer:
                await self.stream_destination(buffer)
                self._output_history.append({
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": list(buffer),
                    "source": "stream",
                    "buffer_size": len(buffer),
                    "item_count": item_count,
                    "final_flush": True
                })
            
            return {
                "result": output_data,
                "output_status": "success",
                "metadata": {
                    "output_type": "stream",
                    "total_items": item_count,
                    "buffer_size": self.buffer_size
                }
            }
            
        except Exception as e:
            raise IOError(f"Error in stream output: {str(e)}")
