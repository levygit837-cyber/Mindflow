"""Live integration tests — LLM tool usage verification.

These tests make **real LLM calls** (Vertex AI / Gemini by default) and verify
that:
1. Tools are correctly converted to LangChain format.
2. The LLM actually *calls* the tools (tool_calls present in response).
3. The tool invocation loop executes the tool and produces a final answer.
4. The root_dir feature correctly constrains filesystem paths.

Run with::

    RUN_LIVE_TOOL_TESTS=1 pytest tests/live/test_tool_llm_integration.py -v

Environment variables:
    RUN_LIVE_TOOL_TESTS=1    Required to enable (avoids accidental CI cost).
    VERTEX_AI_PROJECT         GCP project ID (if not set in .env).
    GOOGLE_APPLICATION_CREDENTIALS  Path to service account JSON.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Guard — only run when explicitly enabled
# ---------------------------------------------------------------------------

def _live_enabled() -> bool:
    return os.getenv("RUN_LIVE_TOOL_TESTS", "").strip() == "1"


pytestmark = pytest.mark.skipif(
    not _live_enabled(),
    reason="Set RUN_LIVE_TOOL_TESTS=1 to run live LLM tool tests",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm(provider: str | None = None, model: str | None = None):
    """Return a LangChain chat model using the project's configured defaults."""
    from mindflow_backend.runtime.providers import get_model_for_provider
    from mindflow_backend.infra.config import get_settings

    settings = get_settings()
    return get_model_for_provider(
        provider or settings.default_provider,
        model or settings.default_model,
    )


def _make_filesystem_tools(root_dir: str | None = None):
    """Instantiate filesystem tool set, optionally with root_dir."""
    from mindflow_backend.agents.tools.filesystem import (
        FileReadTool,
        FileWriteTool,
        DirectoryListTool,
    )
    tools = [FileReadTool(), FileWriteTool(), DirectoryListTool()]
    if root_dir:
        for t in tools:
            t.root_dir = root_dir
    return tools


def _make_shell_tools():
    """Instantiate shell tool set."""
    from mindflow_backend.agents.tools.system import ShellExecutorTool, SystemInfoTool
    return [ShellExecutorTool(), SystemInfoTool()]


def _make_web_tools():
    """Instantiate lightweight web tools (no browser automation)."""
    from mindflow_backend.agents.tools.web import HttpClientTool
    return [HttpClientTool()]


# ---------------------------------------------------------------------------
# 1. Schema Conversion Tests (no LLM call needed, but kept here for coherence)
# ---------------------------------------------------------------------------

class TestToolSchemaConversion:
    """Verify MindFlow → LangChain StructuredTool conversion."""

    def test_filesystem_tool_converts(self):
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tool
        from mindflow_backend.agents.tools.filesystem import FileReadTool

        lc_tool = to_langchain_tool(FileReadTool())
        assert lc_tool is not None, "FileReadTool must convert successfully"
        assert lc_tool.name == "read_file"
        assert lc_tool.description
        # args_schema must define file_path
        assert "file_path" in lc_tool.args_schema.model_fields

    def test_shell_tool_converts(self):
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tool
        from mindflow_backend.agents.tools.system import ShellExecutorTool

        lc_tool = to_langchain_tool(ShellExecutorTool())
        assert lc_tool is not None
        assert lc_tool.name == "shell_execute"

    def test_all_filesystem_tools_convert(self):
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools

        tools = _make_filesystem_tools()
        lc_tools = to_langchain_tools(tools)
        assert len(lc_tools) == len(tools), (
            f"All {len(tools)} filesystem tools must convert, got {len(lc_tools)}"
        )

    def test_tool_schema_has_required_fields(self):
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tool
        from mindflow_backend.agents.tools.filesystem import FileWriteTool

        lc_tool = to_langchain_tool(FileWriteTool())
        assert lc_tool is not None
        fields = lc_tool.args_schema.model_fields
        # file_path and content are required
        assert "file_path" in fields
        assert "content" in fields


# ---------------------------------------------------------------------------
# 2. Tool Direct Execution Tests (no LLM)
# ---------------------------------------------------------------------------

class TestToolDirectExecution:
    """Verify tools execute correctly before involving the LLM."""

    @pytest.mark.asyncio
    async def test_file_write_then_read(self, tmp_path):
        from mindflow_backend.agents.tools.filesystem import FileWriteTool, FileReadTool

        write = FileWriteTool()
        write.root_dir = str(tmp_path)
        read = FileReadTool()
        read.root_dir = str(tmp_path)

        # Write a test file
        write_result = await write.execute(file_path="hello.txt", content="hello world")
        assert write_result["success"], f"Write failed: {write_result}"

        # Read it back
        read_result = await read.execute(file_path="hello.txt")
        assert read_result["success"], f"Read failed: {read_result}"
        assert "hello world" in read_result["result"]["content"]

    @pytest.mark.asyncio
    async def test_shell_execute_echo(self):
        from mindflow_backend.agents.tools.system import ShellExecutorTool

        shell = ShellExecutorTool()
        result = await shell.execute(command="echo 'tool_test_ok'")
        assert result["success"], f"Shell execute failed: {result}"
        assert "tool_test_ok" in result["result"]["output"]

    @pytest.mark.asyncio
    async def test_directory_list(self, tmp_path):
        # DirectoryListTool from operations.py (legacy) uses "path" parameter
        from mindflow_backend.agents.tools.filesystem import DirectoryListTool

        # Create some files
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")

        tool = DirectoryListTool()
        result = await tool.execute(path=str(tmp_path))
        assert result["success"], f"Directory list failed: {result}"
        entries = result.get("entries", [])
        assert "a.txt" in entries
        assert "b.txt" in entries


# ---------------------------------------------------------------------------
# 3. LLM Tool Binding Verification (real LLM, no execution)
# ---------------------------------------------------------------------------

class TestLLMToolBinding:
    """Verify the LLM receives tool descriptions and generates tool_calls."""

    @pytest.mark.asyncio
    async def test_llm_generates_filesystem_tool_call(self, tmp_path):
        """LLM should call read_file when asked to read a specific file."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools

        # Prepare a file
        test_file = tmp_path / "test_data.txt"
        test_file.write_text("The secret answer is 42.")

        tools = _make_filesystem_tools(root_dir=str(tmp_path))
        lc_tools = to_langchain_tools(tools)
        assert lc_tools, "Tool conversion must succeed"

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a helpful assistant with filesystem access. "
                    f"Your working directory is {tmp_path}. "
                    "Always use tools to answer questions about files."
                ),
            },
            {
                "role": "user",
                "content": f"Read the file test_data.txt and tell me what it says.",
            },
        ]

        response = await llm_with_tools.ainvoke(messages)
        tool_calls = getattr(response, "tool_calls", []) or []

        assert len(tool_calls) > 0, (
            f"LLM should have called a tool but didn't. Response content: {response.content}"
        )
        tool_names = [tc.get("name") for tc in tool_calls]
        # Accept any filesystem tool — LLM may choose list_dir, read_file, etc.
        filesystem_tools = {"read_file", "write_file", "list_dir", "list_directory", "glob_search", "grep_search"}
        assert any(t in filesystem_tools for t in tool_names), (
            f"Expected a filesystem tool call, got: {tool_names}"
        )

    @pytest.mark.asyncio
    async def test_llm_generates_shell_tool_call(self):
        """LLM should call shell_execute when asked to run a command."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools

        tools = _make_shell_tools()
        lc_tools = to_langchain_tools(tools)
        assert lc_tools, "Shell tool conversion must succeed"

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant with shell access. "
                    "Always use the shell_execute tool to run commands."
                ),
            },
            {
                "role": "user",
                "content": "What is the current date? Use the shell to find out.",
            },
        ]

        response = await llm_with_tools.ainvoke(messages)
        tool_calls = getattr(response, "tool_calls", []) or []

        assert len(tool_calls) > 0, (
            f"LLM should have called shell_execute. Response: {response.content}"
        )
        tool_names = [tc.get("name") for tc in tool_calls]
        assert any("shell" in name for name in tool_names), (
            f"Expected shell tool call, got: {tool_names}"
        )

    @pytest.mark.asyncio
    async def test_llm_generates_write_tool_call(self, tmp_path):
        """LLM should call write_file when asked to create a file."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools

        tools = _make_filesystem_tools(root_dir=str(tmp_path))
        lc_tools = to_langchain_tools(tools)

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a file management assistant. "
                    f"Working directory: {tmp_path}. Use tools to manage files."
                ),
            },
            {
                "role": "user",
                "content": "Create a file named output.txt with the content 'Hello from LLM tool test'.",
            },
        ]

        response = await llm_with_tools.ainvoke(messages)
        tool_calls = getattr(response, "tool_calls", []) or []

        assert len(tool_calls) > 0, (
            f"LLM should call write_file. Response: {response.content}"
        )
        tool_names = [tc.get("name") for tc in tool_calls]
        assert "write_file" in tool_names, (
            f"Expected write_file call, got: {tool_names}"
        )


# ---------------------------------------------------------------------------
# 4. Full Invocation Loop Tests (tool call → execute → final answer)
# ---------------------------------------------------------------------------

class TestToolInvocationLoop:
    """End-to-end: LLM calls tool → tool executes → LLM produces answer."""

    @pytest.mark.asyncio
    async def test_read_file_loop(self, tmp_path):
        """Full loop: LLM reads a file and incorporates its content into the answer."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools

        test_file = tmp_path / "secret.txt"
        test_file.write_text("The magic number is 7777.")

        tools = _make_filesystem_tools(root_dir=str(tmp_path))
        lc_tools = to_langchain_tools(tools)

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a helpful assistant with filesystem access. "
                    f"Working directory: {tmp_path}. "
                    "You MUST use the read_file tool to answer questions about file contents."
                ),
            },
            {"role": "user", "content": "What is in secret.txt?"},
        ]

        result = await invoke_with_tools(
            llm=llm_with_tools,
            messages=messages,
            lc_tools=lc_tools,
        )

        assert result, "invoke_with_tools must return non-empty text"
        assert "7777" in result, (
            f"Final answer must contain file content. Got: {result[:500]}"
        )

    @pytest.mark.asyncio
    async def test_shell_command_loop(self):
        """Full loop: LLM runs a shell command and reports the output."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools

        tools = _make_shell_tools()
        lc_tools = to_langchain_tools(tools)

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a system assistant with shell access. "
                    "Use the shell_execute tool for every system-related question."
                ),
            },
            {
                "role": "user",
                "content": "Run 'echo TOOL_TEST_MARKER' and report the exact output.",
            },
        ]

        result = await invoke_with_tools(
            llm=llm_with_tools,
            messages=messages,
            lc_tools=lc_tools,
        )

        assert result, "invoke_with_tools must return text"
        assert "TOOL_TEST_MARKER" in result, (
            f"Final answer must mention the tool output. Got: {result[:500]}"
        )

    @pytest.mark.asyncio
    async def test_write_and_verify_loop(self, tmp_path):
        """Full loop: LLM writes a file then reads it back (multi-turn tool use)."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools

        tools = _make_filesystem_tools(root_dir=str(tmp_path))
        lc_tools = to_langchain_tools(tools)

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a file management assistant. Working directory: {tmp_path}. "
                    "Use write_file and read_file tools as needed."
                ),
            },
            {
                "role": "user",
                "content": (
                    "1) Write a file called result.txt with content 'WRITE_VERIFY_OK'. "
                    "2) Read it back. "
                    "3) Confirm the content matches."
                ),
            },
        ]

        result = await invoke_with_tools(
            llm=llm_with_tools,
            messages=messages,
            lc_tools=lc_tools,
            max_iterations=8,
        )

        assert result, "Must return final answer"
        # Verify the file was actually written on disk
        written = (tmp_path / "result.txt")
        assert written.exists(), "File result.txt must exist on disk after tool execution"
        content = written.read_text()
        assert "WRITE_VERIFY_OK" in content, f"File content mismatch: {content}"


# ---------------------------------------------------------------------------
# 5. Root_dir Feature Tests
# ---------------------------------------------------------------------------

class TestRootDirFeature:
    """Verify root_dir constrains and resolves filesystem paths correctly."""

    @pytest.mark.asyncio
    async def test_relative_path_resolved_via_root_dir(self, tmp_path):
        """Tool must resolve relative path against root_dir."""
        from mindflow_backend.agents.tools.filesystem import FileReadTool, FileWriteTool

        # Write via root_dir-aware tool using relative path
        write = FileWriteTool()
        write.root_dir = str(tmp_path)
        r = await write.execute(file_path="relative.txt", content="root_dir_works")
        assert r["success"], f"Write with relative path failed: {r}"
        assert (tmp_path / "relative.txt").exists(), "File must be at root_dir/relative.txt"

        # Read back with relative path
        read = FileReadTool()
        read.root_dir = str(tmp_path)
        r = await read.execute(file_path="relative.txt")
        assert r["success"], f"Read with relative path failed: {r}"
        assert "root_dir_works" in r["result"]["content"]

    @pytest.mark.asyncio
    async def test_absolute_path_ignores_root_dir(self, tmp_path):
        """Absolute paths must NOT be prefixed with root_dir."""
        from mindflow_backend.agents.tools.filesystem import FileWriteTool, FileReadTool

        target = tmp_path / "absolute_test.txt"

        write = FileWriteTool()
        write.root_dir = "/some/other/dir"  # should be ignored for absolute paths
        r = await write.execute(file_path=str(target), content="absolute_ok")
        assert r["success"], f"Write with absolute path failed: {r}"
        assert target.exists()

    @pytest.mark.asyncio
    async def test_root_dir_propagated_by_registry(self, tmp_path):
        """_DefaultRegistry must set root_dir on all tool instances."""
        from mindflow_backend.agents.tools import create_default_registry
        from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
        from mindflow_backend.schemas.orchestration.orchestrator import AgentType

        sandbox = MindFlowSandbox(root_dir=str(tmp_path))
        registry = create_default_registry(sandbox)
        tools = registry.get_tools_for_agent(AgentType.CODER)

        assert tools, "CODER agent must have tools"
        for tool in tools:
            if hasattr(tool, "root_dir"):
                assert tool.root_dir == str(tmp_path), (
                    f"Tool {tool.name} root_dir mismatch: {tool.root_dir!r} != {tmp_path!r}"
                )

    @pytest.mark.asyncio
    async def test_llm_uses_root_dir_aware_tools(self, tmp_path):
        """LLM tool call with relative path works correctly via root_dir."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools

        (tmp_path / "data.txt").write_text("root_dir_feature=enabled")

        tools = _make_filesystem_tools(root_dir=str(tmp_path))
        lc_tools = to_langchain_tools(tools)

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a helpful assistant. Your working directory is {tmp_path}. "
                    "When reading files, use the filename only (not the full path) since "
                    "your root_dir is already configured. "
                    "Use the read_file tool."
                ),
            },
            {"role": "user", "content": "What does the file data.txt say?"},
        ]

        result = await invoke_with_tools(
            llm=llm_with_tools,
            messages=messages,
            lc_tools=lc_tools,
        )

        assert "root_dir_feature=enabled" in result, (
            f"Expected file content in answer via root_dir. Got: {result[:500]}"
        )


# ---------------------------------------------------------------------------
# 6. Multi-Tool Concurrent Usage
# ---------------------------------------------------------------------------

class TestMultiToolUsage:
    """Verify the LLM can use multiple different tools in one conversation."""

    @pytest.mark.asyncio
    async def test_filesystem_and_shell_tools_together(self, tmp_path):
        """LLM must be able to call both filesystem and shell tools."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools

        (tmp_path / "info.txt").write_text("project_name: MindFlow\nversion: 2.0")

        fs_tools = _make_filesystem_tools(root_dir=str(tmp_path))
        shell_tools = _make_shell_tools()
        all_tools = fs_tools + shell_tools
        lc_tools = to_langchain_tools(all_tools)

        llm = _get_llm()
        llm_with_tools = llm.bind_tools(lc_tools)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are an assistant with filesystem and shell access. "
                    f"Working directory: {tmp_path}."
                ),
            },
            {
                "role": "user",
                "content": (
                    "1. Read the file info.txt and tell me the project name. "
                    "2. Also run 'echo hello_from_shell' and report the output."
                ),
            },
        ]

        result = await invoke_with_tools(
            llm=llm_with_tools,
            messages=messages,
            lc_tools=lc_tools,
            max_iterations=8,
        )

        assert result, "Must return final answer"
        assert "MindFlow" in result, f"Must mention project name from file. Got: {result[:500]}"
        assert "hello_from_shell" in result, f"Must mention shell output. Got: {result[:500]}"
