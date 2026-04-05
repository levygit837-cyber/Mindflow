"""Testes simplificados para o sistema unificado de execução de tools.

Testa apenas o core sem dependências externas complexas.
"""

import asyncio
import pytest
import sys
from typing import Any

sys.path.insert(0, "/home/levybonito/Projetos/MindFlow/python/mindflow_backend")

from mindflow_backend.runtime.execution.tool_partition import (
    partition_tool_calls,
    ToolBatch,
)
from mindflow_backend.runtime.execution.streaming_executor import (
    StreamingToolExecutor,
    ToolDefinition,
    ToolUseContext,
)
from mindflow_backend.schemas.tools.result import ToolResult


class TestToolPartition:
    """Testes para tool_partition logic."""

    def test_partition_empty_list(self):
        """Testa partition de lista vazia."""
        tool_definitions = {
            "FileRead": ToolDefinition(
                name="FileRead",
                callable=lambda x, y: None,
                is_concurrency_safe=True,
                description="Read file",
            )
        }
        batches = partition_tool_calls([], tool_definitions)
        assert batches == []

    def test_partition_single_concurrent_safe(self):
        """Testa partition de única ferramenta concurrent-safe."""
        tool_definitions = {
            "FileRead": ToolDefinition(
                name="FileRead",
                callable=lambda x, y: None,
                is_concurrency_safe=True,
                description="Read file",
            )
        }
        tool_calls = [
            {"name": "FileRead", "args": {"path": "/tmp/a.txt"}, "id": "1"}
        ]
        batches = partition_tool_calls(tool_calls, tool_definitions)

        assert len(batches) == 1
        assert batches[0].is_concurrent_safe is True
        assert len(batches[0].blocks) == 1

    def test_partition_single_non_concurrent(self):
        """Testa partition de única ferramenta não-concurrent."""
        tool_definitions = {
            "FileWrite": ToolDefinition(
                name="FileWrite",
                callable=lambda x, y: None,
                is_concurrency_safe=False,
                description="Write file",
            )
        }
        tool_calls = [
            {"name": "FileWrite", "args": {"path": "/tmp/a.txt"}, "id": "1"}
        ]
        batches = partition_tool_calls(tool_calls, tool_definitions)

        assert len(batches) == 1
        assert batches[0].is_concurrent_safe is False
        assert len(batches[0].blocks) == 1

    def test_partition_multiple_concurrent_safe(self):
        """Testa partition de múltiplas ferramentas concurrent-safe."""
        tool_definitions = {
            "FileRead": ToolDefinition(
                name="FileRead",
                callable=lambda x, y: None,
                is_concurrency_safe=True,
                description="Read file",
            ),
            "DirectoryList": ToolDefinition(
                name="DirectoryList",
                callable=lambda x, y: None,
                is_concurrency_safe=True,
                description="List directory",
            ),
        }
        tool_calls = [
            {"name": "FileRead", "args": {"path": "/tmp/a.txt"}, "id": "1"},
            {"name": "DirectoryList", "args": {"path": "/tmp"}, "id": "2"},
            {"name": "FileRead", "args": {"path": "/tmp/b.txt"}, "id": "3"},
        ]
        batches = partition_tool_calls(tool_calls, tool_definitions)

        # Todas devem estar no mesmo batch concurrent-safe
        assert len(batches) == 1
        assert batches[0].is_concurrent_safe is True
        assert len(batches[0].blocks) == 3

    def test_partition_mixed_concurrent_and_serial(self):
        """Testa partition misto de concurrent-safe e serial."""
        tool_definitions = {
            "FileRead": ToolDefinition(
                name="FileRead",
                callable=lambda x, y: None,
                is_concurrency_safe=True,
                description="Read file",
            ),
            "FileWrite": ToolDefinition(
                name="FileWrite",
                callable=lambda x, y: None,
                is_concurrency_safe=False,
                description="Write file",
            ),
        }
        tool_calls = [
            {"name": "FileRead", "args": {"path": "/tmp/a.txt"}, "id": "1"},
            {"name": "FileWrite", "args": {"path": "/tmp/b.txt"}, "id": "2"},
            {"name": "FileRead", "args": {"path": "/tmp/c.txt"}, "id": "3"},
        ]
        batches = partition_tool_calls(tool_calls, tool_definitions)

        # Deve criar 3 batches:
        # 1. FileRead (concurrent-safe)
        # 2. FileWrite (serial)
        # 3. FileRead (concurrent-safe)
        assert len(batches) == 3
        assert batches[0].is_concurrent_safe is True
        assert batches[1].is_concurrent_safe is False
        assert batches[2].is_concurrent_safe is True

    def test_partition_consecutive_concurrent_safe_grouped(self):
        """Testa que consecutive concurrent-safe são agrupados."""
        tool_definitions = {
            "FileRead": ToolDefinition(
                name="FileRead",
                callable=lambda x, y: None,
                is_concurrency_safe=True,
                description="Read file",
            ),
        }
        tool_calls = [
            {"name": "FileRead", "args": {"path": "/tmp/a.txt"}, "id": "1"},
            {"name": "FileRead", "args": {"path": "/tmp/b.txt"}, "id": "2"},
            {"name": "FileRead", "args": {"path": "/tmp/c.txt"}, "id": "3"},
        ]
        batches = partition_tool_calls(tool_calls, tool_definitions)

        # Todas no mesmo batch
        assert len(batches) == 1
        assert batches[0].is_concurrent_safe is True
        assert len(batches[0].blocks) == 3

    def test_partition_unknown_tool(self):
        """Testa partition com ferramenta desconhecida."""
        tool_definitions = {}
        tool_calls = [
            {"name": "UnknownTool", "args": {}, "id": "1"}
        ]
        batches = partition_tool_calls(tool_calls, tool_definitions)

        # Deve criar um batch serial (safe default)
        assert len(batches) == 1
        assert batches[0].is_concurrent_safe is False


class TestStreamingToolExecutorBatch:
    """Testes para StreamingToolExecutor.execute_batch()."""

    @pytest.mark.asyncio
    async def test_execute_batch_empty(self):
        """Testa execução de batch vazio."""
        tool_definitions = {}
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=lambda name, input: (True, None),
            tool_use_context=ToolUseContext(session_id="test"),
            max_concurrent=5,
        )

        results = await executor.execute_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_batch_single_tool(self):
        """Testa execução de batch com única ferramenta."""
        async def mock_tool(input_dict, context):
            return ToolResult(content="OK", success=True)

        tool_definitions = {
            "MockTool": ToolDefinition(
                name="MockTool",
                callable=mock_tool,
                is_concurrency_safe=True,
                description="Mock tool",
            )
        }
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=lambda name, input: (True, None),
            tool_use_context=ToolUseContext(session_id="test"),
            max_concurrent=5,
        )

        tool_calls = [
            {"name": "MockTool", "args": {"test": "value"}, "id": "tool-1"}
        ]
        results = await executor.execute_batch(tool_calls)

        assert len(results) == 1
        assert results[0].tool_name == "MockTool"
        assert results[0].tool_id == "tool-1"
        assert results[0].status.value == "completed"

    @pytest.mark.asyncio
    async def test_execute_batch_concurrent_tools(self):
        """Testa execução paralela de ferramentas concurrent-safe."""
        execution_order = []

        async def mock_tool_a(input_dict, context):
            execution_order.append("A")
            await asyncio.sleep(0.1)
            return ToolResult(content="A", success=True)

        async def mock_tool_b(input_dict, context):
            execution_order.append("B")
            await asyncio.sleep(0.1)
            return ToolResult(content="B", success=True)

        tool_definitions = {
            "ToolA": ToolDefinition(
                name="ToolA",
                callable=mock_tool_a,
                is_concurrency_safe=True,
                description="Tool A",
            ),
            "ToolB": ToolDefinition(
                name="ToolB",
                callable=mock_tool_b,
                is_concurrency_safe=True,
                description="Tool B",
            ),
        }
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=lambda name, input: (True, None),
            tool_use_context=ToolUseContext(session_id="test"),
            max_concurrent=5,
        )

        tool_calls = [
            {"name": "ToolA", "args": {}, "id": "1"},
            {"name": "ToolB", "args": {}, "id": "2"},
        ]
        results = await executor.execute_batch(tool_calls)

        assert len(results) == 2
        # Deve executar em paralelo, então a ordem não é garantida
        assert len(execution_order) == 2

    @pytest.mark.asyncio
    async def test_execute_batch_serial_tools(self):
        """Testa execução serial de ferramentas não-concurrent."""
        execution_order = []

        async def mock_tool_a(input_dict, context):
            execution_order.append("A")
            await asyncio.sleep(0.05)
            return ToolResult(content="A", success=True)

        async def mock_tool_b(input_dict, context):
            execution_order.append("B")
            await asyncio.sleep(0.05)
            return ToolResult(content="B", success=True)

        tool_definitions = {
            "ToolA": ToolDefinition(
                name="ToolA",
                callable=mock_tool_a,
                is_concurrency_safe=False,
                description="Tool A",
            ),
            "ToolB": ToolDefinition(
                name="ToolB",
                callable=mock_tool_b,
                is_concurrency_safe=False,
                description="Tool B",
            ),
        }
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=lambda name, input: (True, None),
            tool_use_context=ToolUseContext(session_id="test"),
            max_concurrent=5,
        )

        tool_calls = [
            {"name": "ToolA", "args": {}, "id": "1"},
            {"name": "ToolB", "args": {}, "id": "2"},
        ]
        results = await executor.execute_batch(tool_calls)

        assert len(results) == 2
        # Deve executar em ordem serial
        assert execution_order == ["A", "B"]

    @pytest.mark.asyncio
    async def test_execute_batch_unknown_tool(self):
        """Testa execução com ferramenta desconhecida."""
        tool_definitions = {}
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=lambda name, input: (True, None),
            tool_use_context=ToolUseContext(session_id="test"),
            max_concurrent=5,
        )

        tool_calls = [
            {"name": "UnknownTool", "args": {}, "id": "1"}
        ]
        results = await executor.execute_batch(tool_calls)

        assert len(results) == 1
        assert results[0].status.value == "error"
        assert "Unknown tool" in results[0].error

    @pytest.mark.asyncio
    async def test_execute_batch_mixed_concurrent_and_serial(self):
        """Testa execução mista de concurrent e serial."""
        execution_log = []

        async def mock_tool(input_dict, context):
            tool_name = input_dict.get("name", "Unknown")
            execution_log.append(tool_name)
            return ToolResult(content=f"Result from {tool_name}", success=True)

        tool_definitions = {
            "ConcurrentTool": ToolDefinition(
                name="ConcurrentTool",
                callable=mock_tool,
                is_concurrency_safe=True,
                description="Concurrent tool",
            ),
            "SerialTool": ToolDefinition(
                name="SerialTool",
                callable=mock_tool,
                is_concurrency_safe=False,
                description="Serial tool",
            ),
        }
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=lambda name, input: (True, None),
            tool_use_context=ToolUseContext(session_id="test"),
            max_concurrent=5,
        )

        tool_calls = [
            {"name": "ConcurrentTool", "args": {"name": "C1"}, "id": "1"},
            {"name": "SerialTool", "args": {"name": "S1"}, "id": "2"},
            {"name": "ConcurrentTool", "args": {"name": "C2"}, "id": "3"},
        ]
        results = await executor.execute_batch(tool_calls)

        assert len(results) == 3
        # SerialTool deve executar entre os concurrent tools
        assert len(execution_log) == 3


class TestIntegration:
    """Testes de integração end-to-end."""

    @pytest.mark.asyncio
    async def test_partition_and_execute_integration(self):
        """Testa integração de partition + execute."""
        # Criar tools com diferentes propriedades de concorrência
        async def concurrent_tool(input_dict, context):
            return ToolResult(content="Concurrent result", success=True)

        async def serial_tool(input_dict, context):
            return ToolResult(content="Serial result", success=True)

        definitions = {
            "ConcurrentTool": ToolDefinition(
                name="ConcurrentTool",
                callable=concurrent_tool,
                is_concurrency_safe=True,
                description="Concurrent",
            ),
            "SerialTool": ToolDefinition(
                name="SerialTool",
                callable=serial_tool,
                is_concurrency_safe=False,
                description="Serial",
            ),
        }

        # Criar tool calls mistos
        tool_calls = [
            {"name": "ConcurrentTool", "args": {}, "id": "1"},
            {"name": "SerialTool", "args": {}, "id": "2"},
            {"name": "ConcurrentTool", "args": {}, "id": "3"},
        ]

        # Partition
        batches = partition_tool_calls(tool_calls, definitions)
        assert len(batches) == 3

        # Execute
        executor = StreamingToolExecutor(
            tool_definitions=definitions,
            can_use_tool=lambda name, input: (True, None),
            tool_use_context=ToolUseContext(session_id="test"),
            max_concurrent=5,
        )

        results = await executor.execute_batch(tool_calls)
        assert len(results) == 3
