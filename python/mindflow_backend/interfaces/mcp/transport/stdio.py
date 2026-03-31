"""
Stdio MCP Transport Implementation

Transport implementation for MCP communication over standard input/output.
Suitable for command-line tools and subprocess communication.
"""

import asyncio
import json
import subprocess

from mindflow_backend.interfaces.mcp.transport.base import (
    ConnectionError,
    MCPTransport,
    MessageError,
    TransportError,
    TransportState,
)
from mindflow_backend.schemas.mcp.base import MCPMessage
from mindflow_backend.schemas.mcp.transport import StdioConfig


class StdioTransportError(TransportError):
    """Exception specific to stdio transport errors."""
    pass


class StdioTransport(MCPTransport):
    """
    MCP transport implementation using standard input/output.
    
    This transport is commonly used for command-line MCP servers
    where communication happens via stdin/stdout.
    """
    
    def __init__(self, config: StdioConfig):
        """
        Initialize stdio transport.
        
        Args:
            config: Stdio transport configuration
        """
        super().__init__(config)
        self.process: subprocess.Popen | None = None
        self.stdin_writer: asyncio.StreamWriter | None = None
        self.stdout_reader: asyncio.StreamReader | None = None
        self.stderr_reader: asyncio.StreamReader | None = None
        self._stderr_monitor_task: asyncio.Task | None = None
    
    async def connect(self) -> None:
        """
        Start the subprocess and establish stdio communication.
        
        Raises:
            ConnectionError: If subprocess fails to start
        """
        if self.state != TransportState.DISCONNECTED:
            raise ConnectionError(f"Cannot connect from state {self.state}")
        
        self._set_state(TransportState.CONNECTING)
        
        try:
            self.logger.info(f"Starting subprocess: {' '.join(self.config.command)}")
            
            # Start the subprocess
            self.process = subprocess.Popen(
                self.config.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.config.working_directory,
                env=self.config.environment,
                text=False,  # Use bytes for better control
                bufsize=0,  # Unbuffered
            )
            
            # Create asyncio streams from process pipes
            self.stdin_writer = asyncio.StreamWriter(
                self.process.stdin,
                {},
                None,
                asyncio.get_event_loop()
            )
            
            self.stdout_reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self.stdout_reader)
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: protocol,
                self.process.stdout
            )
            
            self.stderr_reader = asyncio.StreamReader()
            stderr_protocol = asyncio.StreamReaderProtocol(self.stderr_reader)
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: stderr_protocol,
                self.process.stderr
            )
            
            # Start monitoring stderr
            self._stderr_monitor_task = asyncio.create_task(self._monitor_stderr())
            
            # Wait a moment to ensure process is running
            await asyncio.sleep(0.1)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise ConnectionError(
                    f"Process exited immediately with code {self.process.returncode}. "
                    f"stderr: {stderr.decode(self.config.stderr_encoding, errors='replace')}"
                )
            
            self._set_state(TransportState.CONNECTED)
            self._connection_info = {
                "pid": self.process.pid,
                "command": self.config.command,
                "working_directory": self.config.working_directory,
                "environment": self.config.environment,
            }
            
            self.logger.info(f"Stdio transport connected to process {self.process.pid}")
            
        except Exception as e:
            self._set_state(TransportState.ERROR)
            await self._cleanup()
            raise ConnectionError(f"Failed to connect stdio transport: {e}")
    
    async def disconnect(self) -> None:
        """Close the subprocess and cleanup resources."""
        if self.state == TransportState.DISCONNECTED:
            return
        
        self._set_state(TransportState.CLOSING)
        await self._cleanup()
        self._set_state(TransportState.DISCONNECTED)
        
        self.logger.info("Stdio transport disconnected")
    
    async def send_message(self, message: MCPMessage) -> None:
        """
        Send a message via stdin.
        
        Args:
            message: The message to send
            
        Raises:
            MessageError: If sending fails
        """
        if not self.is_connected or not self.stdin_writer:
            raise ConnectionError("Transport is not connected")
        
        try:
            # Serialize message to JSON
            message_json = message.model_dump_json(exclude_none=True)
            message_bytes = (message_json + '\n').encode(self.config.stdin_encoding)
            
            # Send message
            self.stdin_writer.write(message_bytes)
            await self.stdin_writer.drain()
            
            self._update_metrics("sent", len(message_bytes))
            self.logger.debug(f"Sent message: {message_json[:100]}...")
            
        except Exception as e:
            self._update_metrics("error")
            raise MessageError(f"Failed to send message: {e}")
    
    async def receive_message(self) -> MCPMessage | None:
        """
        Receive a message from stdout.
        
        Returns:
            Optional[MCPMessage]: Received message or None if no message available
            
        Raises:
            MessageError: If receiving fails
        """
        if not self.is_connected or not self.stdout_reader:
            raise ConnectionError("Transport is not connected")
        
        try:
            # Read a line from stdout
            line_bytes = await self.stdout_reader.readline()
            
            if not line_bytes:
                # EOF reached
                if self.process and self.process.poll() is not None:
                    raise ConnectionError(f"Process exited with code {self.process.returncode}")
                return None
            
            # Decode and parse message
            line = line_bytes.decode(self.config.stdout_encoding, errors='replace').strip()
            
            if not line:
                return None
            
            # Parse JSON message
            try:
                message_data = json.loads(line)
                message = MCPMessage.model_validate(message_data)
            except json.JSONDecodeError as e:
                raise MessageError(f"Invalid JSON received: {e}")
            except Exception as e:
                raise MessageError(f"Invalid message format: {e}")
            
            self._update_metrics("received", len(line_bytes))
            self.logger.debug(f"Received message: {line[:100]}...")
            
            return message
            
        except asyncio.CancelledError:
            return None
        except Exception as e:
            self._update_metrics("error")
            raise MessageError(f"Failed to receive message: {e}")
    
    async def _monitor_stderr(self) -> None:
        """
        Monitor stderr for error messages and logging.
        """
        if not self.stderr_reader:
            return
        
        try:
            while self.is_connected:
                line_bytes = await self.stderr_reader.readline()
                
                if not line_bytes:
                    break
                
                line = line_bytes.decode(self.config.stderr_encoding, errors='replace').strip()
                
                if line:
                    # Log stderr output
                    self.logger.warning(f"stderr: {line}")
                    
        except Exception as e:
            self.logger.error(f"Error monitoring stderr: {e}")
    
    async def _cleanup(self) -> None:
        """Cleanup subprocess and related resources."""
        # Cancel stderr monitor
        if self._stderr_monitor_task:
            self._stderr_monitor_task.cancel()
            try:
                await self._stderr_monitor_task
            except asyncio.CancelledError:
                pass
            self._stderr_monitor_task = None
        
        # Close process
        if self.process:
            try:
                if self.process.poll() is None:
                    # Process is still running, terminate it
                    self.process.terminate()
                    try:
                        await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None, self.process.wait),
                            timeout=5.0
                        )
                    except TimeoutError:
                        # Force kill if terminate doesn't work
                        self.process.kill()
                        await asyncio.get_event_loop().run_in_executor(None, self.process.wait)
            except Exception as e:
                self.logger.error(f"Error cleaning up process: {e}")
            finally:
                self.process = None
        
        # Close streams
        if self.stdin_writer:
            try:
                self.stdin_writer.close()
                await self.stdin_writer.wait_closed()
            except Exception as e:
                self.logger.error(f"Error closing stdin writer: {e}")
            finally:
                self.stdin_writer = None
        
        self.stdout_reader = None
        self.stderr_reader = None
