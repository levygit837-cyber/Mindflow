"""Test configuration for gRPC client and server."""

from unittest.mock import AsyncMock

import pytest

from mindflow_backend.grpc.client import GrpcAgentClient
from mindflow_backend.grpc.config import GrpcClientConfig, GrpcConfig
from mindflow_backend.grpc.server import GrpcAgentServer
from mindflow_backend.infra.config import get_settings


@pytest.fixture
def grpc_config():
    """Create test gRPC configuration."""
    return GrpcConfig(
        enabled=True,
        host="localhost",
        port=50051,
        secure=False,
        max_attempts=3,
        connection_timeout_seconds=5,
        default_timeout_seconds=30,
    )


@pytest.fixture
def grpc_client_config():
    """Create test gRPC client configuration."""
    return GrpcClientConfig(
        host="localhost",
        port=50051,
        secure=False,
        max_attempts=3,
        connection_timeout_seconds=5,
        request_timeout_seconds=30,
    )


@pytest.fixture
def grpc_client():
    """Create gRPC client instance for testing."""
    return GrpcAgentClient(
        host="localhost",
        port=50051,
        secure=False,
        max_attempts=3,
        timeout_seconds=30,
    )


@pytest.fixture
def grpc_server():
    """Create gRPC server instance for testing."""
    return GrpcAgentServer()


@pytest.fixture
def mock_stream_event():
    """Create mock stream event for testing."""
    from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta
    
    return StreamEvent(
        id="test-event-1",
        seq=1,
        type="response",
        mode="messages",
        data="Test response",
        meta=StreamEventMeta(
            runId="test-run-1",
            turnRunId="test-turn-1",
            node="test-node",
            nodeCategory="TEST",
            userVisible=True,
        ),
    )


class TestGrpcConfig:
    """Test gRPC configuration."""
    
    def test_grpc_config_creation(self, grpc_config):
        """Test creating gRPC configuration."""
        assert grpc_config.enabled is True
        assert grpc_config.host == "localhost"
        assert grpc_config.port == 50051
        assert grpc_config.secure is False
        assert grpc_config.max_attempts == 3
    
    def test_grpc_client_config_creation(self, grpc_client_config):
        """Test creating gRPC client configuration."""
        assert grpc_client_config.host == "localhost"
        assert grpc_client_config.port == 50051
        assert grpc_client_config.secure is False
        assert grpc_client_config.max_attempts == 3
    
    def test_client_config_from_server_config(self, grpc_config):
        """Test creating client config from server config."""
        client_config = GrpcClientConfig.from_server_config(grpc_config)
        assert client_config.host == grpc_config.host
        assert client_config.port == grpc_config.port
        assert client_config.secure == grpc_config.secure
        assert client_config.max_attempts == grpc_config.max_attempts


class TestGrpcAgentClient:
    """Test gRPC agent client."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, grpc_client):
        """Test client initialization."""
        assert grpc_client.host == "localhost"
        assert grpc_client.port == 50051
        assert grpc_client.secure is False
        assert grpc_client.max_attempts == 3
        assert grpc_client.is_connected() is False
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self, grpc_client):
        """Test client as context manager."""
        # Mock the connect method to avoid actual connection
        grpc_client.connect = AsyncMock()
        grpc_client.close = AsyncMock()
        
        async with grpc_client as client:
            assert client is grpc_client
            grpc_client.connect.assert_called_once()
        
        grpc_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_when_disconnected(self, grpc_client):
        """Test health check when client is not connected."""
        # Mock connect to avoid actual connection
        grpc_client.connect = AsyncMock()
        
        result = await grpc_client.health_check()
        
        assert isinstance(result, dict)
        assert "status" in result
        grpc_client.connect.assert_called_once()


class TestGrpcAgentServer:
    """Test gRPC agent server."""
    
    def test_server_initialization(self, grpc_server):
        """Test server initialization."""
        assert grpc_server.get_host() == "0.0.0.0"  # Default from settings
        assert grpc_server.get_port() == 50051  # Default from settings
        assert grpc_server.is_running() is False
    
    @pytest.mark.asyncio
    async def test_server_lifecycle(self, grpc_server):
        """Test server start and stop lifecycle."""
        # Mock the actual gRPC server to avoid starting real server
        mock_server = AsyncMock()
        grpc_server._server = mock_server
        
        await grpc_server.start()
        assert grpc_server.is_running() is True
        mock_server.start.assert_called_once()
        
        await grpc_server.stop()
        assert grpc_server.is_running() is False
        mock_server.stop.assert_called_once()
    
    def test_server_uptime(self, grpc_server):
        """Test server uptime calculation."""
        import time
        
        # Test when not started
        uptime = grpc_server.get_uptime_seconds()
        assert uptime == 0.0
        
        # Test when started (mock)
        grpc_server._start_time = time.time() - 10  # 10 seconds ago
        uptime = grpc_server.get_uptime_seconds()
        assert uptime >= 9.0  # Allow for small timing differences
        assert uptime <= 11.0


class TestGrpcIntegration:
    """Test gRPC integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_server_client_configuration_compatibility(self):
        """Test that server and client configurations are compatible."""
        settings = get_settings()
        
        # Create server config from settings
        server_config = GrpcConfig.from_settings()
        
        # Create client config from server config
        client_config = GrpcClientConfig.from_server_config(server_config)
        
        # Verify compatibility
        assert client_config.host == server_config.host
        assert client_config.port == server_config.port
        assert client_config.secure == server_config.secure
    
    @pytest.mark.asyncio
    async def test_error_handling_in_client(self, grpc_client):
        """Test error handling in gRPC client."""
        # Mock connect to raise an exception
        grpc_client.connect = AsyncMock(side_effect=ConnectionError("Connection failed"))
        
        with pytest.raises(ConnectionError):
            await grpc_client.connect()
        
        assert grpc_client.is_connected() is False
