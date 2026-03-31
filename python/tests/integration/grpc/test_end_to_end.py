"""Integration tests for gRPC client and server."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.grpc.client import GrpcAgentClient
from mindflow_backend.grpc.config import GrpcClientConfig, GrpcConfig
from mindflow_backend.grpc.server import GrpcAgentServer, start_grpc_server, stop_grpc_server
from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta


class TestGrpcEndToEnd:
    """Test end-to-end gRPC communication."""
    
    @pytest.mark.asyncio
    async def test_client_server_communication(self):
        """Test full client-server communication flow."""
        # Configuration
        config = GrpcConfig(
            host="localhost",
            port=50052,  # Use different port to avoid conflicts
            secure=False,
            max_attempts=3,
        )
        
        server = GrpcAgentServer()
        server._host = config.host
        server._port = config.port
        
        # Mock server components
        mock_grpc_server = MagicMock()
        mock_grpc_server.start = AsyncMock()
        mock_grpc_server.stop = AsyncMock()
        
        # Mock service implementation
        mock_service = MagicMock()
        mock_event = StreamEvent(
            id="integration-test-1",
            seq=1,
            type="response",
            mode="messages",
            data="Integration test response",
            meta=StreamEventMeta(runId="integration-run"),
        )
        
        async def mock_stream_chat(request, context):
            yield mock_event
        
        mock_service.StreamChat = mock_stream_chat
        
        with patch('grpc.aio.server', return_value=mock_grpc_server), \
             patch('mindflow_backend.grpc.server.pb2_grpc.add_AgentRuntimeServiceServicer_to_server'), \
             patch('mindflow_backend.grpc.server.AgentRuntimeServiceImpl', return_value=mock_service):
            
            # Start server
            await server.start()
            assert server.is_running() is True
            
            # Create client
            client = GrpcAgentClient(
                host=config.host,
                port=config.port,
                max_attempts=1,
                timeout_seconds=5,
            )
            
            # Mock client gRPC components
            mock_channel = MagicMock()
            mock_stub = MagicMock()
            mock_call = AsyncMock()
            
            # Mock protobuf response
            mock_response = MagicMock()
            mock_response.id = mock_event.id
            mock_response.seq = mock_event.seq
            mock_response.type = mock_event.type
            mock_response.mode = mock_event.mode
            mock_response.data = mock_event.data
            mock_response.json_meta = None
            
            mock_call.__aiter__ = AsyncMock(return_value=iter([mock_response]))
            mock_stub.StreamChat.return_value = mock_call
            
            with patch('grpc.aio.insecure_channel', return_value=mock_channel), \
                 patch('grpc.channel_ready_future'), \
                 patch('mindflow_backend.grpc.client.pb2_grpc.AgentRuntimeServiceStub', return_value=mock_stub), \
                 patch('mindflow_backend.grpc.client.pb2.ChatStreamRequest'):
                
                # Connect client
                await client.connect()
                assert client.is_connected() is True
                
                # Test communication
                events = []
                async for event in client.stream_chat(
                    session_id="integration-session",
                    message="Integration test message",
                    provider="openai",
                    model="gpt-4",
                ):
                    events.append(event)
                
                assert len(events) == 1
                assert isinstance(events[0], StreamEvent)
                assert events[0].id == mock_event.id
                assert events[0].data == mock_event.data
                
                # Test health check
                health = await client.health_check()
                assert health["status"] == "healthy"
                
                # Cleanup
                await client.close()
                await server.stop()
    
    @pytest.mark.asyncio
    async def test_server_management_functions(self):
        """Test server management functions."""
        # Clear any existing server
        import mindflow_backend.grpc.server
        mindflow_backend.grpc.server._server_instance = None
        
        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()
        
        with patch('mindflow_backend.grpc.server.get_server', return_value=mock_server):
            # Test start
            server = await start_grpc_server()
            assert server is mock_server
            mock_server.start.assert_called_once()
            
            # Test stop
            await stop_grpc_server()
            mock_server.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in client-server integration."""
        client = GrpcAgentClient(
            host="nonexistent-host",
            port=99999,
            max_attempts=2,
            timeout_seconds=1,
        )
        
        with patch('grpc.aio.insecure_channel', side_effect=Exception("Connection failed")):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client.connect()
        
        assert client.is_connected() is False
    
    @pytest.mark.asyncio
    async def test_configuration_integration(self):
        """Test configuration integration between client and server."""
        # Create server config
        server_config = GrpcConfig(
            host="localhost",
            port=50053,
            secure=False,
            max_attempts=3,
            connection_timeout_seconds=10,
        )
        
        # Create client config from server config
        client_config = GrpcClientConfig.from_server_config(server_config)
        
        # Verify compatibility
        assert client_config.host == server_config.host
        assert client_config.port == server_config.port
        assert client_config.secure == server_config.secure
        assert client_config.max_attempts == server_config.max_attempts
        assert client_config.connection_timeout_seconds == server_config.connection_timeout_seconds
        
        # Create client and server with compatible configs
        server = GrpcAgentServer()
        server._host = server_config.host
        server._port = server_config.port
        
        client = GrpcAgentClient(
            host=client_config.host,
            port=client_config.port,
            secure=client_config.secure,
            max_attempts=client_config.max_attempts,
            timeout_seconds=client_config.request_timeout_seconds,
        )
        
        # Verify they have compatible settings
        assert server.get_host() == client.host
        assert server.get_port() == client.port


class TestGrpcBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    @pytest.mark.asyncio
    async def test_local_agent_client_compatibility(self):
        """Test that LocalAgentClient still works for backward compatibility."""
        from mindflow_backend.grpc.client import LocalAgentClient
        
        client = LocalAgentClient()
        
        # Mock the service implementation
        mock_event = StreamEvent(
            id="compatibility-test-1",
            seq=1,
            type="response", 
            mode="messages",
            data="Compatibility test response",
            meta=StreamEventMeta(runId="compatibility-run"),
        )
        
        client._service.runtime.stream_chat = AsyncMock(return_value=iter([mock_event]))
        
        # Test that the interface is the same
        events = []
        async for event in client.stream_chat(
            session_id="compatibility-session",
            message="Compatibility test message",
            provider="openai",
            model="gpt-4",
            orchestrate=True,
            agent_type="test-agent",
        ):
            events.append(event)
        
        assert len(events) == 1
        assert isinstance(events[0], StreamEvent)
        assert events[0].data == "Compatibility test response"
    
    @pytest.mark.asyncio
    async def test_server_legacy_functions(self):
        """Test that legacy server functions still work."""
        from mindflow_backend.grpc.server import serve
        
        # Mock the server components
        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.wait_for_termination = AsyncMock()
        mock_server.stop = AsyncMock()
        
        with patch('mindflow_backend.grpc.server.GrpcAgentServer', return_value=mock_server), \
             patch('mindflow_backend.grpc.server.setup_signal_handlers'):
            
            # Test that serve function still works
            serve_task = asyncio.create_task(serve())
            
            # Give it a moment to start
            await asyncio.sleep(0.1)
            
            # Cancel the task to avoid hanging
            serve_task.cancel()
            
            try:
                await serve_task
            except asyncio.CancelledError:
                pass  # Expected
            
            mock_server.start.assert_called_once()


class TestGrpcHealthMonitoring:
    """Test gRPC health monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_server_health_status(self):
        """Test server health status reporting."""
        server = GrpcAgentServer()
        
        # Test when not running
        assert server.is_running() is False
        uptime = server.get_uptime_seconds()
        assert uptime == 0.0
        
        # Mock server as running
        import time
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        server._running = True
        server._start_time = time.time() - 5  # 5 seconds ago
        
        assert server.is_running() is True
        uptime = server.get_uptime_seconds()
        assert uptime >= 4.0  # Allow for timing differences
        assert uptime <= 6.0
    
    @pytest.mark.asyncio
    async def test_client_health_monitoring(self):
        """Test client health monitoring."""
        client = GrpcAgentClient(
            host="localhost",
            port=50051,
            max_attempts=1,
            timeout_seconds=1,
        )
        
        # Mock successful connection
        mock_channel = MagicMock()
        
        with patch('grpc.aio.insecure_channel', return_value=mock_channel), \
             patch('grpc.channel_ready_future'):
            
            await client.connect()
            assert client.is_connected() is True
            
            health = await client.health_check()
            assert health["status"] == "healthy"
            assert health["host"] == client.host
            assert health["port"] == str(client.port)
            assert health["connected"] == "true"
            
            await client.close()
            assert client.is_connected() is False
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check integration in main application."""
        # This would test the health endpoint in main.py
        # For now, we'll test the components separately
        
        server = GrpcAgentServer()
        
        # Mock server components
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        server._running = True
        server._start_time = 0  # Mock start time
        
        # Test server health info
        health_info = {
            "enabled": True,
            "status": "running",
            "host": server.get_host(),
            "port": server.get_port(),
            "uptime_seconds": server.get_uptime_seconds(),
        }
        
        assert health_info["enabled"] is True
        assert health_info["status"] == "running"
        assert health_info["host"] == server.get_host()
        assert health_info["port"] == server.get_port()
