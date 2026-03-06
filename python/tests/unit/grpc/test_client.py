"""Test gRPC client functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from omnimind_backend.grpc.client import GrpcAgentClient, LocalAgentClient
from omnimind_backend.schemas.chat.agent import StreamEvent, StreamEventMeta
from omnimind_backend.schemas.core.common import LLMProvider


class TestGrpcAgentClient:
    """Test the real gRPC client implementation."""
    
    @pytest.mark.asyncio
    async def test_stream_chat_success(self):
        """Test successful stream chat call."""
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=5)
        
        # Mock the gRPC components
        mock_channel = MagicMock()
        mock_stub = MagicMock()
        mock_call = AsyncMock()
        
        # Mock protobuf response
        mock_response = MagicMock()
        mock_response.id = "test-event-1"
        mock_response.seq = 1
        mock_response.type = "response"
        mock_response.mode = "messages"
        mock_response.data = "Test response"
        mock_response.json_meta = '{"runId": "test-run"}'
        
        # Setup mocks
        mock_call.__aiter__ = AsyncMock(return_value=iter([mock_response]))
        mock_stub.StreamChat.return_value = mock_call
        
        with patch('grpc.aio.insecure_channel', return_value=mock_channel), \
             patch('grpc.channel_ready_future'), \
             patch('omnimind_backend.grpc.client.pb2_grpc.AgentRuntimeServiceStub', return_value=mock_stub), \
             patch('omnimind_backend.grpc.client.pb2.ChatStreamRequest'):
            
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
        """Test stream chat with connection error."""
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=1)
        
        with patch('grpc.aio.insecure_channel', side_effect=Exception("Connection failed")):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client.connect()
    
    @pytest.mark.asyncio
    async def test_stream_chat_grpc_error(self):
        """Test stream chat with gRPC streaming error."""
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=5)
        
        # Mock the gRPC components
        mock_channel = MagicMock()
        mock_stub = MagicMock()
        mock_call = AsyncMock()
        
        # Mock gRPC error
        import grpc
        mock_call.__aiter__ = AsyncMock(side_effect=grpc.RpcError("Stream failed"))
        mock_stub.StreamChat.return_value = mock_call
        
        with patch('grpc.aio.insecure_channel', return_value=mock_channel), \
             patch('grpc.channel_ready_future'), \
             patch('omnimind_backend.grpc.client.pb2_grpc.AgentRuntimeServiceStub', return_value=mock_stub), \
             patch('omnimind_backend.grpc.client.pb2.ChatStreamRequest'):
            
            await client.connect()
            
            with pytest.raises(ConnectionError, match="gRPC streaming error"):
                events = []
                async for event in client.stream_chat(
                    session_id="test-session",
                    message="Hello",
                ):
                    events.append(event)
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=5)
        
        # Mock the gRPC components
        mock_channel = MagicMock()
        
        with patch('grpc.aio.insecure_channel', return_value=mock_channel), \
             patch('grpc.channel_ready_future'):
            
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
        """Test health check when connection fails."""
        client = GrpcAgentClient(max_attempts=1, timeout_seconds=1)
        
        with patch('grpc.aio.insecure_channel', side_effect=Exception("Connection failed")):
            result = await client.health_check()
            
            assert isinstance(result, dict)
            assert result["status"] == "unhealthy"
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test connection retry logic."""
        client = GrpcAgentClient(max_attempts=3, timeout_seconds=1)
        
        call_count = 0
        def mock_channel(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return MagicMock()
        
        with patch('grpc.aio.insecure_channel', side_effect=mock_channel), \
             patch('grpc.channel_ready_future'), \
             patch('omnimind_backend.grpc.client.pb2_grpc.AgentRuntimeServiceStub'), \
             patch('omnimind_backend.grpc.client.pb2.ChatStreamRequest'):
            
            await client.connect()
            assert client.is_connected() is True
            assert call_count == 3  # Should retry 3 times
            
            await client.close()
    
    def test_parse_metadata_success(self):
        """Test successful metadata parsing."""
        client = GrpcAgentClient()
        
        json_meta = '{"runId": "test-run", "node": "test-node"}'
        result = client._parse_metadata(json_meta)
        
        assert isinstance(result, dict)
        assert result["runId"] == "test-run"
        assert result["node"] == "test-node"
    
    def test_parse_metadata_failure(self):
        """Test metadata parsing with invalid JSON."""
        client = GrpcAgentClient()
        
        # Invalid JSON
        result = client._parse_metadata('{"invalid": json}')
        assert result is None
        
        # Empty string
        result = client._parse_metadata('')
        assert result is None
        
        # None
        result = client._parse_metadata(None)
        assert result is None


class TestLocalAgentClient:
    """Test the fallback local client."""
    
    @pytest.mark.asyncio
    async def test_local_client_stream_chat(self):
        """Test local client stream chat functionality."""
        client = LocalAgentClient()
        
        # Mock the service implementation
        mock_event = StreamEvent(
            id="local-event-1",
            seq=1,
            type="response",
            mode="messages",
            data="Local response",
            meta=StreamEventMeta(runId="local-run"),
        )
        
        client._service.runtime.stream_chat = AsyncMock(return_value=iter([mock_event]))
        
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
        """Test local client has expected attributes."""
        client = LocalAgentClient()
        
        assert hasattr(client, '_service')
        assert hasattr(client, 'agent')
        assert client.agent is client._service
