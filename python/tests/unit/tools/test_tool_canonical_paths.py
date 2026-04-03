from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from mindflow_backend.agents.tools import _DefaultRegistry
from mindflow_backend.agents.tools.ai.model_tools import LocalModelTool
from mindflow_backend.agents.tools.data.data_tools import CSVProcessorTool
from mindflow_backend.agents.tools.filesystem.file_operations import FileReadTool
from mindflow_backend.agents.tools.filesystem.operations import DirectoryListTool
from mindflow_backend.agents.tools.filesystem.search_tools import GrepSearchTool
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.agents.tools.search_web import search_web
from mindflow_backend.agents.tools.system.resource_monitor import ResourceMonitorTool
from mindflow_backend.agents.tools.system.sandbox import SandboxTool
from mindflow_backend.agents.tools.system.shell_executor import ShellExecutorTool
from mindflow_backend.agents.tools.system.system_info import SystemInfoTool


def _load_module(relative_path: str, module_name: str):
    root = Path(__file__).resolve().parents[3]
    module_path = root / relative_path
    spec = spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_specialist_modules_reexport_canonical_tool_classes() -> None:
    specialist_ai = _load_module(
        "mindflow_backend/agents/tools/specialist/common/ai/model_tools.py",
        "specialist_common_ai_model_tools",
    )
    specialist_data = _load_module(
        "mindflow_backend/agents/tools/specialist/common/data/data_tools.py",
        "specialist_common_data_data_tools",
    )
    specialist_filesystem = _load_module(
        "mindflow_backend/agents/tools/specialist/coder/filesystem/search_tools.py",
        "specialist_coder_filesystem_search_tools",
    )

    assert specialist_ai.LocalModelTool is LocalModelTool
    assert specialist_data.CSVProcessorTool is CSVProcessorTool
    assert specialist_filesystem.GrepSearchTool is GrepSearchTool


def test_specialist_search_module_reexports_canonical_function() -> None:
    specialist_search = _load_module(
        "mindflow_backend/agents/tools/specialist/research/search_web.py",
        "specialist_research_search_web",
    )

    specialist_search_web = specialist_search.search_web
    assert specialist_search_web is search_web


def test_specialist_filesystem_and_system_modules_reexport_canonical_symbols() -> None:
    specialist_coder_sandbox = _load_module(
        "mindflow_backend/agents/tools/specialist/coder/sandbox.py",
        "specialist_coder_sandbox",
    )
    specialist_coder_file_ops = _load_module(
        "mindflow_backend/agents/tools/specialist/coder/filesystem/file_operations.py",
        "specialist_coder_filesystem_file_operations",
    )
    specialist_coder_ops = _load_module(
        "mindflow_backend/agents/tools/specialist/coder/filesystem/operations.py",
        "specialist_coder_filesystem_operations",
    )
    specialist_shell = _load_module(
        "mindflow_backend/agents/tools/specialist/common/system/shell_executor.py",
        "specialist_common_system_shell_executor",
    )
    specialist_resource = _load_module(
        "mindflow_backend/agents/tools/specialist/common/system/resource_monitor.py",
        "specialist_common_system_resource_monitor",
    )
    specialist_system_info = _load_module(
        "mindflow_backend/agents/tools/specialist/common/system/system_info.py",
        "specialist_common_system_system_info",
    )
    specialist_sandbox = _load_module(
        "mindflow_backend/agents/tools/specialist/common/system/sandbox.py",
        "specialist_common_system_sandbox",
    )

    assert specialist_coder_sandbox.MindFlowSandbox is MindFlowSandbox
    assert specialist_coder_file_ops.FileReadTool is FileReadTool
    assert specialist_coder_ops.DirectoryListTool is DirectoryListTool
    assert specialist_shell.ShellExecutorTool is ShellExecutorTool
    assert specialist_resource.ResourceMonitorTool is ResourceMonitorTool
    assert specialist_system_info.SystemInfoTool is SystemInfoTool
    assert specialist_system_info.SystemInfoCollector is SystemInfoTool
    assert specialist_sandbox.SandboxTool is SandboxTool


def test_shell_registry_returns_shell_tools() -> None:
    from mindflow_backend.agents.tools.system.shell_executor_v2 import ShellExecutorToolV2

    registry = _DefaultRegistry(MindFlowSandbox(root_dir="."))
    shell_tools = registry._get_shell_tools()

    assert shell_tools
    assert any(isinstance(tool, ShellExecutorToolV2) for tool in shell_tools)
