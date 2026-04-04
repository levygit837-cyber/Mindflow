import uuid
from mindflow_backend.schemas.a2a.task import A2AMessage, TextPart
from mindflow_backend.communication.a2a.task_adapter import TaskAdapter
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, Priority

def test_a2a_task_to_delegation_task():
    # Arrange
    a2a_msg = A2AMessage(
        role="user",
        context_id="session_123",
        target_agent="coder",
        parts=[
            TextPart(text="Fix the bug in main.py")
        ]
    )

    # Act
    del_task = TaskAdapter.a2a_task_to_delegation_task(a2a_msg)

    # Assert
    assert del_task.objective.strip() == "Fix the bug in main.py"
    assert del_task.agent == AgentType.CODER
    assert del_task.agent_id == "coder"
    assert getattr(del_task, "session_id", None) == "session_123"

def test_delegation_result_to_a2a_artifact():
    # Arrange
    del_result = DelegationResult(
        task_id=uuid.uuid4(),
        agent=AgentType.CODER,
        status="completed",
        key_findings="Bug fixed successfully.",
        full_output="Bug fixed successfully. Code committed.",
        confidence=0.95,
        tokens_consumed=150,
        files_analyzed=["main.py"]
    )

    # Act
    artifact = TaskAdapter.delegation_result_to_a2a_artifact(del_result)

    # Assert
    assert len(artifact.parts) == 2
    assert artifact.parts[0].type == "text"
    assert "Bug fixed successfully" in artifact.parts[0].text
    
    assert artifact.parts[1].type == "data"
    assert artifact.parts[1].data["confidence"] == 0.95
    assert artifact.parts[1].data["tokens_consumed"] == 150
    assert "main.py" in artifact.parts[1].data["files_analyzed"]
