from __future__ import annotations

from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.file_operations import (
    DirectoryListTool as CanonicalDirectoryListTool,
    FileReadTool,
    FileWriteTool,
)
from mindflow_backend.agents.tools.filesystem.search_tools import (
    FileFinderTool,
    GlobSearchTool,
)
from mindflow_backend.agents.tools.filesystem import directory_create_v3
from mindflow_backend.agents.tools.filesystem import directory_list_v3
from mindflow_backend.agents.tools.filesystem import file_delete_v3
from mindflow_backend.agents.tools.filesystem import file_edit_v3
from mindflow_backend.agents.tools.filesystem import file_finder_v3
from mindflow_backend.agents.tools.filesystem import file_operations_v3
from mindflow_backend.agents.tools.filesystem import file_write_v3
from mindflow_backend.agents.tools.filesystem import glob_v3
from mindflow_backend.agents.tools.filesystem import grep_v3
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.mark.asyncio
async def test_canonical_file_read_supports_pagination_and_line_numbers(tmp_path) -> None:
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\n")

    tool = FileReadTool()
    tool.root_dir = str(tmp_path)

    result = await tool.execute(
        file_path=str(test_file),
        offset=1,
        limit=2,
        include_line_numbers=True,
    )

    assert result["success"] is True
    data = result["result"]
    assert data["lines_read"] == 2
    assert data["has_more"] is True
    assert "2\tLine 2" in data["content"]
    assert "3\tLine 3" in data["content"]


@pytest.mark.asyncio
async def test_canonical_file_write_supports_overwrite_flag(tmp_path) -> None:
    test_file = tmp_path / "existing.txt"
    test_file.write_text("original")

    tool = FileWriteTool()
    tool.root_dir = str(tmp_path)

    result = await tool.execute(
        file_path=str(test_file),
        content="new",
        overwrite=False,
    )

    assert result["success"] is False
    assert "overwrite" in (result["error"] or "").lower()


@pytest.mark.asyncio
async def test_canonical_directory_list_supports_v3_style_entries(tmp_path) -> None:
    (tmp_path / "visible.txt").write_text("visible")
    (tmp_path / ".hidden.txt").write_text("hidden")
    (tmp_path / "subdir").mkdir()

    tool = CanonicalDirectoryListTool()
    tool.root_dir = str(tmp_path)

    result = await tool.execute(
        directory_path=str(tmp_path),
        include_hidden=False,
        include_size=True,
        include_type=True,
        max_items=2,
    )

    assert result["success"] is True
    data = result["result"]
    assert data["total_count"] == 2
    assert data["truncated"] is True
    assert len(data["entries"]) == 2
    assert all("type" in entry for entry in data["entries"])


@pytest.mark.asyncio
async def test_canonical_file_finder_supports_recursive_flag_and_truncation(tmp_path) -> None:
    (tmp_path / "root.txt").write_text("root")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "deep.txt").write_text("deep")

    tool = FileFinderTool()

    non_recursive = await tool.execute(
        pattern="*.txt",
        directory=str(tmp_path),
        recursive=False,
    )
    assert non_recursive["success"] is True
    assert non_recursive["result"]["total_count"] == 1

    truncated = await tool.execute(
        pattern="*.txt",
        directory=str(tmp_path),
        recursive=True,
        max_results=1,
    )
    assert truncated["success"] is True
    assert truncated["result"]["truncated"] is True


@pytest.mark.asyncio
async def test_canonical_glob_supports_directory_and_path_options(tmp_path) -> None:
    (tmp_path / "file.txt").write_text("content")
    (tmp_path / "folder").mkdir()

    tool = GlobSearchTool()
    result = await tool.execute(
        pattern="*",
        directory=str(tmp_path),
        include_dirs=True,
        absolute_paths=True,
    )

    assert result["success"] is True
    data = result["result"]
    assert data["total_files"] == 1
    assert data["total_directories"] == 1
    assert data["files"][0].startswith("/")


def _make_fake_tool(calls: dict[str, object], payload: dict[str, object]):
    class _FakeTool:
        def __init__(self) -> None:
            self.root_dir = None
            self.sandbox_mode = None

        async def execute(self, **kwargs):
            calls["kwargs"] = kwargs
            calls["root_dir"] = self.root_dir
            return {
                "success": True,
                "result": payload,
                "error": None,
            }

    return _FakeTool


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "input_kwargs", "tool_attr", "payload", "expected_keys"),
    [
        (
            file_operations_v3,
            {"file_path": "sample.txt"},
            "FileReadTool",
            {"content": "hello", "lines_read": 1},
            {"content": "hello", "lines_read": 1},
        ),
        (
            file_write_v3,
            {"file_path": "sample.txt", "content": "hello"},
            "FileWriteTool",
            {"file_path": "/tmp/sample.txt", "bytes_written": 5},
            {"file_path": "/tmp/sample.txt", "bytes_written": 5},
        ),
        (
            file_edit_v3,
            {"file_path": "sample.txt", "old_string": "a", "new_string": "b"},
            "FileEditTool",
            {"replacements_made": 1},
            {"replacements_made": 1},
        ),
        (
            directory_list_v3,
            {"directory_path": "."},
            "DirectoryListTool",
            {"entries": [], "total_count": 0},
            {"entries": [], "total_count": 0},
        ),
        (
            file_finder_v3,
            {"pattern": "*.py", "directory": "."},
            "FileFinderTool",
            {"files": [], "total_count": 0},
            {"files": [], "total_count": 0},
        ),
        (
            grep_v3,
            {"pattern": "foo", "directory": "."},
            "GrepSearchTool",
            {"matches": [], "total_matches": 0},
            {"matches": [], "total_matches": 0},
        ),
        (
            glob_v3,
            {"pattern": "*.py", "directory": "."},
            "GlobSearchTool",
            {"files": [], "total_files": 0},
            {"files": [], "total_files": 0},
        ),
        (
            file_delete_v3,
            {"file_path": "sample.txt"},
            "FileDeleteTool",
            {"deleted": True, "file_path": "/tmp/sample.txt"},
            {"deleted": True, "file_path": "/tmp/sample.txt"},
        ),
        (
            directory_create_v3,
            {"directory_path": "newdir"},
            "DirectoryCreateTool",
            {"created": True, "directory_path": "/tmp/newdir"},
            {"created": True, "directory_path": "/tmp/newdir"},
        ),
    ],
)
async def test_v3_modules_delegate_to_canonical_tools(
    monkeypatch,
    module,
    input_kwargs,
    tool_attr,
    payload,
    expected_keys,
) -> None:
    calls: dict[str, object] = {}
    fake_tool = _make_fake_tool(calls, payload)
    monkeypatch.setattr(module, tool_attr, fake_tool, raising=False)
    tool_context = ToolContext(metadata={})

    input_cls = next(
        value
        for name, value in vars(module).items()
        if name.endswith("Input")
    )
    execute_fn = next(
        value
        for name, value in vars(module).items()
        if name.endswith("_execute")
    )

    result = await execute_fn(input_cls(**input_kwargs), tool_context)

    for key, value in input_kwargs.items():
        assert calls["kwargs"][key] == value
    for key, value in expected_keys.items():
        assert result[key] == value
