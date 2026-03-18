"""GitNexus CLI-backed code intelligence tools."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.code_schemas import (
    GITNEXUS_CONTEXT_SCHEMA,
    GITNEXUS_IMPACT_SCHEMA,
    GITNEXUS_QUERY_SCHEMA,
    GITNEXUS_STATUS_SCHEMA,
)

_logger = get_logger(__name__)

GITNEXUS_BINARY = "gitnexus"
DEFAULT_TIMEOUT_SECONDS = 90


def get_gitnexus_registry_path() -> Path:
    """Return the registry path used by the GitNexus CLI."""
    return Path.home() / ".gitnexus" / "registry.json"


def load_gitnexus_registry() -> list[dict[str, Any]]:
    """Load indexed repository metadata from the local GitNexus registry."""
    registry_path = get_gitnexus_registry_path()
    if not registry_path.exists():
        return []

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        repos = payload.get("repos", [])
        return [entry for entry in repos if isinstance(entry, dict)]
    return []


def parse_gitnexus_status_output(output: str) -> dict[str, Any]:
    """Parse `gitnexus status` output into a structured payload."""
    text = output.strip()
    result: dict[str, Any] = {
        "state": "unknown",
        "repository_path": None,
        "indexed_at": None,
        "indexed_commit": None,
        "current_commit": None,
        "status_line": None,
        "stale": False,
        "raw_output": text,
    }

    if not text:
        result["state"] = "empty_output"
        return result

    if "Not a git repository." in text:
        result["state"] = "not_git_repository"
        return result

    if "Repository not indexed." in text:
        result["state"] = "not_indexed"
        return result

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Repository:"):
            result["repository_path"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Indexed:"):
            result["indexed_at"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Indexed commit:"):
            result["indexed_commit"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Current commit:"):
            result["current_commit"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Status:"):
            status_line = stripped.split(":", 1)[1].strip()
            result["status_line"] = status_line
            lowered = status_line.lower()
            if "up-to-date" in lowered:
                result["state"] = "up_to_date"
                result["stale"] = False
            elif "stale" in lowered:
                result["state"] = "stale"
                result["stale"] = True

    if result["repository_path"] and result["state"] == "unknown":
        result["state"] = "indexed"

    return result


def resolve_gitnexus_repo_name(
    workspace_path: str | Path,
    repo_path: str | None = None,
    registry_entries: list[dict[str, Any]] | None = None,
) -> str | None:
    """Resolve the indexed GitNexus repository name for a workspace path."""
    entries = registry_entries if registry_entries is not None else load_gitnexus_registry()
    workspace = Path(workspace_path).expanduser().resolve()
    target = Path(repo_path).expanduser().resolve() if repo_path else workspace

    best_match: dict[str, Any] | None = None
    best_match_length = -1

    for entry in entries:
        entry_path_raw = entry.get("path")
        if not isinstance(entry_path_raw, str):
            continue
        try:
            entry_path = Path(entry_path_raw).expanduser().resolve()
        except OSError:
            continue

        if target == entry_path or target.is_relative_to(entry_path):
            match_length = len(str(entry_path))
            if match_length > best_match_length:
                best_match = entry
                best_match_length = match_length

    if best_match:
        name = best_match.get("name")
        if isinstance(name, str) and name.strip():
            return name

    return target.name if target.name else None


def run_gitnexus_subprocess(
    command: list[str],
    cwd: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Run a GitNexus CLI command and capture stdout/stderr."""
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _parse_gitnexus_json_output(*streams: str) -> Any:
    decoder = json.JSONDecoder()
    for stream in streams:
        candidate = (stream or "").strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        for index, char in enumerate(candidate):
            if char not in "[{":
                continue
            try:
                parsed, parsed_len = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue

            if candidate[index + parsed_len :].strip():
                continue
            return parsed

    raise ValueError("GitNexus did not return valid JSON output.")


class _GitNexusToolBase(AsyncToolInterface):
    tool_family = "gitnexus"
    category = "code_analysis"
    timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    def __init__(self) -> None:
        super().__init__()
        self.version = "1.0.0"

    def _resolve_workspace_path(self, workspace_path: str | None = None) -> Path:
        raw_path = workspace_path or self.root_dir or "."
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute() and self.root_dir:
            candidate = Path(self.root_dir) / candidate
        return candidate.resolve()

    def _build_repo_info(
        self,
        *,
        workspace: Path,
        status_payload: dict[str, Any],
    ) -> dict[str, Any]:
        repo_path = status_payload.get("repository_path")
        repo_name = resolve_gitnexus_repo_name(workspace, repo_path)
        identifier = repo_name or repo_path or str(workspace)
        return {
            "name": repo_name,
            "path": repo_path,
            "identifier": identifier,
        }

    def _result_payload(
        self,
        *,
        success: bool,
        result: Any = None,
        error: str | None = None,
        error_type: str | None = None,
        remediation: str | None = None,
        repo: dict[str, Any] | None = None,
        gitnexus_status: dict[str, Any] | None = None,
        command: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = self._format_result(success=success, result=result, error=error)
        if error_type:
            payload["error_type"] = error_type
        if remediation:
            payload["remediation"] = remediation
        if repo:
            payload["repo"] = repo
        if gitnexus_status:
            payload["gitnexus_status"] = gitnexus_status
        if command:
            payload["command"] = command
        return payload

    async def _run_status(self, workspace: Path) -> tuple[subprocess.CompletedProcess[str] | None, dict[str, Any]]:
        try:
            completed = await asyncio.to_thread(
                run_gitnexus_subprocess,
                [GITNEXUS_BINARY, "status"],
                workspace,
                self.timeout_seconds,
            )
        except FileNotFoundError:
            return None, {
                "state": "binary_missing",
                "stale": False,
                "raw_output": "",
            }
        except subprocess.TimeoutExpired as exc:
            return None, {
                "state": "timeout",
                "stale": False,
                "raw_output": str(exc),
            }

        combined_output = "\n".join(
            chunk for chunk in [completed.stdout, completed.stderr] if chunk
        )
        status_payload = parse_gitnexus_status_output(combined_output)
        return completed, status_payload

    async def _ensure_repo_ready(
        self,
        workspace: Path,
        *,
        allow_stale: bool = False,
    ) -> dict[str, Any]:
        completed, status_payload = await self._run_status(workspace)
        repo = self._build_repo_info(workspace=workspace, status_payload=status_payload)

        if status_payload["state"] == "binary_missing":
            return {
                "ok": False,
                "payload": self._result_payload(
                    success=False,
                    error="GitNexus CLI is not installed or is not available on PATH.",
                    error_type="binary_missing",
                    remediation="Install GitNexus and verify `gitnexus --help` works before retrying.",
                    repo=repo,
                    gitnexus_status=status_payload,
                ),
            }

        if status_payload["state"] == "timeout":
            return {
                "ok": False,
                "payload": self._result_payload(
                    success=False,
                    error="GitNexus status command timed out.",
                    error_type="timeout",
                    remediation=f"Retry from `{workspace}` and, if needed, run `gitnexus analyze` manually.",
                    repo=repo,
                    gitnexus_status=status_payload,
                ),
            }

        if status_payload["state"] == "not_git_repository":
            return {
                "ok": False,
                "payload": self._result_payload(
                    success=False,
                    error="GitNexus status failed because the workspace is not a git repository.",
                    error_type="not_git_repository",
                    remediation="Run the tool from a git repository root or provide `workspace_path` for a repository.",
                    repo=repo,
                    gitnexus_status=status_payload,
                ),
            }

        if status_payload["state"] == "not_indexed":
            return {
                "ok": False,
                "payload": self._result_payload(
                    success=False,
                    error="GitNexus has not indexed this repository yet.",
                    error_type="repo_not_indexed",
                    remediation=f"Run `gitnexus analyze` in `{workspace}` and retry the request.",
                    repo=repo,
                    gitnexus_status=status_payload,
                ),
            }

        if status_payload["stale"] and not allow_stale:
            return {
                "ok": False,
                "payload": self._result_payload(
                    success=False,
                    error="GitNexus index is stale for this repository.",
                    error_type="stale_index",
                    remediation=f"Run `gitnexus analyze` in `{workspace}` to refresh the index, then retry.",
                    repo=repo,
                    gitnexus_status=status_payload,
                ),
            }

        return {
            "ok": True,
            "repo": repo,
            "status": status_payload,
            "completed": completed,
        }

    async def _run_json_command(
        self,
        *,
        workspace: Path,
        command: list[str],
    ) -> dict[str, Any]:
        try:
            completed = await asyncio.to_thread(
                run_gitnexus_subprocess,
                command,
                workspace,
                self.timeout_seconds,
            )
        except FileNotFoundError:
            return self._result_payload(
                success=False,
                error="GitNexus CLI is not installed or is not available on PATH.",
                error_type="binary_missing",
                remediation="Install GitNexus and verify `gitnexus --help` works before retrying.",
                command=command,
            )
        except subprocess.TimeoutExpired as exc:
            return self._result_payload(
                success=False,
                error="GitNexus command timed out.",
                error_type="timeout",
                remediation=f"Retry the command or increase the timeout if the repository is very large. Details: {exc}",
                command=command,
            )

        combined_output = "\n".join(
            chunk for chunk in [completed.stderr, completed.stdout] if chunk
        ).strip()

        if completed.returncode != 0:
            return self._result_payload(
                success=False,
                error=combined_output or "GitNexus command failed.",
                error_type="command_failed",
                remediation="Check GitNexus status for this repo and rerun the command once the index is healthy.",
                command=command,
            )

        try:
            parsed_output = _parse_gitnexus_json_output(
                completed.stderr,
                completed.stdout,
                combined_output,
            )
        except ValueError:
            return self._result_payload(
                success=False,
                error="GitNexus returned a non-JSON response.",
                error_type="invalid_output",
                remediation="Retry the command. If the problem persists, run the CLI manually to inspect the raw output.",
                command=command,
            )

        return self._result_payload(
            success=True,
            result=parsed_output,
            command=command,
        )


class GitNexusStatusTool(_GitNexusToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "gitnexus_status"
        self.description = "Inspect GitNexus index status for the current workspace"
        self.notifier_kind = self.name
        self._schema = GITNEXUS_STATUS_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        workspace = self._resolve_workspace_path(kwargs.get("workspace_path"))
        status_result = await self._ensure_repo_ready(workspace, allow_stale=True)
        if not status_result["ok"]:
            return status_result["payload"]

        status_payload = status_result["status"]
        repo = status_result["repo"]
        remediation = None
        if status_payload["stale"]:
            remediation = f"Run `gitnexus analyze` in `{workspace}` to refresh the index before deeper analysis."

        return self._result_payload(
            success=True,
            result=status_payload,
            remediation=remediation,
            repo=repo,
            gitnexus_status=status_payload,
            command=[GITNEXUS_BINARY, "status"],
        )

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class GitNexusQueryTool(_GitNexusToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "gitnexus_query"
        self.description = "Search GitNexus execution flows related to a concept"
        self.notifier_kind = self.name
        self._schema = GITNEXUS_QUERY_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        workspace = self._resolve_workspace_path(kwargs.get("workspace_path"))
        prepared = await self._ensure_repo_ready(workspace)
        if not prepared["ok"]:
            return prepared["payload"]

        command = [
            GITNEXUS_BINARY,
            "query",
            "--repo",
            str(prepared["repo"]["identifier"]),
            "--limit",
            str(kwargs.get("limit", 5)),
        ]
        if kwargs.get("task_context"):
            command.extend(["--context", str(kwargs["task_context"])])
        if kwargs.get("goal"):
            command.extend(["--goal", str(kwargs["goal"])])
        if kwargs.get("include_content"):
            command.append("--content")
        command.append(str(kwargs["query"]))

        payload = await self._run_json_command(workspace=workspace, command=command)
        payload["repo"] = prepared["repo"]
        payload["gitnexus_status"] = prepared["status"]
        return payload

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class GitNexusContextTool(_GitNexusToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "gitnexus_context"
        self.description = "Get a 360-degree GitNexus view of a code symbol"
        self.notifier_kind = self.name
        self._schema = GITNEXUS_CONTEXT_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if not kwargs.get("name") and not kwargs.get("uid"):
            return self._result_payload(
                success=False,
                error="Either `name` or `uid` must be provided for gitnexus_context.",
                error_type="validation_error",
                remediation="Pass a symbol name or a GitNexus UID from a previous result.",
            )

        workspace = self._resolve_workspace_path(kwargs.get("workspace_path"))
        prepared = await self._ensure_repo_ready(workspace)
        if not prepared["ok"]:
            return prepared["payload"]

        command = [
            GITNEXUS_BINARY,
            "context",
            "--repo",
            str(prepared["repo"]["identifier"]),
        ]
        if kwargs.get("uid"):
            command.extend(["--uid", str(kwargs["uid"])])
        if kwargs.get("file_path"):
            command.extend(["--file", str(kwargs["file_path"])])
        if kwargs.get("include_content"):
            command.append("--content")
        if kwargs.get("name"):
            command.append(str(kwargs["name"]))

        payload = await self._run_json_command(workspace=workspace, command=command)
        payload["repo"] = prepared["repo"]
        payload["gitnexus_status"] = prepared["status"]
        return payload

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class GitNexusImpactTool(_GitNexusToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "gitnexus_impact"
        self.description = "Analyze GitNexus blast radius for a symbol or file"
        self.notifier_kind = self.name
        self._schema = GITNEXUS_IMPACT_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        workspace = self._resolve_workspace_path(kwargs.get("workspace_path"))
        prepared = await self._ensure_repo_ready(workspace)
        if not prepared["ok"]:
            return prepared["payload"]

        command = [
            GITNEXUS_BINARY,
            "impact",
            "--repo",
            str(prepared["repo"]["identifier"]),
            "--direction",
            str(kwargs.get("direction", "upstream")),
            "--depth",
            str(kwargs.get("depth", 3)),
        ]
        if kwargs.get("include_tests"):
            command.append("--include-tests")
        command.append(str(kwargs["target"]))

        payload = await self._run_json_command(workspace=workspace, command=command)
        payload["repo"] = prepared["repo"]
        payload["gitnexus_status"] = prepared["status"]
        return payload

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


__all__ = [
    "GitNexusStatusTool",
    "GitNexusQueryTool",
    "GitNexusContextTool",
    "GitNexusImpactTool",
    "get_gitnexus_registry_path",
    "load_gitnexus_registry",
    "parse_gitnexus_status_output",
    "resolve_gitnexus_repo_name",
    "run_gitnexus_subprocess",
]
