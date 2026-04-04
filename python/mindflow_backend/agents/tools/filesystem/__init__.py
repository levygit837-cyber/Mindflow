"""Filesystem tools for MindFlow agents."""

from __future__ import annotations

import warnings
from importlib import import_module

from .file_operations import FileEditTool, FileReadTool, FileWriteTool
from .operations import DirectoryCreateTool, DirectoryListTool, FileDeleteTool
from .search_tools import FileFinderTool, FindFilesTool, GlobSearchTool, GrepSearchTool

_COMPAT_EXPORTS = {
    "FileReadToolV3": (".file_operations_v3", "FileReadToolV3"),
    "FileWriteToolV3": (".file_write_v3", "FileWriteToolV3"),
    "FileEditToolV3": (".file_edit_v3", "FileEditToolV3"),
    "GrepToolV3": (".grep_v3", "GrepToolV3"),
    "GlobToolV3": (".glob_v3", "GlobToolV3"),
    "DirectoryListToolV3": (".directory_list_v3", "DirectoryListToolV3"),
    "DirectoryCreateToolV3": (".directory_create_v3", "DirectoryCreateToolV3"),
    "FileDeleteToolV3": (".file_delete_v3", "FileDeleteToolV3"),
    "FileFinderToolV3": (".file_finder_v3", "FileFinderToolV3"),
    "FindFilesToolV3": (".file_finder_v3", "FindFilesToolV3"),
    "FileReadToolV2": (".file_operations_v2", "FileReadToolV2"),
    "FileWriteToolV2": (".file_operations_v2", "FileWriteToolV2"),
    "FileEditToolV2": (".file_operations_v2", "FileEditToolV2"),
    "GlobToolV2": (".search_tools_v2", "GlobToolV2"),
    "GrepToolV2": (".search_tools_v2", "GrepToolV2"),
}

__all__ = [
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "DirectoryListTool",
    "DirectoryCreateTool",
    "FileDeleteTool",
    "GrepSearchTool",
    "GlobSearchTool",
    "FileFinderTool",
    "FindFilesTool",
]


def __getattr__(name: str):
    if name not in _COMPAT_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _COMPAT_EXPORTS[name]
    warnings.warn(
        (
            f"{__name__}.{name} is a deprecated compatibility export. "
            f"Import {attr_name} from {__name__}{module_name} instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value
