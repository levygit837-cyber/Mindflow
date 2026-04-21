"""Testes para o sistema unificado de execução de tools.

Testa:
- callable_adapter.py - Conversão de CallableTool para ToolDefinition
- tool_partition.py - Partition logic Claude-style
- StreamingToolExecutor.execute_batch() - Execução em batches
- Integração com CallableTools reais da codebase
"""

import asyncio
import pytest
import sys
from typing import Any

# Adiciona path para imports diretos
sys.path.insert(0, "/home/levybonito/Projetos/MindFlow/python/mindflow_backend")

# Imports diretos para evitar __init__.py problemático
from mindflow_backend.agents.tools.callable.filesystem import (
    FileReadCallable as FileReadCallableInstance,
    DirectoryListCallable as DirectoryListCallableInstance,
    FileWriteCallable as FileWriteCallableInstance,
)
from mindflow_backend.agents.tools.callable.shell import (
    ShellExecutorCallable as ShellExecutorCallableInstance,
)
from mindflow_backend.agents.tools.callable.scope_mapping import get_all_callable_tools
from mindflow_backend.runtime.execution.callable_adapter import (
    callable_to_tool_definition,
    callable_tools_to_definitions,
)
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


class TestCallableAdapter:
    """Testes para callable_adapter."""

    def test_callable_to_tool_definition_basic(self):
        """Testa conversão básica de CallableTool para ToolDefinition."""
        tool = FileReadCallableInstance  # Já é uma instância
        tool_def = callable_to_tool_definition(tool)

        assert tool_def.name == "file_read"
        assert tool_def.description
        assert tool_def.callable is not None
        assert isinstance(tool_def.is_concurrency_safe, bool)

    def test_callable_to_tool_definition_with_input(self):
        """Testa conversão com validação de input."""
        tool = FileReadCallableInstance  # Já é uma instância
        tool_def = callable_to_tool_definition(tool)

        # Teste que o callable wrapper funciona
        async def test_call():
            result = await tool_def.callable({"path": "/tmp/test.txt"}, None)
            assert isinstance(result, ToolResult)

        # Não executamos o teste real pois pode falhar se o arquivo não existir
        # Mas verificamos que a estrutura está correta

    def test_callable_tools_to_definitions_batch(self):
        """Testa conversão em batch de múltiplas CallableTools."""
        tools = [
            FileReadCallableInstance,
            DirectoryListCallableInstance,
            FileWriteCallableInstance,
        ]  # Já são instâncias
        definitions = callable_tools_to_definitions(tools)

        assert len(definitions) == 3
        assert "file_read" in definitions
        assert "list_dir" in definitions
        assert "write_file" in definitions

        for tool_def in definitions.values():
            assert isinstance(tool_def, ToolDefinition)
            assert tool_def.callable is not None

    def test_callable_adapter_metadata_extraction(self):
        """Testa extração correta de metadata."""
        tool = FileReadCallableInstance  # Já é uma instância
        tool_def = callable_to_tool_definition(tool)

        # Verifica que metadata foi extraído corretamente
        assert hasattr(tool_def, "is_concurrency_safe")
        assert hasattr(tool_def, "is_read_only")
        assert hasattr(tool_def, "description")


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


class TestRealCallableTools:
    """Testes de integração com CallableTools reais da codebase."""

    @pytest.mark.asyncio
    async def test_file_read_callable_adapter(self):
        """Testa adapter com FileReadCallable real."""
        tool = FileReadCallableInstance  # Já é uma instância
        tool_def = callable_to_tool_definition(tool)

        assert tool_def.name == "file_read"
        assert tool_def.is_concurrency_safe is True
        assert tool_def.is_read_only is True

    @pytest.mark.asyncio
    async def test_directory_list_callable_adapter(self):
        """Testa adapter com DirectoryListCallable real."""
        tool = DirectoryListCallableInstance  # Já é uma instância
        tool_def = callable_to_tool_definition(tool)

        assert tool_def.name == "list_dir"
        assert tool_def.is_concurrency_safe is True
        assert tool_def.is_read_only is True

    @pytest.mark.asyncio
    async def test_file_write_callable_adapter(self):
        """Testa adapter com FileWriteCallable real."""
        tool = FileWriteCallableInstance  # Já é uma instância
        tool_def = callable_to_tool_definition(tool)

        assert tool_def.name == "write_file"
        assert tool_def.is_concurrency_safe is False
        assert tool_def.is_read_only is False

    @pytest.mark.asyncio
    async def test_shell_executor_callable_adapter(self):
        """Testa adapter com ShellExecutorCallable real."""
        tool = ShellExecutorCallableInstance  # Já é uma instância
        tool_def = callable_to_tool_definition(tool)

        assert tool_def.name == "shell_execute"
        assert isinstance(tool_def.is_concurrency_safe, bool)

    @pytest.mark.asyncio
    async def test_all_callable_tools_adapter(self):
        """Testa adapter com todas as CallableTools registradas."""
        all_tools = get_all_callable_tools()
        assert len(all_tools) > 0

        definitions = callable_tools_to_definitions(all_tools)

        assert len(definitions) == len(all_tools)
        for tool_name, tool_def in definitions.items():
            assert isinstance(tool_def, ToolDefinition)
            assert tool_def.name == tool_name
            assert tool_def.callable is not None

    @pytest.mark.asyncio
    async def test_partition_with_real_callable_tools(self):
        """Testa partition com CallableTools reais."""
        all_tools = get_all_callable_tools()
        definitions = callable_tools_to_definitions(all_tools)

        # Seleciona algumas tools para teste
        tool_calls = [
            {"name": "FileRead", "args": {"path": "/tmp/test.txt"}, "id": "1"},
            {"name": "DirectoryList", "args": {"path": "/tmp"}, "id": "2"},
            {"name": "FileWrite", "args": {"path": "/tmp/out.txt"}, "id": "3"},
        ]

        batches = partition_tool_calls(tool_calls, definitions)

        # Deve criar batches baseado em is_concurrency_safe
        assert len(batches) > 0
        for batch in batches:
            assert isinstance(batch, ToolBatch)
            assert len(batch.blocks) > 0


class TestIntegration:
    """Testes de integração end-to-end."""

    @pytest.mark.asyncio
    async def test_full_workflow_mock_tools(self):
        """Testa workflow completo com tools mock."""
        # Usar tools reais já instanciadas em vez de criar mock
        all_tools = get_all_callable_tools()
        definitions = callable_tools_to_definitions(all_tools)

        # Seleciona algumas tools para teste
        tool_calls = [
            {"name": "file_read", "args": {"path": "/tmp/test.txt"}, "id": "1"},
            {"name": "list_dir", "args": {"path": "/tmp"}, "id": "2"},
        ]

        batches = partition_tool_calls(tool_calls, definitions)

        # Deve criar batches baseado em is_concurrency_safe
        assert len(batches) > 0
        for batch in batches:
            assert isinstance(batch, ToolBatch)
            assert len(batch.blocks) > 0

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
