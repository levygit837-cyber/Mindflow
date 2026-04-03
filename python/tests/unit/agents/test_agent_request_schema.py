from pydantic import ValidationError

from mindflow_backend.schemas.agent import AgentChatRequest


def test_agent_request_accepts_agent_type_and_agent_alias() -> None:
    by_name = AgentChatRequest.model_validate({"message": "oi", "agent_type": "coder"})
    by_alias = AgentChatRequest.model_validate({"message": "oi", "agent": "coder"})

    assert by_name.agent_type == "coder"
    assert by_alias.agent_type == "coder"


def test_agent_request_normalizes_file_folder_path_to_parent_directory(tmp_path) -> None:
    target_file = tmp_path / "feature.py"
    target_file.write_text("print('ok')\n", encoding="utf-8")

    request = AgentChatRequest.model_validate(
        {"message": "analise esse arquivo", "folder_path": str(target_file)}
    )

    assert request.folder_path == str(tmp_path)


def test_agent_request_rejects_removed_codex_provider() -> None:
    try:
        AgentChatRequest.model_validate({"message": "oi", "provider": "codex"})
    except ValidationError as exc:
        assert "provider" in str(exc)
    else:
        raise AssertionError("AgentChatRequest should reject codex as a removed provider")


def test_agent_request_accepts_workspace_policy() -> None:
    request = AgentChatRequest.model_validate(
        {"message": "implemente", "workspace_policy": "worktree"}
    )

    assert request.workspace_policy.value == "worktree"
