"""Input Node - Handles data input in I/O pipelines.

This node manages data input from various sources including
user input, file input, API input, and stream input.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union, AsyncIterator
import asyncio

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode


class InputNode(StatefulNode, BaseNode):
    """Node that handles data input from various sources.
    
    This node supports various input types:
    - Static input: Predefined static data
    - File input: Read from file system
    - API input: Read from API endpoints
    - Stream input: Read from data streams
    - User input: Interactive user input
    - Form input: Structured form data input
    """
    
    def __init__(
        self,
        node_id: str = "input",
        input_type: str = "static",  # static, file, api, stream, user, form
        input_data: Optional[Any] = None,
        file_path: Optional[str] = None,
        api_config: Optional[Dict[str, Any]] = None,
        stream_source: Optional[AsyncIterator] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        validation_function: Optional[Callable[[Any], bool]] = None,
        timeout: Optional[float] = None,
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.IO,
            category=NodeCategory.IO_INPUT,
            description=description or f"{input_type} input"
        )
        
        self.input_type = input_type.lower()
        self.input_data = input_data
        self.file_path = file_path
        self.api_config = api_config or {}
        self.stream_source = stream_source
        self.input_schema = input_schema
        self.validation_function = validation_function
        self.timeout = timeout
        
        # Required inputs
        self._setup_required_inputs()
        self.config.outputs = {"result", "input_data", "metadata"}
        
        # Internal state
        self._input_count = 0
        self._input_history = []
    
    def _setup_required_inputs(self) -> None:
        """Setup required inputs based on input type."""
        if self.input_type == "static":
            self.config.required_inputs = set()
        elif self.input_type == "file":
            self.config.required_inputs = {"file_path"}
        elif self.input_type == "api":
            self.config.required_inputs = {"endpoint", "method", "headers"}
        elif self.input_type == "stream":
            self.config.required_inputs = {"stream_source"}
        elif self.input_type == "user":
            self.config.required_inputs = {"prompt", "default_value"}
        elif self.input_type == "form":
            self.config.required_inputs = {"form_data"}
        else:
            self.config.required_inputs = {"input_data"}
    
    async def initialize(self) -> None:
        """Initialize the input node."""
        await super().initialize()
        
        # Pre-load static data
        if self.input_type == "static" and self.input_data:
            self._input_count = 1
            self._input_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": self.input_data,
                "source": "static"
            })
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the input operation based on configured type."""
        try:
            if self.input_type == "static":
                result = await self._execute_static_input(state)
            elif self.input_type == "file":
                result = await self._execute_file_input(state)
            elif self.input_type == "api":
                result = await self._execute_api_input(state)
            elif self.input_type == "stream":
                result = await self._execute_stream_input(state)
            elif self.input_type == "user":
                result = await self._execute_user_input(state)
            elif self.input_type == "form":
                result = await self._execute_form_input(state)
            else:
                raise ValueError(f"Unsupported input type: {self.input_type}")
            
            self._input_count += 1
            
            return {
                "result": result,
                "input_data": result,
                "metadata": {
                    "input_type": self.input_type,
                    "input_count": self._input_count,
                    "validation_passed": True,
                    "source": self.input_type
                }
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("input_node_execution_failed", 
                       input_type=self.input_type, 
                       error=str(e))
            
            return {
                "result": None,
                "input_data": None,
                "error": str(e),
                "metadata": {"input_type": self.input_type, "status": "error"}
            }
    
    async def _execute_static_input(self, state: Dict[str, Any]) -> Any:
        """Execute static input operation."""
        if not self.input_data:
            raise ValueError("Static input data is required")
        
        # Validate input if validation function provided
        if self.validation_function and not self.validation_function(self.input_data):
            raise ValueError("Static input data failed validation")
        
        return self.input_data
    
    async def _execute_file_input(self, state: Dict[str, Any]) -> Any:
        """Execute file input operation."""
        file_path = state.get("file_path", self.file_path)
        
        if not file_path:
            raise ValueError("File path is required for file input")
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Validate content if validation function provided
            if self.validation_function and not self.validation_function(content):
                raise ValueError(f"File content failed validation: {file_path}")
            
            # Add to history
            self._input_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": content,
                "source": "file",
                "file_path": file_path,
                "size": len(content)
            })
            
            return content
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file not found: {file_path}")
        except IOError as e:
            raise IOError(f"Error reading input file {file_path}: {str(e)}")
    
    async def _execute_api_input(self, state: Dict[str, Any]) -> Any:
        """Execute API input operation."""
        endpoint = state.get("endpoint", self.api_config.get("endpoint"))
        method = state.get("method", self.api_config.get("method", "GET"))
        headers = state.get("headers", self.api_config.get("headers", {}))
        
        if not endpoint:
            raise ValueError("API endpoint is required for API input")
        
        try:
            # Make API request
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(endpoint, headers=headers) as response:
                        response_data = await self._process_api_response(response)
                elif method.upper() == "POST":
                    data = state.get("data", {})
                    async with session.post(endpoint, json=data, headers=headers) as response:
                        response_data = await self._process_api_response(response)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Validate response if validation function provided
            if self.validation_function and not self.validation_function(response_data):
                raise ValueError(f"API response failed validation: {endpoint}")
            
            # Add to history
            self._input_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": response_data,
                "source": "api",
                "endpoint": endpoint,
                "method": method,
                "status": "success"
            })
            
            return response_data
            
        except Exception as e:
            raise IOError(f"Error calling API {endpoint}: {str(e)}")
    
    async def _process_api_response(self, response) -> Any:
        """Process API response and extract data."""
        if response.status >= 200 and response.status < 300:
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                return await response.json()
            else:
                return await response.text()
        else:
            raise IOError(f"API request failed with status {response.status}")
    
    async def _execute_stream_input(self, state: Dict[str, Any]) -> Any:
        """Execute stream input operation."""
        stream_source = state.get("stream_source", self.stream_source)
        
        if not stream_source:
            raise ValueError("Stream source is required for stream input")
        
        # Collect data from stream
        collected_data = []
        
        try:
            async for item in stream_source:
                collected_data.append(item)
                
                # Add to history for each item
                self._input_history.append({
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": item,
                    "source": "stream",
                    "item_index": len(collected_data)
                })
            
            # Validate collected data if validation function provided
            if self.validation_function and not self.validation_function(collected_data):
                raise ValueError("Stream data failed validation")
            
            return collected_data
            
        except Exception as e:
            raise IOError(f"Error reading from stream: {str(e)}")
    
    async def _execute_user_input(self, state: Dict[str, Any]) -> Any:
        """Execute user input operation."""
        prompt = state.get("prompt", "Please provide input:")
        default_value = state.get("default_value")
        
        # In a real implementation, this would prompt the user
        # For now, simulate user input
        user_input = default_value or input("User input simulation")
        
        # Validate input if validation function provided
        if self.validation_function and not self.validation_function(user_input):
            raise ValueError("User input failed validation")
        
        # Add to history
        self._input_history.append({
            "timestamp": asyncio.get_event_loop().time(),
            "data": user_input,
            "source": "user",
            "prompt": prompt
        })
        
        return user_input
    
    async def _execute_form_input(self, state: Dict[str, Any]) -> Any:
        """Execute form input operation."""
        form_data = state.get("form_data", {})
        
        if not form_data:
            raise ValueError("Form data is required for form input")
        
        # Validate form data against schema if provided
        if self.input_schema:
            validated_data = self._validate_form_data(form_data, self.input_schema)
        else:
            validated_data = form_data
        
        # Validate final data if validation function provided
        if self.validation_function and not self.validation_function(validated_data):
            raise ValueError("Form data failed validation")
        
        # Add to history
        self._input_history.append({
            "timestamp": asyncio.get_event_loop().time(),
            "data": validated_data,
            "source": "form",
            "schema": self.input_schema
        })
        
        return validated_data
    
    def _validate_form_data(self, form_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate form data against schema."""
        validated_data = {}
        
        for field_name, field_schema in schema.items():
            field_value = form_data.get(field_name)
            
            if field_value is None and field_schema.get("required", False):
                raise ValueError(f"Required field {field_name} is missing")
            
            field_type = field_schema.get("type")
            if field_type and not self._check_field_type(field_value, field_type):
                raise ValueError(f"Field {field_name} has invalid type")
            
            validated_data[field_name] = field_value
        
        return validated_data
    
    def _check_field_type(self, value: Any, field_type: str) -> bool:
        """Check if value matches expected field type."""
        if field_type == "string":
            return isinstance(value, str)
        elif field_type == "number":
            return isinstance(value, (int, float))
        elif field_type == "boolean":
            return isinstance(value, bool)
        elif field_type == "array":
            return isinstance(value, list)
        elif field_type == "object":
            return isinstance(value, dict)
        
        return True
    
    def get_input_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the input history."""
        return self._input_history[-limit:] if len(self._input_history) > limit else self._input_history
    
    def clear_input_history(self) -> None:
        """Clear the input history."""
        self._input_history = []
    
    def set_input_data(self, input_data: Any) -> None:
        """Set static input data."""
        self.input_type = "static"
        self.input_data = input_data
        self._setup_required_inputs()
    
    def get_input_info(self) -> Dict[str, Any]:
        """Get information about the current input configuration."""
        return {
            "input_type": self.input_type,
            "input_count": self._input_count,
            "file_path": self.file_path,
            "has_validation": self.validation_function is not None,
            "has_schema": self.input_schema is not None,
            "timeout": self.timeout,
            "history_size": len(self._input_history)
        }
    
    async def cleanup(self) -> None:
        """Cleanup input node resources."""
        self._input_count = 0
        self._input_history = []
        
        await super().cleanup()


class StreamInputNode(InputNode):
    """Specialized node for streaming data input."""
    
    def __init__(
        self,
        node_id: str = "stream_input",
        buffer_size: int = 1000,
        timeout: Optional[float] = None,
        description: str = "Streaming data input"
    ) -> None:
        super().__init__(
            node_id=node_id,
            input_type="stream",
            description=description
        )
        
        self.buffer_size = buffer_size
        self.timeout = timeout
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute streaming input with buffering."""
        stream_source = state.get("stream_source", self.stream_source)
        
        if not stream_source:
            raise ValueError("Stream source is required for stream input")
        
        buffer = []
        item_count = 0
        
        try:
            async for item in stream_source:
                buffer.append(item)
                item_count += 1
                
                # Emit buffer when full or timeout reached
                if len(buffer) >= self.buffer_size:
                    self._input_history.append({
                        "timestamp": asyncio.get_event_loop().time(),
                        "data": list(buffer),
                        "source": "stream",
                        "buffer_size": len(buffer),
                        "item_count": item_count
                    })
                    
                    buffer = []
            
            # Process remaining items in buffer
            if buffer:
                self._input_history.append({
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": list(buffer),
                    "source": "stream",
                    "buffer_size": len(buffer),
                    "item_count": item_count,
                    "stream_complete": True
                })
            
            return {
                "result": buffer,
                "input_data": buffer,
                "metadata": {
                    "input_type": "stream",
                    "total_items": item_count,
                    "buffer_size": self.buffer_size
                }
            }
            
        except Exception as e:
            raise IOError(f"Error in stream input: {str(e)}")


class FileInputNode(InputNode):
    """Specialized node for file-based data input."""
    
    def __init__(
        self,
        node_id: str = "file_input",
        file_path: str,
        encoding: str = "utf-8",
        description: str = "File-based data input"
    ) -> None:
        super().__init__(
            node_id=node_id,
            input_type="file",
            file_path=file_path,
            description=description
        )
        
        self.encoding = encoding
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file input with encoding support."""
        file_path = state.get("file_path", self.file_path)
        
        if not file_path:
            raise ValueError("File path is required for file input")
        
        try:
            with open(file_path, 'r', encoding=self.encoding) as file:
                content = file.read()
            
            # Get file metadata
            import os
            file_stats = os.stat(file_path)
            
            self._input_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "data": content,
                "source": "file",
                "file_path": file_path,
                "size": file_stats.st_size,
                "encoding": self.encoding,
                "modified": file_stats.st_mtime
            })
            
            return {
                "result": content,
                "input_data": content,
                "metadata": {
                    "input_type": "file",
                    "file_size": file_stats.st_size,
                    "encoding": self.encoding
                }
            }
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file not found: {file_path}")
        except UnicodeDecodeError as e:
            raise IOError(f"Encoding error reading file {file_path}: {str(e)}")
