"""
Exemplo de uso do StreamingToolExecutor.

Este exemplo demonstra como usar o StreamingToolExecutor para
executar ferramentas em paralelo com streaming de resultados.
"""

import asyncio
from typing import Any

from mindflow_backend.runtime.execution.streaming_executor import (
    StreamingToolExecutor,
    ToolDefinition,
    ToolUseContext,
)
from mindflow_backend.schemas.tools.result import ToolResult
from mindflow_backend.schemas.tools.streaming_types import (
    AbortController,
    ToolStatus,
)


# ── Definições de Ferramentas ────────────────────────────────────────

async def read_file(tool_input: dict[str, Any], context: Any) -> ToolResult:
    """Simula leitura de arquivo."""
    path = tool_input.get("path", "")
    print(f"[read_file] Lendo: {path}")
    await asyncio.sleep(0.1)  # Simula I/O
    return ToolResult(
        success=True,
        result=f"Conteúdo do arquivo {path}",
        tool_name="read_file",
    )


async def write_file(tool_input: dict[str, Any], context: Any) -> ToolResult:
    """Simula escrita de arquivo."""
    path = tool_input.get("path", "")
    content = tool_input.get("content", "")
    print(f"[write_file] Escrevendo em: {path}")
    await asyncio.sleep(0.2)  # Simula I/O
    return ToolResult(
        success=True,
        result=f"Arquivo {path} escrito com {len(content)} caracteres",
        tool_name="write_file",
    )


async def search_web(tool_input: dict[str, Any], context: Any) -> ToolResult:
    """Simula busca na web."""
    query = tool_input.get("query", "")
    print(f"[search_web] Buscando: {query}")
    await asyncio.sleep(0.3)  # Simula rede
    return ToolResult(
        success=True,
        result=f"Resultados para: {query}",
        tool_name="search_web",
    )


async def failing_tool(tool_input: dict[str, Any], context: Any) -> ToolResult:
    """Ferramenta que sempre falha."""
    print("[failing_tool] Executando...")
    await asyncio.sleep(0.1)
    raise ValueError("Esta ferramenta falhou intencionalmente!")


# ── Configuração ─────────────────────────────────────────────────────

def create_tool_definitions() -> dict[str, ToolDefinition]:
    """Cria definições de ferramentas."""
    return {
        "read_file": ToolDefinition(
            name="read_file",
            callable=read_file,
            is_concurrency_safe=True,
        ),
        "write_file": ToolDefinition(
            name="write_file",
            callable=write_file,
            is_concurrency_safe=True,
        ),
        "search_web": ToolDefinition(
            name="search_web",
            callable=search_web,
            is_concurrency_safe=True,
        ),
        "failing_tool": ToolDefinition(
            name="failing_tool",
            callable=failing_tool,
            is_concurrency_safe=True,
        ),
    }


async def can_use_tool(tool_name: str, tool_input: dict[str, Any]) -> tuple[bool, str | None]:
    """Função de permissão - sempre permite."""
    return True, None


# ── Exemplos de Uso ──────────────────────────────────────────────────

async def example_basic_execution():
    """Exemplo 1: Execução básica de múltiplas ferramentas."""
    print("\n=== Exemplo 1: Execução Básica ===\n")

    tool_definitions = create_tool_definitions()
    abort_controller = AbortController()
    tool_context = ToolUseContext(
        session_id="session-001",
        abort_controller=abort_controller,
    )

    executor = StreamingToolExecutor(
        tool_definitions=tool_definitions,
        can_use_tool=can_use_tool,
        tool_use_context=tool_context,
        max_concurrent=3,
    )

    # Adiciona ferramentas
    executor.add_tool("tool-1", "read_file", {"path": "/tmp/file1.txt"})
    executor.add_tool("tool-2", "read_file", {"path": "/tmp/file2.txt"})
    executor.add_tool("tool-3", "search_web", {"query": "Python async"})

    # Obtém resultados conforme ficam prontos
    print("Executando ferramentas...")
    async for result in executor.get_remaining_results():
        status_icon = "✓" if result.status == ToolStatus.COMPLETED else "✗"
        print(f"  {status_icon} {result.tool_name} ({result.status.value})")
        if result.result:
            print(f"     Resultado: {result.result}")

    # Mostra estatísticas
    stats = executor.get_stats()
    print(f"\nEstatísticas: {stats}")


async def example_concurrent_execution():
    """Exemplo 2: Execução concorrente com medição de tempo."""
    print("\n=== Exemplo 2: Execução Concorrente ===\n")

    import time

    tool_definitions = create_tool_definitions()
    abort_controller = AbortController()
    tool_context = ToolUseContext(
        session_id="session-002",
        abort_controller=abort_controller,
    )

    executor = StreamingToolExecutor(
        tool_definitions=tool_definitions,
        can_use_tool=can_use_tool,
        tool_use_context=tool_context,
        max_concurrent=5,
    )

    # Adiciona 5 ferramentas
    for i in range(5):
        executor.add_tool(
            f"tool-{i}",
            "read_file",
            {"path": f"/tmp/file{i}.txt"},
        )

    start_time = time.time()
    results = await executor.wait_all()
    total_time = time.time() - start_time

    print(f"Executadas {len(results)} ferramentas em {total_time:.2f}s")
    print(f"Tempo médio por ferramenta: {total_time/len(results):.2f}s")


async def example_error_handling():
    """Exemplo 3: Tratamento de erros e abort."""
    print("\n=== Exemplo 3: Tratamento de Erros ===\n")

    tool_definitions = create_tool_definitions()
    abort_controller = AbortController()
    tool_context = ToolUseContext(
        session_id="session-003",
        abort_controller=abort_controller,
    )

    executor = StreamingToolExecutor(
        tool_definitions=tool_definitions,
        can_use_tool=can_use_tool,
        tool_use_context=tool_context,
        max_concurrent=5,
    )

    # Adiciona ferramentas (incluindo uma que falha)
    executor.add_tool("tool-1", "read_file", {"path": "/tmp/file1.txt"})
    executor.add_tool("tool-2", "failing_tool", {})
    executor.add_tool("tool-3", "read_file", {"path": "/tmp/file3.txt"})

    print("Executando ferramentas (uma vai falhar)...")
    async for result in executor.get_remaining_results():
        if result.status == ToolStatus.COMPLETED:
            print(f"  ✓ {result.tool_name}: Sucesso")
        elif result.status == ToolStatus.ERROR:
            print(f"  ✗ {result.tool_name}: Erro - {result.error}")
        elif result.status == ToolStatus.DISCARDED:
            print(f"  ⊘ {result.tool_name}: Descartada")


async def example_non_concurrent_tools():
    """Exemplo 4: Ferramentas não-concorrentes."""
    print("\n=== Exemplo 4: Ferramentas Não-Concorrentes ===\n")

    tool_definitions = create_tool_definitions()
    # Adiciona ferramenta não-concorrente
    tool_definitions["write_file"] = ToolDefinition(
        name="write_file",
        callable=write_file,
        is_concurrency_safe=False,  # Não pode rodar em paralelo
    )

    abort_controller = AbortController()
    tool_context = ToolUseContext(
        session_id="session-004",
        abort_controller=abort_controller,
    )

    executor = StreamingToolExecutor(
        tool_definitions=tool_definitions,
        can_use_tool=can_use_tool,
        tool_use_context=tool_context,
        max_concurrent=5,
    )

    # Adiciona ferramentas concorrentes e não-concorrentes
    executor.add_tool("tool-1", "read_file", {"path": "/tmp/file1.txt"})
    executor.add_tool("tool-2", "write_file", {"path": "/tmp/out.txt", "content": "dados"})
    executor.add_tool("tool-3", "read_file", {"path": "/tmp/file2.txt"})

    print("Executando (write_file não é concorrente)...")
    async for result in executor.get_remaining_results():
        print(f"  • {result.tool_name}: {result.status.value}")


async def example_manual_abort():
    """Exemplo 5: Cancelamento manual."""
    print("\n=== Exemplo 5: Cancelamento Manual ===\n")

    tool_definitions = create_tool_definitions()
    abort_controller = AbortController()
    tool_context = ToolUseContext(
        session_id="session-005",
        abort_controller=abort_controller,
    )

    executor = StreamingToolExecutor(
        tool_definitions=tool_definitions,
        can_use_tool=can_use_tool,
        tool_use_context=tool_context,
        max_concurrent=5,
    )

    # Adiciona ferramentas
    for i in range(5):
        executor.add_tool(
            f"tool-{i}",
            "read_file",
            {"path": f"/tmp/file{i}.txt"},
        )

    # Cancela após um curto período
    async def cancel_after_delay():
        await asyncio.sleep(0.05)
        print("  ⚠ Cancelando execução...")
        executor.discard()

    asyncio.create_task(cancel_after_delay())

    print("Executando (será cancelada)...")
    async for result in executor.get_remaining_results():
        print(f"  • {result.tool_name}: {result.status.value}")


# ── Main ─────────────────────────────────────────────────────────────

async def main():
    """Executa todos os exemplos."""
    print("=" * 60)
    print("StreamingToolExecutor - Exemplos de Uso")
    print("=" * 60)

    await example_basic_execution()
    await example_concurrent_execution()
    await example_error_handling()
    await example_non_concurrent_tools()
    await example_manual_abort()

    print("\n" + "=" * 60)
    print("Todos os exemplos concluídos!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())