import pytest
import json
from typing import AsyncGenerator
from mindflow_backend.communication.a2a.stream_adapter import A2AStreamAdapter
from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta

@pytest.mark.asyncio
async def test_a2a_stream_adapter_mapping():
    """Verify that MindFlow StreamEvents are correctly mapped to A2A SSE events."""
    
    async def mock_mf_stream() -> AsyncGenerator[StreamEvent, None]:
        yield StreamEvent(
            id="1", seq=1, type="agent_step", mode="updates", data="Initializing"
        )
        yield StreamEvent(
            id="2", seq=2, type="thought", mode="updates", data="Reasoning..."
        )
        yield StreamEvent(
            id="3", seq=3, type="response", mode="updates", data="Hello "
        )
        yield StreamEvent(
            id="4", seq=4, type="response", mode="updates", data="World"
        )
        yield StreamEvent(
            id="5", seq=5, type="done", mode="updates", data=""
        )

    adapter = A2AStreamAdapter()
    results = []
    async for sse_event in adapter.adapt_stream(mock_mf_stream()):
        results.append(sse_event)

    assert len(results) == 5
    
    # Check first event (agent_step -> TaskStatusUpdateEvent)
    assert "event: TaskStatusUpdateEvent" in results[0]
    assert '"status":"working"' in results[0]
    assert '"message":"Initializing"' in results[0]
    
    # Check second event (thought -> TaskStatusUpdateEvent)
    assert "event: TaskStatusUpdateEvent" in results[1]
    assert '"message":"Analyzing or using tools..."' in results[1]
    
    # Check third event (response -> TaskArtifactUpdateEvent)
    assert "event: TaskArtifactUpdateEvent" in results[2]
    assert '"text":"Hello "' in results[2]
    
    # Check final event (done -> TaskStatusUpdateEvent completed)
    assert "event: TaskStatusUpdateEvent" in results[4]
    assert '"status":"completed"' in results[4]

@pytest.mark.asyncio
async def test_a2a_stream_adapter_error_handling():
    """Verify that errors in the stream are handled by the adapter."""
    
    async def mock_error_stream() -> AsyncGenerator[StreamEvent, None]:
        yield StreamEvent(
            id="1", seq=1, type="error", mode="updates", data="Model timeout"
        )

    adapter = A2AStreamAdapter()
    results = []
    async for sse_event in adapter.adapt_stream(mock_error_stream()):
        results.append(sse_event)

    assert len(results) == 1
    assert "event: TaskStatusUpdateEvent" in results[0]
    assert '"status":"failed"' in results[0]
    assert '"error":"Model timeout"' in results[0]
