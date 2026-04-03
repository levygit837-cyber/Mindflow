"""Workspace isolation service for session and execution runtimes."""

from __future__ import annotations

import inspect
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import (
    WorkspaceBinding,
    WorkspaceKind,
    WorkspacePolicy,
)

_logger = get_logger(__name__)

_COPY_EXCLUDES = (
    ".git",
    "node_modules",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _slug(value: str, *, fallback: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    compact = "-".join(part for part in cleaned.split("-") if part)
    return compact[:64] or fallback


def _short_id(value: str, *, fallback: str) -> str:
    compact = "".join(char.lower() for char in value if char.isalnum())
    return (compact[:8] or fallback).lower()


class WorktreeService:
    """Resolve and persist the effective workspace used by a runtime."""

    def __init__(
        self,
        *,
        session_runtime_state_service: Any | None = None,
        cache_root: str | Path | None = None,
    ) -> None:
        self._session_runtime_state_service = session_runtime_state_service
        self._cache_root = Path(cache_root or Path.home() / ".cache" / "mindflow" / "workspaces").expanduser()

    async def ensure_workspace(
        self,
        *,
        session_id: str,
        requested_root: str | Path | None,
        policy: WorkspacePolicy | str | None,
        needs_isolation: bool,
        execution_id: str | None = None,
        force_fallback_copy: bool = False,
    ) -> WorkspaceBinding:
        requested_path = self._resolve_requested_root(requested_root)
        resolved_policy = self._resolve_policy(policy, needs_isolation)

        existing = await self.load_workspace_binding(session_id, execution_id=execution_id)
        if self._binding_matches(existing, requested_path=requested_path, resolved_policy=resolved_policy):
            return existing

        git_context = None if force_fallback_copy else self._detect_git_context(requested_path)
        if resolved_policy == WorkspacePolicy.SHARED:
            binding = self._build_shared_binding(
                session_id=session_id,
                execution_id=execution_id,
                requested_path=requested_path,
                git_context=git_context,
                policy=resolved_policy,
            )
        elif git_context is not None:
            binding = self._create_git_worktree_binding(
                session_id=session_id,
                execution_id=execution_id,
                requested_path=requested_path,
                git_context=git_context,
                policy=resolved_policy,
            )
        else:
            binding = self._create_isolated_copy_binding(
                session_id=session_id,
                execution_id=execution_id,
                requested_path=requested_path,
                policy=resolved_policy,
            )

        await self._persist_binding(session_id, binding, execution_id=execution_id)
        if binding.workspace_kind != WorkspaceKind.SHARED:
            await self._emit_worktree_hook("create", session_id=session_id, worktree_path=binding.workspace_root)
        return binding

    async def load_workspace_binding(
        self,
        session_id: str,
        *,
        execution_id: str | None = None,
    ) -> WorkspaceBinding | None:
        service = self._get_session_runtime_state_service()
        if service is None:
            return None

        snapshot = await self._call_service(service, "load_session_state", session_id)
        if not isinstance(snapshot, dict):
            return None

        workspace_state = snapshot.get("workspace")
        if not isinstance(workspace_state, dict):
            return None

        payload: dict[str, Any] | None = None
        if execution_id:
            executions = workspace_state.get("executions")
            if isinstance(executions, dict):
                candidate = executions.get(execution_id)
                if isinstance(candidate, dict):
                    payload = candidate

        if payload is None:
            candidate = workspace_state.get("session")
            if isinstance(candidate, dict):
                payload = candidate

        if payload is None:
            return None

        try:
            binding = WorkspaceBinding.model_validate(payload)
        except Exception as exc:
            _logger.warning("workspace_binding_restore_failed", session_id=session_id, error=str(exc))
            return None

        return binding if self._binding_exists(binding) else None

    async def remove_workspace(
        self,
        binding: WorkspaceBinding,
        *,
        session_id: str,
    ) -> None:
        if binding.workspace_kind == WorkspaceKind.SHARED:
            return

        workspace_root = Path(binding.workspace_root)
        checkout_root = Path(binding.checkout_root)
        try:
            if binding.workspace_kind == WorkspaceKind.GIT_WORKTREE and binding.repo_root:
                subprocess.run(
                    ["git", "-C", binding.repo_root, "worktree", "remove", "--force", binding.checkout_root],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if binding.branch_name:
                    subprocess.run(
                        ["git", "-C", binding.repo_root, "branch", "-D", binding.branch_name],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
            if checkout_root.exists():
                shutil.rmtree(checkout_root, ignore_errors=True)
            if workspace_root.exists() and workspace_root != checkout_root:
                shutil.rmtree(workspace_root, ignore_errors=True)
        finally:
            await self._emit_worktree_hook("remove", session_id=session_id, worktree_path=binding.workspace_root)

    def _resolve_requested_root(self, requested_root: str | Path | None) -> Path:
        candidate = Path(requested_root or Path.cwd()).expanduser()
        if candidate.exists() and candidate.is_file():
            candidate = candidate.parent
        resolved = candidate.resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"Workspace root does not exist or is not a directory: {resolved}")
        return resolved

    def _resolve_policy(
        self,
        policy: WorkspacePolicy | str | None,
        needs_isolation: bool,
    ) -> WorkspacePolicy:
        if isinstance(policy, WorkspacePolicy):
            requested = policy
        else:
            try:
                requested = WorkspacePolicy(str(policy or WorkspacePolicy.AUTO))
            except ValueError:
                requested = WorkspacePolicy.AUTO

        if requested == WorkspacePolicy.AUTO:
            return WorkspacePolicy.WORKTREE if needs_isolation else WorkspacePolicy.SHARED
        return requested

    def _binding_matches(
        self,
        binding: WorkspaceBinding | None,
        *,
        requested_path: Path,
        resolved_policy: WorkspacePolicy,
    ) -> bool:
        if binding is None or not self._binding_exists(binding):
            return False
        if binding.requested_root != str(requested_path):
            return False
        if resolved_policy == WorkspacePolicy.SHARED:
            return binding.workspace_kind == WorkspaceKind.SHARED
        return binding.workspace_kind in {WorkspaceKind.GIT_WORKTREE, WorkspaceKind.ISOLATED_COPY}

    def _binding_exists(self, binding: WorkspaceBinding) -> bool:
        return Path(binding.workspace_root).exists() and Path(binding.workspace_path).exists()

    def _build_shared_binding(
        self,
        *,
        session_id: str,
        execution_id: str | None,
        requested_path: Path,
        git_context: dict[str, Any] | None,
        policy: WorkspacePolicy,
    ) -> WorkspaceBinding:
        now = _utc_now()
        return WorkspaceBinding(
            session_id=session_id,
            execution_id=execution_id,
            requested_root=str(requested_path),
            workspace_root=str(requested_path),
            workspace_path=str(requested_path),
            checkout_root=str(requested_path),
            workspace_kind=WorkspaceKind.SHARED,
            policy=policy,
            repo_root=git_context["repo_root"] if git_context else None,
            branch_name=git_context["branch_name"] if git_context else None,
            head_sha=git_context["head_sha"] if git_context else None,
            created_at=now,
            updated_at=now,
        )

    def _create_git_worktree_binding(
        self,
        *,
        session_id: str,
        execution_id: str | None,
        requested_path: Path,
        git_context: dict[str, Any],
        policy: WorkspacePolicy,
    ) -> WorkspaceBinding:
        repo_root = Path(git_context["repo_root"])
        relative_path = git_context["relative_path"]
        checkout_root = self._workspace_directory(requested_path, session_id, execution_id) / "checkout"
        checkout_root.parent.mkdir(parents=True, exist_ok=True)

        if checkout_root.exists():
            existing_toplevel = self._git_rev_parse(checkout_root, "--show-toplevel")
            if existing_toplevel is None:
                shutil.rmtree(checkout_root, ignore_errors=True)

        branch_name = self._branch_name(session_id, execution_id)
        if not checkout_root.exists():
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "worktree",
                    "add",
                    "--force",
                    "-B",
                    branch_name,
                    str(checkout_root),
                    git_context["head_sha"],
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        workspace_path = checkout_root / relative_path if relative_path != Path(".") else checkout_root
        now = _utc_now()
        return WorkspaceBinding(
            session_id=session_id,
            execution_id=execution_id,
            requested_root=str(requested_path),
            workspace_root=str(checkout_root),
            workspace_path=str(workspace_path),
            checkout_root=str(checkout_root),
            workspace_kind=WorkspaceKind.GIT_WORKTREE,
            policy=policy,
            repo_root=str(repo_root),
            branch_name=branch_name,
            head_sha=git_context["head_sha"],
            created_at=now,
            updated_at=now,
        )

    def _create_isolated_copy_binding(
        self,
        *,
        session_id: str,
        execution_id: str | None,
        requested_path: Path,
        policy: WorkspacePolicy,
    ) -> WorkspaceBinding:
        workspace_root = self._workspace_directory(requested_path, session_id, execution_id) / "copy"
        if workspace_root.exists():
            shutil.rmtree(workspace_root, ignore_errors=True)
        workspace_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            requested_path,
            workspace_root,
            symlinks=False,
            ignore=shutil.ignore_patterns(*_COPY_EXCLUDES),
        )

        now = _utc_now()
        return WorkspaceBinding(
            session_id=session_id,
            execution_id=execution_id,
            requested_root=str(requested_path),
            workspace_root=str(workspace_root),
            workspace_path=str(workspace_root),
            checkout_root=str(workspace_root),
            workspace_kind=WorkspaceKind.ISOLATED_COPY,
            policy=policy,
            created_at=now,
            updated_at=now,
        )

    def _workspace_directory(
        self,
        requested_path: Path,
        session_id: str,
        execution_id: str | None,
    ) -> Path:
        project_slug = _slug(requested_path.name or "workspace", fallback="workspace")
        scope_id = _short_id(execution_id or session_id, fallback="runtime")
        scope_label = "exec" if execution_id else "session"
        return self._cache_root / project_slug / f"{scope_label}-{scope_id}"

    def _branch_name(self, session_id: str, execution_id: str | None) -> str:
        session_token = _short_id(session_id, fallback="session")
        if execution_id:
            return f"mindflow/s-{session_token}-e-{_short_id(execution_id, fallback='exec')}"
        return f"mindflow/s-{session_token}"

    def _detect_git_context(self, requested_path: Path) -> dict[str, Any] | None:
        repo_root_raw = self._git_rev_parse(requested_path, "--show-toplevel")
        if repo_root_raw is None:
            return None

        repo_root = Path(repo_root_raw).resolve()
        try:
            relative_path = requested_path.relative_to(repo_root)
        except ValueError:
            relative_path = Path(".")

        return {
            "repo_root": str(repo_root),
            "relative_path": relative_path if relative_path.parts else Path("."),
            "head_sha": self._git_rev_parse(repo_root, "HEAD"),
            "branch_name": self._git_current_branch(repo_root),
        }

    def _git_current_branch(self, repo_root: Path) -> str | None:
        branch = self._run_git(["branch", "--show-current"], cwd=repo_root)
        normalized = branch.strip() if branch else ""
        return normalized or None

    def _git_rev_parse(self, cwd: Path, argument: str) -> str | None:
        output = self._run_git(["rev-parse", argument], cwd=cwd)
        normalized = output.strip() if output else ""
        return normalized or None

    def _run_git(self, args: list[str], *, cwd: Path) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(cwd), *args],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception:
            return None
        return completed.stdout

    def _get_session_runtime_state_service(self) -> Any | None:
        if self._session_runtime_state_service is not None:
            return self._session_runtime_state_service

        try:
            from mindflow_backend.services.core import get_session_runtime_state_service

            self._session_runtime_state_service = get_session_runtime_state_service()
        except Exception as exc:
            _logger.warning("workspace_runtime_state_service_unavailable", error=str(exc))
            self._session_runtime_state_service = None
        return self._session_runtime_state_service

    async def _persist_binding(
        self,
        session_id: str,
        binding: WorkspaceBinding,
        *,
        execution_id: str | None,
    ) -> None:
        service = self._get_session_runtime_state_service()
        if service is None:
            return

        payload = binding.model_dump(mode="json")
        state = (
            {"workspace": {"executions": {execution_id: payload}}}
            if execution_id
            else {"workspace": {"session": payload}}
        )
        await self._call_service(service, "save_session_state", session_id, state)

    async def _call_service(self, service: Any, method_name: str, *args: Any) -> Any:
        method = getattr(service, method_name, None)
        if method is None:
            return None
        result = method(*args)
        if inspect.isawaitable(result):
            return await result
        return result

    async def _emit_worktree_hook(self, action: str, *, session_id: str, worktree_path: str) -> None:
        hook_event_name = "WORKTREE_CREATE" if action == "create" else "WORKTREE_REMOVE"
        try:
            from mindflow_backend.hooks.context import HookContext
            from mindflow_backend.hooks.manager import HookManager
            from mindflow_backend.hooks.types import HookEvent

            event = getattr(HookEvent, hook_event_name)
            context = HookContext(
                hook_event_name=event.value,
                session_id=session_id,
                cwd=worktree_path,
                worktree_path=worktree_path,
            )
            async for _ in HookManager.get_instance().execute(
                event,
                context,
                session_id=session_id,
            ):
                pass
        except Exception as exc:
            _logger.warning(
                "workspace_hook_execution_failed",
                session_id=session_id,
                action=action,
                error=str(exc),
            )


__all__ = ["WorktreeService"]
