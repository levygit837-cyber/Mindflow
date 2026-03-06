"""Test gRPC server functionality."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from omnimind_backend.grpc.server import GrpcAgentServer, get_server, start_grpc_server, stop_grpc_server


class TestGrpcAgentServer:
    """Test the enhanced gRPC server implementation."""
    
    def test_server_initialization(self):
        """Test server initialization with default settings."""
        server = GrpcAgentServer()
        
        assert server.get_host() == "0.0.0.0"  # Default from settings
        assert server.get_port() == 50051  # Default from settings
        assert server.is_running() is False
        assert server._server is None
        assert server._start_time is None
    
    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        """Test server start and stop lifecycle."""
        server = GrpcAgentServer()
        
        # Mock the gRPC server to avoid starting real server
        mock_grpc_server = MagicMock()
        mock_grpc_server.start = AsyncMock()
        mock_grpc_server.stop = AsyncMock()
        mock_grpc_server.wait_for_termination = AsyncMock()
        
        with patch('grpc.aio.server', return_value=mock_grpc_server), \
             patch('omnimind_backend.grpc.server.pb2_grpc.add_AgentRuntimeServiceServicer_to_server'):
            
            await server.start()
            
            assert server.is_running() is True
            assert server._server is mock_grpc_server
            assert server._start_time is not None
            mock_grpc_server.start.assert_called_once()
            
            await server.stop()
            
            assert server.is_running() is False
            mock_grpc_server.stop.assert_called_once_with(30.0)
    
    @pytest.mark.asyncio
    async def test_server_start_already_running(self):
        """Test starting server when already running."""
        server = GrpcAgentServer()
        
        # Mock server as already running
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        server._running = True
        
        await server.start()
        
        # Should not call start again
        mock_grpc_server.start.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_server_stop_not_running(self):
        """Test stopping server when not running."""
        server = GrpcAgentServer()
        
        # Should not raise any errors
        await server.stop()
        
        assert server.is_running() is False
    
    @pytest.mark.asyncio
    async def test_server_wait_for_termination(self):
        """Test waiting for server termination."""
        server = GrpcAgentServer()
        
        # Mock server
        mock_grpc_server = MagicMock()
        mock_grpc_server.wait_for_termination = AsyncMock()
        server._server = mock_grpc_server
        
        await server.wait_for_termination()
        
        mock_grpc_server.wait_for_termination.assert_called_once()
    
    def test_add_interceptor(self):
        """Test adding interceptor to server."""
        server = GrpcAgentServer()
        
        # Mock server
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        
        mock_interceptor = MagicMock()
        server.add_interceptor(mock_interceptor)
        
        mock_grpc_server.add_interceptor.assert_called_once_with(mock_interceptor)
    
    def test_add_interceptor_no_server(self):
        """Test adding interceptor when server not initialized."""
        server = GrpcAgentServer()
        
        mock_interceptor = MagicMock()
        
        # Should not raise error, just log warning
        server.add_interceptor(mock_interceptor)
        
        # No server to add interceptor to
        assert server._server is None
    
    def test_add_service(self):
        """Test adding service to server."""
        server = GrpcAgentServer()
        
        # Mock server
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        
        mock_service = MagicMock()
        server.add_service(mock_service)
        
        mock_grpc_server.add_service.assert_called_once_with(mock_service)
    
    def test_add_service_no_server(self):
        """Test adding service when server not initialized."""
        server = GrpcAgentServer()
        
        mock_service = MagicMock()
        
        # Should not raise error, just log warning
        server.add_service(mock_service)
        
        # No server to add service to
        assert server._server is None
    
    @pytest.mark.asyncio
    async def test_setup_interceptors(self):
        """Test interceptor setup."""
        server = GrpcAgentServer()
        
        # Mock server and settings
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        server.settings.app_env = "development"
        
        with patch('omnimind_backend.grpc.server.ErrorHandlerInterceptor') as mock_interceptor_class:
            mock_interceptor = MagicMock()
            mock_interceptor_class.return_value = mock_interceptor
            
            server._setup_interceptors()
            
            mock_interceptor_class.assert_called_once_with(debug=True)
            mock_grpc_server.add_interceptor.assert_called_once_with(mock_interceptor)
    
    @pytest.mark.asyncio
    async def test_setup_services(self):
        """Test service setup."""
        server = GrpcAgentServer()
        
        # Mock server
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        
        with patch('omnimind_backend.grpc.server.pb2_grpc.add_AgentRuntimeServiceServicer_to_server') as mock_add_service:
            await server._setup_services()
            
            mock_add_service.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_services_missing_bindings(self):
        """Test service setup with missing generated bindings."""
        server = GrpcAgentServer()
        
        # Mock server
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        
        with patch('omnimind_backend.grpc.server.pb2_grpc', side_effect=ImportError("No module")):
            with pytest.raises(RuntimeError, match="Missing generated gRPC bindings"):
                await server._setup_services()
    
    @pytest.mark.asyncio
    async def test_configure_port_insecure(self):
        """Test port configuration without TLS."""
        server = GrpcAgentServer()
        server.settings.app_env = "development"
        server.settings.grpc_tls_cert_path = None
        server.settings.grpc_tls_key_path = None
        
        # Mock server
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        
        await server._configure_port()
        
        mock_grpc_server.add_insecure_port.assert_called_once_with(f"{server._host}:{server._port}")
        mock_grpc_server.add_secure_port.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_configure_port_tls_missing_files(self):
        """Test TLS configuration with missing certificate files."""
        server = GrpcAgentServer()
        server.settings.app_env = "production"
        server.settings.grpc_tls_cert_path = "/path/to/missing.crt"
        server.settings.grpc_tls_key_path = "/path/to/missing.key"
        
        # Mock server and pathlib
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        
        with patch('pathlib.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path
            
            await server._configure_port()
            
            # Should fall back to insecure port
            mock_grpc_server.add_insecure_port.assert_called_once_with(f"{server._host}:{server._port}")
            mock_grpc_server.add_secure_port.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_configure_port_tls_success(self):
        """Test successful TLS configuration."""
        server = GrpcAgentServer()
        server.settings.app_env = "production"
        server.settings.grpc_tls_cert_path = "/path/to/cert.crt"
        server.settings.grpc_tls_key_path = "/path/to/key.key"
        
        # Mock server and pathlib
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        
        with patch('pathlib.Path') as mock_path_class, \
             patch('grpc.ssl_server_credentials') as mock_ssl_credentials:
            
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.read_bytes.return_value = b"certificate_data"
            mock_path_class.return_value = mock_path
            
            mock_credentials = MagicMock()
            mock_ssl_credentials.return_value = mock_credentials
            
            await server._configure_port()
            
            mock_grpc_server.add_secure_port.assert_called_once_with(
                f"{server._host}:{server._port}", mock_credentials
            )
            mock_grpc_server.add_insecure_port.assert_not_called()
    
    def test_get_uptime_seconds(self):
        """Test uptime calculation."""
        server = GrpcAgentServer()
        
        # Test when not started
        uptime = server.get_uptime_seconds()
        assert uptime == 0.0
        
        # Test when started (mock)
        import time
        server._start_time = time.time() - 10  # 10 seconds ago
        uptime = server.get_uptime_seconds()
        assert uptime >= 9.0  # Allow for small timing differences
        assert uptime <= 11.0


class TestServerManagement:
    """Test server management functions."""
    
    @pytest.mark.asyncio
    async def test_get_server_singleton(self):
        """Test get_server returns singleton instance."""
        # Clear any existing server
        import omnimind_backend.grpc.server
        omnimind_backend.grpc.server._server_instance = None
        
        server1 = await get_server()
        server2 = await get_server()
        
        assert server1 is server2
    
    @pytest.mark.asyncio
    async def test_start_grpc_server(self):
        """Test start_grpc_server function."""
        # Clear any existing server
        import omnimind_backend.grpc.server
        omnimind_backend.grpc.server._server_instance = None
        
        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.start = AsyncMock()
        
        with patch('omnimind_backend.grpc.server.get_server', return_value=mock_server):
            result = await start_grpc_server()
            
            assert result is mock_server
            mock_server.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_grpc_server_already_running(self):
        """Test start_grpc_server when already running."""
        # Clear any existing server
        import omnimind_backend.grpc.server
        omnimind_backend.grpc.server._server_instance = None
        
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        mock_server.start = AsyncMock()
        
        with patch('omnimind_backend.grpc.server.get_server', return_value=mock_server):
            result = await start_grpc_server()
            
            assert result is mock_server
            mock_server.start.assert_not_called()  # Should not start if already running
    
    @pytest.mark.asyncio
    async def test_stop_grpc_server(self):
        """Test stop_grpc_server function."""
        # Set up a running server
        import omnimind_backend.grpc.server
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        mock_server.stop = AsyncMock()
        omnimind_backend.grpc.server._server_instance = mock_server
        
        await stop_grpc_server()
        
        mock_server.stop.assert_called_once()
        assert omnimind_backend.grpc.server._server_instance is None
    
    @pytest.mark.asyncio
    async def test_stop_grpc_server_not_running(self):
        """Test stop_grpc_server when not running."""
        # Clear any existing server
        import omnimind_backend.grpc.server
        omnimind_backend.grpc.server._server_instance = None
        
        # Should not raise error
        await stop_grpc_server()
        
        assert omnimind_backend.grpc.server._server_instance is None
