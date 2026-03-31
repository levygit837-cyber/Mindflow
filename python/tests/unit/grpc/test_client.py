"""Test gRPC client functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.grpc.client import GrpcAgentClient, LocalAgentClient
from mindflow_backend.grpc.config.config import GrpcClientConfig
from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta

# ── Task 1: public compatibility surface ──────────────────────────────────────


def test_client_config_from_settings():
    """GrpcClientConfig.from_settings() must map settings fields."""
    from mindflow_backend.infra.config import get_settings
    settings = get_settings()
    config = GrpcClientConfig.from_settings(settings)
    assert config.host == settings.grpc_host
    assert config.port == settings.grpc_port


def test_client_compat_kwargs_max_attempts():
    """Passing max_attempts= as compat kwarg must override config."""
    client = GrpcAgentClient(max_attempts=7)
    assert client.config.max_attempts == 7


def test_client_compat_kwargs_timeout_seconds():
    """Passing timeout_seconds= must override request_timeout_seconds."""
    client = GrpcAgentClient(timeout_seconds=42)
    assert client.config.request_timeout_seconds == 42


# ── Task 3: channel + stub flow ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_client_builds_channel_with_interceptors():
    """connect() must call grpc.aio.insecure_channel() and create stub."""
    client = GrpcAgentClient(max_attempts=1, timeout_seconds=5)
    mock_channel = MagicMock()
    mock_channel.channel_ready = AsyncMock()

    with patch("grpc.aio.insecure_channel", return_value=mock_channel) as channel_factory, \
         patch("mindflow_backend.grpc.client.pb2_grpc") as mock_pb2_grpc:
        mock_pb2_grpc.AgentRuntimeServiceStub.return_value = MagicMock()
        await client.connect()

    mock_pb2_grpc.AgentRuntimeServiceStub.assert_called_once_with(mock_channel)
    channel_factory.assert_called_once()


@pytest.mark.asyncio
async def test_client_awaits_aio_channel_ready():
    """_test_connection() must await channel.channel_ready()."""
    client = GrpcAgentClient(max_attempts=1, timeout_seconds=5)
    mock_channel = MagicMock()
    mock_channel.channel_ready = AsyncMock()
    client._channel = mock_channel

    await client._test_connection()

    mock_channel.channel_ready.assert_awaited_once()


# ── Existing tests (updated for grpc.aio API) ─────────────────────────────────


class TestGrpcAgentClient:
    """Test the real gRPC client implementation."""

    @pytest.mark.asyncio
    async def test_stream_chat_success(self):
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=5)

        mock_channel = MagicMock()
        mock_channel.channel_ready = AsyncMock()
        mock_stub = MagicMock()
        mock_call = AsyncMock()

        mock_response = MagicMock()
        mock_response.id = "test-event-1"
        mock_response.seq = 1
        mock_response.type = "response"
        mock_response.mode = "messages"
        mock_response.data = "Test response"
        mock_response.json_meta = '{"runId": "test-run"}'

        mock_call.__aiter__ = AsyncMock(return_value=iter([mock_response]))
        mock_stub.StreamChat.return_value = mock_call

        with patch("grpc.aio.insecure_channel", return_value=mock_channel), \
             patch("mindflow_backend.grpc.client.pb2_grpc") as mock_pb2_grpc, \
             patch("mindflow_backend.grpc.client.pb2") as mock_pb2:
            mock_pb2_grpc.AgentRuntimeServiceStub.return_value = mock_stub

            await client.connect()

            events = []
            async for event in client.stream_chat(
                session_id="test-session",
                message="Hello",
                provider="openai",
                model="gpt-4",
            ):
                events.append(event)

        assert len(events) == 1
        assert isinstance(events[0], StreamEvent)
        assert events[0].id == "test-event-1"
        assert events[0].data == "Test response"

        await client.close()

    @pytest.mark.asyncio
    async def test_stream_chat_connection_error(self):
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=1)

        with patch("grpc.aio.insecure_channel", side_effect=Exception("Connection failed")):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=5)
        mock_channel = MagicMock()
        mock_channel.channel_ready = AsyncMock()

        with patch("grpc.aio.insecure_channel", return_value=mock_channel), \
             patch("mindflow_backend.grpc.client.pb2_grpc") as mock_pb2_grpc:
            mock_pb2_grpc.AgentRuntimeServiceStub.return_value = MagicMock()
            await client.connect()

            result = await client.health_check()

        assert isinstance(result, dict)
        assert result["status"] == "healthy"
        assert result["host"] == client.host
        assert result["port"] == str(client.port)
        assert result["connected"] == "true"

        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=1)

        with patch("grpc.aio.insecure_channel", side_effect=Exception("Connection failed")):
            result = await client.health_check()

        assert isinstance(result, dict)
        assert result["status"] == "unhealthy"
        assert "error" in result

    def test_parse_metadata_success(self):
        client = GrpcAgentClient()
        json_meta = '{"runId": "test-run", "node": "test-node"}'
        result = client._parse_metadata(json_meta)
        assert isinstance(result, dict)
        assert result["runId"] == "test-run"
        assert result["node"] == "test-node"

    def test_parse_metadata_failure(self):
        client = GrpcAgentClient()
        assert client._parse_metadata('{"invalid": json}') is None
        assert client._parse_metadata('') is None
        assert client._parse_metadata(None) is None


class TestLocalAgentClient:
    """Test the fallback local client."""

    @pytest.mark.asyncio
    async def test_local_client_stream_chat(self):
        client = LocalAgentClient()

        mock_event = StreamEvent(
            id="local-event-1",
            seq=1,
            type="response",
            mode="messages",
            data="Local response",
            meta=StreamEventMeta(runId="local-run"),
        )

        async def _fake_stream(*_a, **_kw):
            yield mock_event

        client._service.runtime.stream_chat = _fake_stream

        events = []
        async for event in client.stream_chat(
            session_id="test-session",
            message="Hello",
            provider="openai",
            model="gpt-4",
        ):
            events.append(event)

        assert len(events) == 1
        assert isinstance(events[0], StreamEvent)
        assert events[0].id == "local-event-1"
        assert events[0].data == "Local response"

    def test_local_client_attributes(self):
        client = LocalAgentClient()
        assert hasattr(client, "_service")
        assert hasattr(client, "agent")
        assert client.agent is client._service
