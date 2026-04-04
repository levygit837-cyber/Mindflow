from unittest.mock import AsyncMock

import pytest

from mindflow_backend.agents.tools.callable import filesystem as callable_filesystem
from mindflow_backend.schemas.tools.context import ToolContext


def _make_fake_legacy_builder(calls: dict[str, object], payload: dict[str, object]):
    class _FakeTool:
        async def execute(self, **kwargs):
            calls["kwargs"] = kwargs
            return {"success": True, "result": payload}

    def _builder(tool_cls, context):
        calls["tool_cls"] = tool_cls.__name__
        calls["context"] = context
        return _FakeTool()

    return _builder


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("impl_name", "input_name", "tool_name", "input_kwargs", "payload", "expected_kwargs"),
    [
        (
            "file_read_impl",
            "FileReadInput",
            "FileReadTool",
            {
                "file_path": "sample.txt",
                "offset": 2,
                "limit": 5,
                "encoding": "utf-8",
                "include_line_numbers": True,
            },
            {"marker": "read"},
            {
                "file_path": "sample.txt",
                "offset": 2,
                "limit": 5,
                "encoding": "utf-8",
                "include_line_numbers": True,
            },
        ),
        (
            "directory_list_impl",
            "DirectoryListInput",
            "DirectoryListTool",
            {
                "directory_path": ".",
                "include_hidden": True,
                "include_size": True,
                "include_type": True,
                "max_items": 10,
            },
            {"marker": "list"},
            {
                "directory_path": ".",
                "include_hidden": True,
                "include_size": True,
                "include_type": True,
                "max_items": 10,
            },
        ),
        (
            "file_finder_impl",
            "FileFinderInput",
            "FileFinderTool",
            {
                "pattern": "*.py",
                "directory": ".",
                "recursive": False,
                "min_size": 1,
                "max_size": 20,
                "min_date": None,
                "max_date": None,
                "max_results": 7,
            },
            {"marker": "find"},
            {
                "pattern": "*.py",
                "directory": ".",
                "recursive": False,
                "min_size": 1,
                "max_size": 20,
                "min_date": None,
                "max_date": None,
                "max_results": 7,
            },
        ),
        (
            "grep_search_impl",
            "GrepSearchInput",
            "GrepSearchTool",
            {
                "pattern": "MindFlow",
                "directory": ".",
                "file_pattern": "*.py",
                "recursive": True,
                "case_sensitive": True,
                "max_results": 25,
                "include_line_numbers": False,
            },
            {"marker": "grep"},
            {
                "pattern": "MindFlow",
                "directory": ".",
                "file_pattern": "*.py",
                "recursive": True,
                "case_sensitive": True,
                "max_results": 25,
                "include_line_numbers": False,
            },
        ),
        (
            "glob_search_impl",
            "GlobSearchInput",
            "GlobSearchTool",
            {
                "pattern": "**/*.py",
                "directory": ".",
                "max_results": 25,
                "include_dirs": True,
                "absolute_paths": True,
            },
            {"marker": "glob"},
            {
                "pattern": "**/*.py",
                "directory": ".",
                "max_results": 25,
                "include_dirs": True,
                "absolute_paths": True,
            },
        ),
        (
            "file_write_impl",
            "FileWriteInput",
            "FileWriteTool",
            {
                "file_path": "created.txt",
                "content": "hello",
                "encoding": "utf-8",
                "create_dirs": True,
                "overwrite": False,
            },
            {"marker": "write"},
            {
                "file_path": "created.txt",
                "content": "hello",
                "encoding": "utf-8",
                "create_dirs": True,
                "overwrite": False,
            },
        ),
        (
            "file_edit_impl",
            "FileEditInput",
            "FileEditTool",
            {
                "file_path": "editable.txt",
                "old_string": "before",
                "new_string": "after",
                "count": -1,
                "encoding": "utf-8",
            },
            {"marker": "edit"},
            {
                "file_path": "editable.txt",
                "old_string": "before",
                "new_string": "after",
                "count": -1,
                "encoding": "utf-8",
            },
        ),
        (
            "file_delete_impl",
            "FileDeleteInput",
            "FileDeleteTool",
            {
                "file_path": "deleteme.txt",
                "confirm": True,
            },
            {"marker": "delete"},
            {
                "file_path": "deleteme.txt",
                "confirm": True,
            },
        ),
        (
            "directory_create_impl",
            "DirectoryCreateInput",
            "DirectoryCreateTool",
            {
                "directory_path": "new-dir",
                "parents": False,
                "exist_ok": False,
                "mode": 0o700,
            },
            {"marker": "mkdir"},
            {
                "directory_path": "new-dir",
                "parents": False,
                "exist_ok": False,
            },
        ),
    ],
)
async def test_callable_filesystem_impls_delegate_to_canonical_tools(
    monkeypatch,
    tmp_path,
    impl_name,
    input_name,
    tool_name,
    input_kwargs,
    payload,
    expected_kwargs,
) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        callable_filesystem,
        "build_legacy_tool",
        _make_fake_legacy_builder(calls, payload),
    )
    monkeypatch.setattr(
        callable_filesystem,
        "deny_if_permission_blocked",
        AsyncMock(return_value=None),
    )

    impl = getattr(callable_filesystem, impl_name)
    input_cls = getattr(callable_filesystem, input_name)

    sandbox_root = tmp_path / "workspace"
    sandbox_root.mkdir()
    (sandbox_root / "sample.txt").write_text("before\nbefore\n")
    (sandbox_root / "editable.txt").write_text("before\nbefore\n")
    (sandbox_root / "deleteme.txt").write_text("remove")

    context = ToolContext(root_dir=str(sandbox_root), metadata={})
    result = await impl(input_cls(**input_kwargs), context)

    assert calls["tool_cls"] == tool_name
    assert calls["kwargs"] == expected_kwargs
    assert result.success is True
    for key, value in payload.items():
        assert result.data[key] == value
