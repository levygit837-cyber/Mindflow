import pytest
import uuid
from unittest.mock import patch, MagicMock
from mindflow_backend.schemas.orchestration.delegation import DelegationTask
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from mindflow_backend.communication.a2a.a2a_client import A2AClient

@pytest.mark.asyncio
async def test_a2a_client_call_external_agent():
    # Arrange
    task = DelegationTask(
        task_id=uuid.uuid4(),
        agent=AgentType.RESEARCHER,
        objective="Search internal DB for customer info",
    )
    target_url = "http://external-agent.local/a2a/tasks/send"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "parts": [
            {"type": "text", "text": "Customer John Doe found."},
            {"type": "data", "data": {"confidence": 0.99}}
        ]
    }
    mock_response.raise_for_status.return_value = None

    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def post(self, url, json):
            return mock_response

    with patch("httpx.AsyncClient", return_value=MockAsyncClient()):
        # Act
        result = await A2AClient.call_external_agent(task, target_url)

    # Assert
    assert result.status == "completed"
    assert result.agent == AgentType.RESEARCHER
    assert "Customer John Doe found." in result.key_findings
    assert "Customer John Doe found." in result.full_output
