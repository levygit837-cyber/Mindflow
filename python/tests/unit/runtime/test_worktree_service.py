from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


class _FakeRuntimeStateService:
    def __init__(self) -> None:
        self.saved: dict[str, dict] = {}

    async def save_session_state(self, session_id: str, state: dict) -> dict:
        current = self.saved.get(session_id, {})
        merged = {**current, **state}
        if "workspace" in current and "workspace" in state:
            merged["workspace"] = {
                **current["workspace"],
                **state["workspace"],
            }
        self.saved[session_id] = merged
        return merged

    async def load_session_state(self, session_id: str) -> dict | None:
        return self.saved.get(session_id)


def _init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "mindflow@example.com"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "MindFlow Tests"], cwd=repo_root, check=True, capture_output=True)
    (repo_root / "README.md").write_text("# repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_root, check=True, capture_output=True)


@pytest.mark.asyncio
async def test_worktree_service_returns_shared_binding_when_isolation_not_needed(tmp_path: Path) -> None:
    from mindflow_backend.schemas.orchestration.orchestrator import WorkspaceKind, WorkspacePolicy
    from mindflow_backend.services.core.worktree_service import WorktreeService

    runtime_state = _FakeRuntimeStateService()
    service = WorktreeService(
        session_runtime_state_service=runtime_state,
        cache_root=tmp_path / ".cache",
    )

    binding = await service.ensure_workspace(
        session_id="sess-shared",
        requested_root=str(tmp_path),
        policy=WorkspacePolicy.AUTO,
        needs_isolation=False,
    )

    assert binding.workspace_kind == WorkspaceKind.SHARED
    assert binding.workspace_root == str(tmp_path)
    assert binding.workspace_path == str(tmp_path)
    assert runtime_state.saved["sess-shared"]["workspace"]["session"]["workspace_kind"] == "shared"


@pytest.mark.asyncio
async def test_worktree_service_creates_git_worktree_for_isolated_workspace(tmp_path: Path) -> None:
    from mindflow_backend.schemas.orchestration.orchestrator import WorkspaceKind, WorkspacePolicy
    from mindflow_backend.services.core.worktree_service import WorktreeService

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    runtime_state = _FakeRuntimeStateService()
    service = WorktreeService(
        session_runtime_state_service=runtime_state,
        cache_root=tmp_path / ".cache",
    )

    binding = await service.ensure_workspace(
        session_id="sess-git",
        requested_root=str(repo_root),
        policy=WorkspacePolicy.WORKTREE,
        needs_isolation=True,
    )

    assert binding.workspace_kind == WorkspaceKind.GIT_WORKTREE
    assert Path(binding.checkout_root).exists()
    assert Path(binding.workspace_root).exists()
    assert binding.branch_name.startswith("mindflow/s-")
    resolved_root = subprocess.run(
        ["git", "-C", binding.checkout_root, "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert resolved_root == binding.checkout_root


@pytest.mark.asyncio
async def test_worktree_service_falls_back_to_isolated_copy_outside_git(tmp_path: Path) -> None:
    from mindflow_backend.schemas.orchestration.orchestrator import WorkspaceKind, WorkspacePolicy
    from mindflow_backend.services.core.worktree_service import WorktreeService

    project_root = tmp_path / "plain-project"
    project_root.mkdir()
    (project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (project_root / ".git").mkdir()
    (project_root / ".git" / "ignored").write_text("nope\n", encoding="utf-8")

    runtime_state = _FakeRuntimeStateService()
    service = WorktreeService(
        session_runtime_state_service=runtime_state,
        cache_root=tmp_path / ".cache",
    )

    binding = await service.ensure_workspace(
        session_id="sess-copy",
        requested_root=str(project_root),
        policy=WorkspacePolicy.WORKTREE,
        needs_isolation=True,
        force_fallback_copy=True,
    )

    assert binding.workspace_kind == WorkspaceKind.ISOLATED_COPY
    assert Path(binding.workspace_root, "app.py").exists()
    assert not Path(binding.workspace_root, ".git").exists()
