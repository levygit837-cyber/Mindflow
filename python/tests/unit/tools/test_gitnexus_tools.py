from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.code.gitnexus import (
    GitNexusQueryTool,
    parse_gitnexus_status_output,
    resolve_gitnexus_repo_name,
)


def test_parse_gitnexus_status_output_marks_stale() -> None:
    output = """
Repository: /tmp/MindFlow
Indexed: 2026-03-15T20:23:31.864Z
Indexed commit: abc123
Current commit: def456
Status: ⚠️ stale (re-run gitnexus analyze)
"""
    parsed = parse_gitnexus_status_output(output)

    assert parsed["repository_path"] == "/tmp/MindFlow"
    assert parsed["indexed_commit"] == "abc123"
    assert parsed["current_commit"] == "def456"
    assert parsed["state"] == "stale"
    assert parsed["stale"] is True


def test_resolve_gitnexus_repo_name_prefers_matching_repo_path(tmp_path: Path) -> None:
    repo_path = tmp_path / "MindFlow"
    nested_path = repo_path / "python" / "mindflow_backend"
    nested_path.mkdir(parents=True)

    registry_entries = [
        {"name": "OtherRepo", "path": str(tmp_path / "other")},
        {"name": "MindFlow", "path": str(repo_path)},
    ]

    assert resolve_gitnexus_repo_name(
        nested_path,
        repo_path=str(repo_path),
        registry_entries=registry_entries,
    ) == "MindFlow"


@pytest.mark.asyncio
async def test_gitnexus_query_tool_builds_repo_command_and_parses_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "MindFlow"
    repo_path.mkdir()
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "mindflow_backend.agents.tools.code.gitnexus.load_gitnexus_registry",
        lambda: [{"name": "MindFlow", "path": str(repo_path)}],
    )

    def fake_run(command: list[str], cwd: Path, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command == ["gitnexus", "status"]:
            stdout = "\n".join(
                [
                    f"Repository: {repo_path}",
                    "Indexed: 2026-03-15T20:23:31.864Z",
                    "Indexed commit: abc123",
                    "Current commit: abc123",
                    "Status: ✅ up-to-date",
                ]
            )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        return subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr='{"processes":[],"process_symbols":[],"definitions":[]}',
        )

    monkeypatch.setattr(
        "mindflow_backend.agents.tools.code.gitnexus.run_gitnexus_subprocess",
        fake_run,
    )

    tool = GitNexusQueryTool()
    tool.root_dir = str(repo_path)

    result = await tool.execute(
        query="authentication flow",
        task_context="debugging login",
        goal="find entrypoint",
        limit=2,
        include_content=True,
    )

    assert result["success"] is True
    assert result["repo"]["name"] == "MindFlow"
    assert result["result"] == {"processes": [], "process_symbols": [], "definitions": []}
    assert commands[1] == [
        "gitnexus",
        "query",
        "--repo",
        "MindFlow",
        "--limit",
        "2",
        "--context",
        "debugging login",
        "--goal",
        "find entrypoint",
        "--content",
        "authentication flow",
    ]


@pytest.mark.asyncio
async def test_gitnexus_query_tool_returns_stale_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "MindFlow"
    repo_path.mkdir()

    def fake_run(command: list[str], cwd: Path, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        assert command == ["gitnexus", "status"]
        stdout = "\n".join(
            [
                f"Repository: {repo_path}",
                "Indexed: 2026-03-15T20:23:31.864Z",
                "Indexed commit: abc123",
                "Current commit: def456",
                "Status: ⚠️ stale (re-run gitnexus analyze)",
            ]
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(
        "mindflow_backend.agents.tools.code.gitnexus.run_gitnexus_subprocess",
        fake_run,
    )

    tool = GitNexusQueryTool()
    tool.root_dir = str(repo_path)
    result = await tool.execute(query="auth")

    assert result["success"] is False
    assert result["error_type"] == "stale_index"
    assert "gitnexus analyze" in result["remediation"]


@pytest.mark.asyncio
async def test_gitnexus_query_tool_reports_binary_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "MindFlow"
    repo_path.mkdir()

    def fake_run(command: list[str], cwd: Path, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("gitnexus")

    monkeypatch.setattr(
        "mindflow_backend.agents.tools.code.gitnexus.run_gitnexus_subprocess",
        fake_run,
    )

    tool = GitNexusQueryTool()
    tool.root_dir = str(repo_path)
    result = await tool.execute(query="auth")

    assert result["success"] is False
    assert result["error_type"] == "binary_missing"
    assert "PATH" in result["error"]
