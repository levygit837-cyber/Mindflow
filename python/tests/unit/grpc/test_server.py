"""Test gRPC server functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.grpc.server import (
    EnhancedGrpcAgentServer,
    GrpcAgentServer,
    get_grpc_server,
    get_server,
    start_grpc_server,
    stop_grpc_server,
)

# ── Task 1: public compatibility surface ──────────────────────────────────────


def test_server_legacy_aliases_are_exported():
    """GrpcAgentServer and get_grpc_server must be exported for back-compat."""
    assert GrpcAgentServer is EnhancedGrpcAgentServer
    assert callable(get_grpc_server)


# ── Task 2: server bootstrap ──────────────────────────────────────────────────


def test_connection_pool_manager_receives_config():
    """GrpcConnectionPoolManager must be instantiated (with PoolManagerConfig)."""
    with patch("mindflow_backend.grpc.server.GrpcConnectionPoolManager") as mock_pool:
        GrpcAgentServer()
    mock_pool.assert_called_once()


@pytest.mark.asyncio
async def test_server_passes_interceptors_to_grpc_factory():
    """grpc.aio.server() must receive interceptors=... at creation time."""
    server = GrpcAgentServer()
    mock_grpc_server = MagicMock()
    mock_grpc_server.start = AsyncMock()

    with patch("grpc.aio.server", return_value=mock_grpc_server) as factory, \
         patch.object(server, "_start_monitoring", AsyncMock()), \
         patch.object(server, "_setup_services", AsyncMock()), \
         patch.object(server, "_configure_port", AsyncMock()):
        await server.start()

    _, kwargs = factory.call_args
    assert "interceptors" in kwargs
    assert isinstance(kwargs["interceptors"], list)


@pytest.mark.asyncio
async def test_build_server_interceptors_returns_list():
    """_build_server_interceptors() must return a non-empty list."""
    server = GrpcAgentServer()
    interceptors = server._build_server_interceptors()
    assert isinstance(interceptors, list)
    assert len(interceptors) >= 1


# ── Existing tests (updated to work with GrpcAgentServer alias) ───────────────


class TestGrpcAgentServer:
    """Test the enhanced gRPC server implementation."""

    def test_server_initialization(self):
        server = GrpcAgentServer()
        assert server.get_host() == "0.0.0.0"
        assert server.get_port() == 50051
        assert server.is_running() is False
        assert server._server is None
        assert server._start_time is None

    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        server = GrpcAgentServer()

        mock_grpc_server = MagicMock()
        mock_grpc_server.start = AsyncMock()
        mock_grpc_server.stop = AsyncMock()
        mock_grpc_server.wait_for_termination = AsyncMock()

        with patch("grpc.aio.server", return_value=mock_grpc_server), \
             patch.object(server, "_setup_services", AsyncMock()), \
             patch.object(server, "_configure_port", AsyncMock()), \
             patch.object(server, "_start_monitoring", AsyncMock()):
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
        server = GrpcAgentServer()
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        server._running = True

        await server.start()
        mock_grpc_server.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_server_stop_not_running(self):
        server = GrpcAgentServer()
        await server.stop()
        assert server.is_running() is False

    @pytest.mark.asyncio
    async def test_server_wait_for_termination(self):
        server = GrpcAgentServer()
        mock_grpc_server = MagicMock()
        mock_grpc_server.wait_for_termination = AsyncMock()
        server._server = mock_grpc_server
        await server.wait_for_termination()
        mock_grpc_server.wait_for_termination.assert_called_once()

    def test_add_interceptor_pre_server(self):
        """add_interceptor() must not raise when called before start()."""
        server = GrpcAgentServer()
        mock_interceptor = MagicMock()
        server.add_interceptor(mock_interceptor)
        assert server._server is None

    def test_add_interceptor_with_server(self):
        """add_interceptor() delegates to the underlying grpc server when available."""
        server = GrpcAgentServer()
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        mock_interceptor = MagicMock()
        server.add_interceptor(mock_interceptor)
        mock_grpc_server.add_interceptor.assert_called_once_with(mock_interceptor)

    @pytest.mark.asyncio
    async def test_setup_services(self):
        server = GrpcAgentServer()
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server

        with patch("mindflow_backend.grpc.server.AgentRuntimeServiceImpl"), \
             patch("mindflow_backend.grpc.generated.mindflow_backend_pb2_grpc"
                   ".add_AgentRuntimeServiceServicer_to_server") as mock_add:
            await server._setup_services()
            mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_configure_port_insecure(self):
        server = GrpcAgentServer()
        server.config.secure = False
        mock_grpc_server = MagicMock()
        server._server = mock_grpc_server
        await server._configure_port()
        mock_grpc_server.add_insecure_port.assert_called_once_with(
            f"{server._host}:{server._port}"
        )

    def test_get_uptime_seconds_not_started(self):
        server = GrpcAgentServer()
        assert server.get_uptime_seconds() == 0.0

    def test_get_uptime_seconds_started(self):
        import time
        server = GrpcAgentServer()
        server._start_time = time.time() - 10
        uptime = server.get_uptime_seconds()
        assert 9.0 <= uptime <= 11.0


class TestServerManagement:
    """Test server management functions."""

    @pytest.mark.asyncio
    async def test_get_server_singleton(self):
        import mindflow_backend.grpc.server
        mindflow_backend.grpc.server._server_instance = None

        s1 = await get_server()
        s2 = await get_server()
        assert s1 is s2

    @pytest.mark.asyncio
    async def test_get_grpc_server_awaitable(self):
        import mindflow_backend.grpc.server
        mindflow_backend.grpc.server._server_instance = None

        server = await get_grpc_server()
        assert isinstance(server, EnhancedGrpcAgentServer)

    @pytest.mark.asyncio
    async def test_start_grpc_server(self):
        import mindflow_backend.grpc.server
        mindflow_backend.grpc.server._server_instance = None

        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.start = AsyncMock()

        with patch("mindflow_backend.grpc.server.get_server", AsyncMock(return_value=mock_server)):
            result = await start_grpc_server()
            assert result is mock_server
            mock_server.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_grpc_server(self):
        import mindflow_backend.grpc.server
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        mock_server.stop = AsyncMock()
        mindflow_backend.grpc.server._server_instance = mock_server

        await stop_grpc_server()
        mock_server.stop.assert_called_once()
        assert mindflow_backend.grpc.server._server_instance is None

    @pytest.mark.asyncio
    async def test_stop_grpc_server_not_running(self):
        import mindflow_backend.grpc.server
        mindflow_backend.grpc.server._server_instance = None
        await stop_grpc_server()
        assert mindflow_backend.grpc.server._server_instance is None
