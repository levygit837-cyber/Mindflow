"""Streaming tool execution types for MindFlow backend.

Provides types for tracking tool execution status, concurrent-safe tools,
and streaming results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.schemas.tools.result import ToolResult


class ToolStatus(str, Enum):
    """Status de execução de uma ferramenta rastreada."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    DISCARDED = "discarded"


@dataclass
class TrackedTool:
    """Ferramenta rastreada pelo StreamingToolExecutor.
    
    Attributes:
        id: ID único da ferramenta (tool_use_id)
        tool_name: Nome da ferramenta
        tool_input: Input da ferramenta
        assistant_message: Mensagem do assistente que solicitou a tool
        status: Status atual da execução
        is_concurrency_safe: Se pode rodar em paralelo com outras tools
        result: Resultado da execução (quando completada)
        error: Erro de execução (quando falhou)
        started_at: Timestamp de início da execução
        completed_at: Timestamp de conclusão
        metadata: Metadados adicionais
    """
    
    id: str
    tool_name: str
    tool_input: dict[str, Any]
    assistant_message: Any = None  # AssistantMessage from langchain
    status: ToolStatus = ToolStatus.PENDING
    is_concurrency_safe: bool = True
    result: ToolResult | None = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_terminal(self) -> bool:
        """Verifica se a ferramenta está em estado terminal."""
        return self.status in {ToolStatus.COMPLETED, ToolStatus.ERROR, ToolStatus.DISCARDED}
    
    @property
    def is_running(self) -> bool:
        """Verifica se a ferramenta está em execução."""
        return self.status == ToolStatus.RUNNING
    
    @property
    def is_pending(self) -> bool:
        """Verifica se a ferramenta está pendente."""
        return self.status == ToolStatus.PENDING
    
    @property
    def execution_time_ms(self) -> int | None:
        """Retorna tempo de execução em milissegundos."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or time.time()
        return int((end_time - self.started_at) * 1000)
    
    def mark_running(self) -> None:
        """Marca ferramenta como em execução."""
        self.status = ToolStatus.RUNNING
        self.started_at = time.time()
    
    def mark_completed(self, result: ToolResult) -> None:
        """Marca ferramenta como completada."""
        self.status = ToolStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()
    
    def mark_error(self, error: str) -> None:
        """Marca ferramenta como falha."""
        self.status = ToolStatus.ERROR
        self.error = error
        self.completed_at = time.time()
    
    def mark_discarded(self) -> None:
        """Marca ferramenta como descartada."""
        self.status = ToolStatus.DISCARDED
        self.completed_at = time.time()
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "status": self.status.value,
            "is_concurrency_safe": self.is_concurrency_safe,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class StreamingToolResult:
    """Resultado de execução de uma ferramenta no contexto de streaming.
    
    Wrapper ao redor de ToolResult com informações adicionais
    de tracking e ordering.
    """
    
    tool_id: str
    tool_name: str
    status: ToolStatus
    result: ToolResult | None = None
    error: str | None = None
    execution_time_ms: int | None = None
    order: int = 0  # Ordem de chegada no executor
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "order": self.order,
        }


class AbortController:
    """Controller para abortar execuções de ferramentas.
    
    Inspirado no AbortController do JavaScript.
    Permite cancelar múltiplas tasks de forma coordenada.
    """
    
    def __init__(self, parent: AbortController | None = None) -> None:
        self._aborted = False
        self._reason: str | None = None
        self._parent = parent
        self._children: list[AbortController] = []
    
    @property
    def is_aborted(self) -> bool:
        """Verifica se foi abortado (incluindo pais)."""
        if self._aborted:
            return True
        if self._parent and self._parent.is_aborted:
            return True
        return False
    
    @property
    def reason(self) -> str | None:
        """Retorna razão do abort."""
        if self._reason:
            return self._reason
        if self._parent:
            return self._parent.reason
        return None
    
    def abort(self, reason: str = "Aborted") -> None:
        """Aborta este controller e todos os filhos."""
        self._aborted = True
        self._reason = reason
        # Propaga para filhos
        for child in self._children:
            child.abort(reason)
    
    def create_child(self) -> AbortController:
        """Cria um controller filho."""
        child = AbortController(parent=self)
        self._children.append(child)
        return child
    
    def remove_child(self, child: AbortController) -> None:
        """Remove um controller filho."""
        if child in self._children:
            self._children.remove(child)
    
    def check_or_raise(self) -> None:
        """Verifica se abortado e levanta exceção se sim."""
        if self.is_aborted:
            raise ToolExecutionAbortedError(self.reason or "Execution aborted")


class ToolExecutionAbortedError(Exception):
    """Exceção levantada quando execução é abortada."""
    
    def __init__(self, reason: str = "Execution aborted") -> None:
        self.reason = reason
        super().__init__(reason)


def create_child_abort_controller(parent: AbortController | None = None) -> AbortController:
    """Factory para criar AbortController filho."""
    if parent is None:
        return AbortController()
    return parent.create_child()