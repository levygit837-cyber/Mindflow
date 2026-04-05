#!/usr/bin/env python3
"""Script de teste manual para o sistema unificado de execução de tools.

Este script testa os novos módulos sem depender do __init__.py do projeto.
"""

import sys
import os

# Adiciona paths específicos ao invés do __init__.py
sys.path.insert(0, "/home/levybonito/Projetos/MindFlow/python/mindflow_backend")
sys.path.insert(0, "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/runtime/execution")
sys.path.insert(0, "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/schemas/tools")

# Importa módulos diretamente para evitar __init__.py problemático
import importlib.util

def import_module_from_file(module_name, file_path):
    """Importa módulo diretamente do arquivo."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Importa ToolResult
tool_result_module = import_module_from_file(
    "tool_result",
    "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/schemas/tools/result.py"
)
ToolResult = tool_result_module.ToolResult

# Importa streaming_types
streaming_types_module = import_module_from_file(
    "streaming_types",
    "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/schemas/tools/streaming_types.py"
)
ToolDefinition = streaming_types_module.ToolDefinition
ToolUseContext = streaming_types_module.ToolUseContext

# Importa tool_partition
tool_partition_module = import_module_from_file(
    "tool_partition",
    "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/runtime/execution/tool_partition.py"
)
partition_tool_calls = tool_partition_module.partition_tool_calls

# Importa streaming_executor
streaming_executor_module = import_module_from_file(
    "streaming_executor",
    "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/runtime/execution/streaming_executor.py"
)
StreamingToolExecutor = streaming_executor_module.StreamingToolExecutor

print("=" * 60)
print("TESTE DO SISTEMA UNIFICADO DE EXECUÇÃO DE TOOLS")
print("=" * 60)

# Teste 1: Partition
print("\n[Teste 1] Partition de tool calls")
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
    {"name": "FileRead", "args": {"path": "/tmp/b.txt"}, "id": "2"},
    {"name": "FileWrite", "args": {"path": "/tmp/c.txt"}, "id": "3"},
    {"name": "FileRead", "args": {"path": "/tmp/d.txt"}, "id": "4"},
]

batches = partition_tool_calls(tool_calls, tool_definitions)
print(f"✓ Criados {len(batches)} batches")
for i, batch in enumerate(batches):
    print(f"  Batch {i+1}: concurrent_safe={batch.is_concurrent_safe}, {len(batch.blocks)} tools")

assert len(batches) == 3, "Deve criar 3 batches"
assert batches[0].is_concurrency_safe is True, "Batch 1 deve ser concurrent-safe"
assert batches[1].is_concurrency_safe is False, "Batch 2 deve ser serial"
assert batches[2].is_concurrency_safe is True, "Batch 3 deve ser concurrent-safe"
print("✓ Teste 1 PASSOU")

# Teste 2: StreamingToolExecutor.execute_batch()
print("\n[Teste 2] Execute batch com tools mock")
import asyncio

async def mock_tool(input_dict, context):
    return ToolResult(content="OK", success=True)

tool_definitions_test = {
    "MockTool": ToolDefinition(
        name="MockTool",
        callable=mock_tool,
        is_concurrency_safe=True,
        description="Mock tool",
    )
}

async def test_execute_batch():
    executor = StreamingToolExecutor(
        tool_definitions=tool_definitions_test,
        can_use_tool=lambda name, input: (True, None),
        tool_use_context=ToolUseContext(session_id="test"),
        max_concurrent=5,
    )

    tool_calls_test = [
        {"name": "MockTool", "args": {"test": "value"}, "id": "tool-1"},
        {"name": "MockTool", "args": {"test": "value2"}, "id": "tool-2"},
    ]

    results = await executor.execute_batch(tool_calls_test)
    print(f"✓ Executados {len(results)} tools")
    for result in results:
        print(f"  Tool: {result.tool_name}, Status: {result.status.value}")

    assert len(results) == 2, "Deve retornar 2 resultados"
    assert all(r.status.value == "completed" for r in results), "Todos devem completar"
    print("✓ Teste 2 PASSOU")

asyncio.run(test_execute_batch())

# Teste 3: Execução serial vs paralela
print("\n[Teste 3] Execução serial vs paralela")

execution_log = []

async def mock_tool_a(input_dict, context):
    execution_log.append("A")
    await asyncio.sleep(0.05)
    return ToolResult(content="A", success=True)

async def mock_tool_b(input_dict, context):
    execution_log.append("B")
    await asyncio.sleep(0.05)
    return ToolResult(content="B", success=True)

async def test_serial_vs_parallel():
    # Teste serial
    tool_definitions_serial = {
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

    executor_serial = StreamingToolExecutor(
        tool_definitions=tool_definitions_serial,
        can_use_tool=lambda name, input: (True, None),
        tool_use_context=ToolUseContext(session_id="test"),
        max_concurrent=5,
    )

    tool_calls_serial = [
        {"name": "ToolA", "args": {}, "id": "1"},
        {"name": "ToolB", "args": {}, "id": "2"},
    ]

    execution_log.clear()
    results_serial = await executor_serial.execute_batch(tool_calls_serial)
    print(f"✓ Execução serial: ordem = {execution_log}")
    assert execution_log == ["A", "B"], "Serial deve executar em ordem"

    # Teste paralelo
    tool_definitions_parallel = {
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

    executor_parallel = StreamingToolExecutor(
        tool_definitions=tool_definitions_parallel,
        can_use_tool=lambda name, input: (True, None),
        tool_use_context=ToolUseContext(session_id="test"),
        max_concurrent=5,
    )

    execution_log.clear()
    results_parallel = await executor_parallel.execute_batch(tool_calls_serial)
    print(f"✓ Execução paralela: ordem = {execution_log}")
    # Paralelo pode ter qualquer ordem, mas deve ter 2 itens
    assert len(execution_log) == 2, "Paralelo deve executar ambos"

    print("✓ Teste 3 PASSOU")

asyncio.run(test_serial_vs_parallel())

print("\n" + "=" * 60)
print("TODOS OS TESTES PASSARAM!")
print("=" * 60)
