"""Build Tool Pattern - Factory para criar ferramentas com defaults inteligentes.

Inspirado no buildTool() do Claude Code.
Fornece type safety, defaults sensíveis e configuração declarativa.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar, Protocol, overload

from mindflow_backend.schemas.tools.result import ToolResult

# Type variables para generics
TInput = TypeVar("TInput", bound=dict[str, Any])
TOutput = TypeVar("TOutput")


class InterruptBehavior(Enum):
    """Comportamento da ferramenta quando o usuário interrompe."""

    CANCEL = "cancel"  # Cancela execução
    BLOCK = "block"  # Bloqueia interrupção até completar


@dataclass
class ToolContext:
    """Contexto passado para execução da ferramenta."""

    session_id: str
    cwd: str | None = None
    abort_signal: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolCallable(Protocol):
    """Protocol para callable de ferramenta."""

    async def __call__(
        self,
        tool_input: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        """Executa a ferramenta."""
        ...


class ToolDescription(Protocol):
    """Protocol para descrição dinâmica."""

    async def __call__(self) -> str:
        """Retorna descrição da ferramenta."""
        ...


@dataclass
class ToolDef(Generic[TInput, TOutput]):
    """Definição de ferramenta com defaults inteligentes.

    Attributes:
        name: Nome único da ferramenta
        description: Descrição estática ou callable assíncrono
        input_schema: Schema de input (para validação)
        callable: Função de execução
        is_concurrency_safe: Se pode rodar em paralelo com outras
        is_read_only: Se não modifica estado (não aborta irmãos)
        interrupt_behavior: Como reagir a interrupções
        max_result_size_chars: Tamanho máximo do resultado
        timeout_seconds: Timeout de execução
    """

    name: str
    description: str | Callable[[], str | Awaitable[str]]
    callable: ToolCallable
    input_schema: type[TInput] | None = None
    is_concurrency_safe: bool = True
    is_read_only: bool = False
    is_destructive: bool = False
    interrupt_behavior: InterruptBehavior = InterruptBehavior.BLOCK
    max_result_size_chars: int = 100_000
    timeout_seconds: float = 30.0


@dataclass
class BuiltTool(Generic[TInput, TOutput]):
    """Ferramenta construída com defaults aplicados.

    Resultado do build_tool(), pronto para uso.
    """

    name: str
    description: str | Callable[[], str | Awaitable[str]]
    callable: ToolCallable
    input_schema: type[TInput] | None
    is_concurrency_safe: bool
    is_read_only: bool
    is_destructive: bool
    interrupt_behavior: InterruptBehavior
    max_result_size_chars: int
    timeout_seconds: float

    async def get_description(self) -> str:
        """Retorna descrição, resolvendo callable se necessário."""
        if isinstance(self.description, str):
            return self.description
        return await self.description()


# Defaults inteligentes
TOOL_DEFAULTS = {
    "is_concurrency_safe": True,
    "is_read_only": False,
    "interrupt_behavior": InterruptBehavior.BLOCK,
    "max_result_size_chars": 100_000,
    "timeout_seconds": 30.0,
}


def build_tool(
    name: str,
    *,
    description: str | Callable[[], str | Awaitable[str]],
    callable: ToolCallable | None = None,
    execute: ToolCallable | None = None,
    input_schema: type | None = None,
    is_concurrency_safe: bool = True,
    is_read_only: bool = False,
    is_destructive: bool = False,
    interrupt_behavior: InterruptBehavior = InterruptBehavior.BLOCK,
    max_result_size_chars: int = 100_000,
    timeout_seconds: float = 30.0,
) -> BuiltTool:
    """Factory function para criar ferramentas com defaults inteligentes.

    Inspirado no buildTool() do Claude Code.

    Args:
        name: Nome único da ferramenta
        description: Descrição estática ou callable assíncrono
        callable: Função de execução assíncrona
        execute: Alias retrocompatível para callable
        input_schema: Schema de input (opcional)
        is_concurrency_safe: Se pode rodar em paralelo (default: True)
        is_read_only: Se não modifica estado (default: False)
        is_destructive: Se a operação altera estado de forma destrutiva
        interrupt_behavior: Como reagir a interrupções (default: BLOCK)
        max_result_size_chars: Tamanho máximo do resultado (default: 100_000)
        timeout_seconds: Timeout de execução (default: 30.0)

    Returns:
        BuiltTool configurada com defaults aplicados

    Example:
        ```python
        read_tool = build_tool(
            name="Read",
            description="Reads a file from the filesystem",
            callable=read_file_impl,
            is_concurrency_safe=True,
            is_read_only=True,
            interrupt_behavior=InterruptBehavior.CANCEL,
        )
        ```
    """
    tool_callable = callable or execute
    if tool_callable is None:
        raise ValueError(f"Tool '{name}' requires a callable or execute handler")

    return BuiltTool(
        name=name,
        description=description,
        callable=tool_callable,
        input_schema=input_schema,
        is_concurrency_safe=is_concurrency_safe,
        is_read_only=is_read_only,
        is_destructive=is_destructive,
        interrupt_behavior=interrupt_behavior,
        max_result_size_chars=max_result_size_chars,
        timeout_seconds=timeout_seconds,
    )


class ToolBuilder(Generic[TInput, TOutput]):
    """Builder fluente para criar ferramentas com múltiplas configurações.

    Alternativa ao build_tool() para casos mais complexos.

    Example:
        ```python
        tool = (
            ToolBuilder("MyTool")
            .with_description("Does something useful")
            .with_callable(my_impl)
            .concurrency_safe()
            .read_only()
            .with_timeout(60.0)
            .build()
        )
        ```
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._description: str | Callable[[], str | Awaitable[str]] = ""
        self._callable: ToolCallable | None = None
        self._input_schema: type | None = None
        self._is_concurrency_safe = True
        self._is_read_only = False
        self._is_destructive = False
        self._interrupt_behavior = InterruptBehavior.BLOCK
        self._max_result_size_chars = 100_000
        self._timeout_seconds = 30.0

    def with_description(
        self,
        description: str | Callable[[], str | Awaitable[str]],
    ) -> "ToolBuilder":
        """Define descrição da ferramenta."""
        self._description = description
        return self

    def with_callable(self, callable: ToolCallable) -> "ToolBuilder":
        """Define callable de execução."""
        self._callable = callable
        return self

    def with_input_schema(self, schema: type) -> "ToolBuilder":
        """Define schema de input."""
        self._input_schema = schema
        return self

    def concurrency_safe(self, safe: bool = True) -> "ToolBuilder":
        """Define se é concurrency-safe."""
        self._is_concurrency_safe = safe
        return self

    def read_only(self, readonly: bool = True) -> "ToolBuilder":
        """Define se é read-only."""
        self._is_read_only = readonly
        return self

    def destructive(self, destructive: bool = True) -> "ToolBuilder":
        """Define se a ferramenta é destrutiva."""
        self._is_destructive = destructive
        return self

    def with_interrupt_behavior(self, behavior: InterruptBehavior) -> "ToolBuilder":
        """Define comportamento de interrupção."""
        self._interrupt_behavior = behavior
        return self

    def with_max_result_size(self, size: int) -> "ToolBuilder":
        """Define tamanho máximo do resultado."""
        self._max_result_size_chars = size
        return self

    def with_timeout(self, seconds: float) -> "ToolBuilder":
        """Define timeout de execução."""
        self._timeout_seconds = seconds
        return self

    def build(self) -> BuiltTool:
        """Constrói ferramenta com configurações aplicadas.

        Returns:
            BuiltTool configurada

        Raises:
            ValueError: Se callable não foi definido
        """
        if self._callable is None:
            raise ValueError(f"Tool '{self._name}' requires a callable")

        return BuiltTool(
            name=self._name,
            description=self._description,
            callable=self._callable,
            input_schema=self._input_schema,
            is_concurrency_safe=self._is_concurrency_safe,
            is_read_only=self._is_read_only,
            is_destructive=self._is_destructive,
            interrupt_behavior=self._interrupt_behavior,
            max_result_size_chars=self._max_result_size_chars,
            timeout_seconds=self._timeout_seconds,
        )
