"""Integration tests for tools v2 with registry and LangChain adapter.

Tests the complete integration of tools v2 with the MindFlow system:
- Registry loading
- LangChain adapter conversion
- Tool execution through adapter
- Backward compatibility
"""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
from mindflow_backend.agents.tools.filesystem.file_operations_v2 import (
    FileEditToolV2,
    FileReadToolV2,
    FileWriteToolV2,
)
from mindflow_backend.agents.tools.filesystem.search_tools_v2 import (
    GlobToolV2,
    GrepToolV2,
)
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.agents.tools.system.shell_executor_v2 import ShellExecutorToolV2
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode


class TestToolsV2RegistryIntegration:
    """Test tools v2 integration with registry."""

    @pytest.fixture
    def sandbox(self, tmp_path):
        """Create test sandbox."""
        return MindFlowSandbox(
            root_dir=str(tmp_path),
            mode=SandboxMode.FULL
        )

    @pytest.fixture
    def registry(self, sandbox):
        """Create test registry."""
        return create_default_registry(sandbox)

    def test_registry_loads_v2_tools(self, registry):
        """Test that registry loads callable filesystem tools by default."""
        from mindflow_backend.schemas.orchestration.orchestrator import ToolScope
        from mindflow_backend.schemas.tools import CallableTool

        # Get filesystem tools
        tools = registry._get_tools_for_scope(ToolScope.FILESYSTEM)

        # Check that callable tools are loaded for the public scope surface
        tool_names = [tool.name for tool in tools]

        assert "file_read" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "grep_search" in tool_names
        assert "glob_search" in tool_names

        read_tool = next(t for t in tools if t.name == "file_read")
        assert isinstance(read_tool, CallableTool)

    def test_registry_loads_canonical_shell(self, registry):
        """Test that registry exposes the canonical shell through callable scope tools."""
        from mindflow_backend.schemas.orchestration.orchestrator import ToolScope
        from mindflow_backend.schemas.tools import CallableTool

        # Get shell tools
        tools = registry._get_tools_for_scope(ToolScope.SHELL)

        # Check that the callable shell surface is loaded
        tool_names = [tool.name for tool in tools]
        assert "shell_execute" in tool_names

        shell_tool = next(t for t in tools if t.name == "shell_execute")
        assert isinstance(shell_tool, CallableTool)

    def test_backward_compatibility_v1_tools_available(self, registry):
        """Test that legacy filesystem tools remain available as fallback compatibility."""

        tools = registry._get_filesystem_tools()

        tool_names = [tool.name for tool in tools]

        assert "read_file_v2" in tool_names
        assert "write_file_v2" in tool_names
        assert "edit_file_v2" in tool_names
        assert "grep_v2" in tool_names
        assert "glob_v2" in tool_names
        assert "file_finder" in tool_names


class TestToolsV2LangChainAdapter:
    """Test LangChain adapter with tools v2."""

    @pytest.fixture
    def v2_tools(self, tmp_path):
        """Create v2 tool instances."""
        return [
            FileReadToolV2(root_dir=str(tmp_path)),
            FileWriteToolV2(root_dir=str(tmp_path)),
            FileEditToolV2(root_dir=str(tmp_path)),
            GrepToolV2(root_dir=str(tmp_path)),
            GlobToolV2(root_dir=str(tmp_path)),
        ]

    def test_adapter_converts_v2_tools(self, v2_tools):
        """Test that adapter successfully converts v2 tools."""
        lc_tools = to_langchain_tools(v2_tools)

        assert len(lc_tools) == 5

        # Check tool names
        tool_names = [tool.name for tool in lc_tools]
        assert "read_file_v2" in tool_names
        assert "write_file_v2" in tool_names
        assert "edit_file_v2" in tool_names
        assert "grep_v2" in tool_names
        assert "glob_v2" in tool_names

    def test_adapter_preserves_v2_schemas(self, v2_tools):
        """Test that adapter preserves v2 parameter schemas."""
        lc_tools = to_langchain_tools(v2_tools)

        # Get read_file tool
        read_tool = next(t for t in lc_tools if t.name == "read_file_v2")

        # Check that v2 parameters are present in schema
        if hasattr(read_tool, 'args_schema') and read_tool.args_schema:
            schema = read_tool.args_schema.model_json_schema()
            properties = schema.get('properties', {})

            # v2 specific parameters
            assert 'offset' in properties
            assert 'limit' in properties
            assert 'include_line_numbers' in properties
            assert 'encoding' in properties

    @pytest.mark.asyncio
    async def test_adapter_tool_execution(self, v2_tools, tmp_path):
        """Test that adapted tools can be executed."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\n")

        lc_tools = to_langchain_tools(v2_tools)

        # Get read_file tool
        read_tool = next(t for t in lc_tools if t.name == "read_file_v2")

        # Execute tool
        result = await read_tool.ainvoke({"file_path": str(test_file)})

        # Parse result (it's JSON string)
        import json
        result_dict = json.loads(result)

        assert result_dict["success"] is True
        assert "Hello World" in result_dict["content"]


class TestToolsV2Features:
    """Test v2 specific features."""

    @pytest.fixture
    def tmp_workspace(self, tmp_path):
        """Create temporary workspace."""
        return tmp_path

    @pytest.mark.asyncio
    async def test_file_read_v2_pagination(self, tmp_workspace):
        """Test FileReadToolV2 pagination feature."""
        # Create test file with multiple lines
        test_file = tmp_workspace / "large.txt"
        test_file.write_text("\n".join([f"Line {i}" for i in range(1, 101)]))

        tool = FileReadToolV2(root_dir=str(tmp_workspace))

        # Read with pagination
        result = await tool.execute(
            file_path=str(test_file),
            offset=10,
            limit=5
        )

        assert result["success"] is True
        assert result["lines_returned"] == 5
        assert result["offset"] == 10
        assert "Line 11" in result["content"]

    @pytest.mark.asyncio
    async def test_file_write_v2_atomic(self, tmp_workspace):
        """Test FileWriteToolV2 atomic write feature."""
        test_file = tmp_workspace / "atomic.txt"

        tool = FileWriteToolV2(root_dir=str(tmp_workspace))

        # Write with atomic flag
        result = await tool.execute(
            file_path=str(test_file),
            content="Atomic content",
            atomic=True
        )

        assert result["success"] is True
        assert result["atomic"] is True
        assert test_file.read_text() == "Atomic content"

    @pytest.mark.asyncio
    async def test_file_edit_v2_dry_run(self, tmp_workspace):
        """Test FileEditToolV2 dry run feature."""
        test_file = tmp_workspace / "edit.txt"
        original_content = "Hello World"
        test_file.write_text(original_content)

        tool = FileEditToolV2(root_dir=str(tmp_workspace))

        # Dry run edit
        result = await tool.execute(
            file_path=str(test_file),
            old_string="World",
            new_string="Universe",
            dry_run=True
        )

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "preview" in result

        # File should not be modified
        assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_glob_v2_exclude_patterns(self, tmp_workspace):
        """Test GlobToolV2 exclude patterns feature."""
        # Create test files
        (tmp_workspace / "include.py").write_text("include")
        (tmp_workspace / "exclude.py").write_text("exclude")
        (tmp_workspace / "test.py").write_text("test")

        tool = GlobToolV2(root_dir=str(tmp_workspace))

        # Search with exclude patterns
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_workspace),
            exclude_patterns=["exclude.py", "test.py"]
        )

        assert result["success"] is True
        assert result["total_matches"] == 1
        assert any("include.py" in m for m in result["matches"])

    @pytest.mark.asyncio
    async def test_grep_v2_context_lines(self, tmp_workspace):
        """Test GrepToolV2 context lines feature."""
        test_file = tmp_workspace / "context.txt"
        test_file.write_text("Line 1\nLine 2\nMatch here\nLine 4\nLine 5\n")

        tool = GrepToolV2(root_dir=str(tmp_workspace))

        # Search with context
        result = await tool.execute(
            pattern="Match",
            path=str(test_file),
            context_before=1,
            context_after=1
        )

        assert result["success"] is True
        context = result["results"][0]["context"]
        assert "Line 2" in context
        assert "Match here" in context
        assert "Line 4" in context

    @pytest.mark.asyncio
    async def test_shell_v2_semantic_analysis(self, tmp_workspace):
        """Test ShellExecutorToolV2 semantic analysis."""
        tool = ShellExecutorToolV2(root_dir=str(tmp_workspace))

        # Execute git command
        result = await tool.execute(command="git status")

        assert "semantic_type" in result
        assert result["semantic_type"] == "git"

    @pytest.mark.asyncio
    async def test_shell_v2_security_classification(self, tmp_workspace):
        """Test ShellExecutorToolV2 security classification."""
        tool = ShellExecutorToolV2(root_dir=str(tmp_workspace))

        # Execute safe command
        result = await tool.execute(command="echo 'Hello'")

        assert "security_level" in result
        assert result["security_level"] == "safe"


class TestIntegrationFeatures:
    """Test integration features (git, history, analytics, caching)."""

    @pytest.mark.asyncio
    async def test_git_integration_diff(self, tmp_path):
        """Test git integration diff generation."""
        from mindflow_backend.agents.tools.integrations import fetch_single_file_git_diff

        # This test requires a git repository
        # Skip if not in git repo
        result = await fetch_single_file_git_diff(
            str(tmp_path / "test.txt"),
            str(tmp_path)
        )

        # Should fail gracefully if not a git repo
        assert "success" in result

    def test_file_history_tracking(self, tmp_path):
        """Test file history tracking."""
        from mindflow_backend.agents.tools.integrations import track_file_edit

        test_file = tmp_path / "history.txt"
        test_file.write_text("Original content")

        # Track edit
        result = track_file_edit(
            str(test_file),
            operation="edit",
            metadata={"user": "test"}
        )

        assert result["success"] is True
        assert "snapshot_id" in result

    def test_analytics_tracking(self):
        """Test analytics tracking."""
        from mindflow_backend.agents.tools.analytics import get_tool_stats, log_file_operation

        # Log operation
        log_file_operation(
            tool_name="read_file",
            operation="read",
            file_path="/test/file.txt",
            success=True,
            duration=0.5
        )

        # Get stats
        stats = get_tool_stats("read_file")

        assert stats["total_executions"] >= 1

    def test_result_caching(self):
        """Test result caching."""
        from mindflow_backend.agents.tools.caching import clear_global_cache, get_global_cache

        cache = get_global_cache()

        # Clear cache first
        clear_global_cache()

        # Set value
        cache.set("test_key", {"result": "test"}, ttl=60)

        # Get value
        value = cache.get("test_key")

        assert value is not None
        assert value["result"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
