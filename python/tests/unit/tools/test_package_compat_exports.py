import importlib

import pytest

import mindflow_backend.agents.tools.filesystem as filesystem_pkg
import mindflow_backend.agents.tools.planning as planning_pkg
import mindflow_backend.agents.tools.system as system_pkg
import mindflow_backend.agents.tools.web as web_pkg
from mindflow_backend.agents.tools.filesystem.file_operations_v2 import FileReadToolV2
from mindflow_backend.agents.tools.filesystem.file_operations_v3 import FileReadToolV3
from mindflow_backend.agents.tools.planning.todo_list_focus_v3 import (
    TodoListFocusToolV3,
)
from mindflow_backend.agents.tools.system.shell_executor_v2 import ShellExecutorToolV2
from mindflow_backend.agents.tools.web.http_client_v3 import HttpClientToolV3


def test_web_package_root_exposes_only_canonical_primary_exports() -> None:
    assert "HttpClientToolV3" not in web_pkg.__all__
    assert "WebScraperTool" in web_pkg.__all__


def test_filesystem_package_root_exposes_only_canonical_primary_exports() -> None:
    assert "FileReadToolV2" not in filesystem_pkg.__all__
    assert "FileReadToolV3" not in filesystem_pkg.__all__
    assert "FileReadTool" in filesystem_pkg.__all__


def test_planning_package_root_exposes_only_canonical_primary_exports() -> None:
    assert "TodoListReadToolV3" not in planning_pkg.__all__
    assert "ReadTodosTool" in planning_pkg.__all__


def test_system_package_root_exposes_only_canonical_primary_exports() -> None:
    assert "ShellExecutorToolV2" not in system_pkg.__all__
    assert "ShellExecutorTool" in system_pkg.__all__


def test_web_v3_package_export_is_lazy_and_deprecated() -> None:
    reloaded_web = importlib.reload(web_pkg)

    with pytest.warns(DeprecationWarning, match="deprecated compatibility export"):
        compat_tool = reloaded_web.HttpClientToolV3

    assert compat_tool is HttpClientToolV3


def test_filesystem_v2_package_export_is_lazy_and_deprecated() -> None:
    reloaded_filesystem = importlib.reload(filesystem_pkg)

    with pytest.warns(DeprecationWarning, match="deprecated compatibility export"):
        compat_tool = reloaded_filesystem.FileReadToolV2

    assert compat_tool is FileReadToolV2


def test_filesystem_v3_package_export_is_lazy_and_deprecated() -> None:
    reloaded_filesystem = importlib.reload(filesystem_pkg)

    with pytest.warns(DeprecationWarning, match="deprecated compatibility export"):
        compat_tool = reloaded_filesystem.FileReadToolV3

    assert compat_tool is FileReadToolV3


def test_planning_v3_package_export_is_lazy_and_deprecated() -> None:
    reloaded_planning = importlib.reload(planning_pkg)

    with pytest.warns(DeprecationWarning, match="deprecated compatibility export"):
        compat_tool = reloaded_planning.TodoListFocusToolV3

    assert compat_tool is TodoListFocusToolV3


def test_system_v2_package_export_is_lazy_and_deprecated() -> None:
    reloaded_system = importlib.reload(system_pkg)

    with pytest.warns(DeprecationWarning, match="deprecated compatibility export"):
        compat_tool = reloaded_system.ShellExecutorToolV2

    assert compat_tool is ShellExecutorToolV2
