# 🚀 Fase 2B — MissionLauncher: Orquestração de Missões Autônomas

**Fase:** 2B | **Semana:** 3–4 | **Prioridade:** P0  
**PRD Base:** `docs/PRD/PRD-Agent-Roles-Execution-Graphs.md`  
**Depende de:** `1A` (CommunicationBus), `1C` (MissionGraphType), `2A` (Execution Graphs)  
**Bloqueia:** `3A` (TeamOrchestrator usa MissionLauncher)  
**Paralelo a:** `1B` (pode ser desenvolvido depois de 1C/2A)

---

## 📋 Sumário

Criar o `MissionLauncher` — componente central que seleciona o execution graph correto dado um `agent_id` e um `mission_type`, instancia o `MissionContext` com todas as dependências e retorna um `MissionResult` estruturado. Depois, integrar o launcher ao `DelegationEngine` para que missões autônomas sejam lançadas automaticamente quando disponível.

O `MissionLauncher` é o elo entre o `Orchestrator` (que decide "analyst deve fazer análise de segurança") e o `AnalysisGraph` (que executa a missão de fato).

---

## 🏗️ Arquitetura

```
DelegationEngine.delegate_task()
        │
        ├─ task.mission_type disponível?
        │       │
        │      YES
        │       ↓
        │  MissionLauncher.launch_mission(agent_id, mission_type, task)
        │       │
        │       ├─ 1. Valida: agent pode executar este mission_type?
        │       ├─ 2. Cria MissionContext(agent_id, type, task, comm_bus)
        │       ├─ 3. GraphFactory.create_mission_graph(mission_type)
        │       ├─ 4. graph.execute(MissionContext)
        │       └─ 5. MissionResult(annotations, messages, duration)
        │
        └─ task.mission_type ausente?
                │
               YES
                ↓
           DelegationEngine._legacy_delegate()  ← comportamento atual
```

---

## 🎯 O Que Criar

```
execution/
  __init__.py                   ← CRIAR
  missions/
    __init__.py                 ← CRIAR
    mission_launcher.py         ← CRIAR: MissionLauncher
    mission_context.py          ← CRIAR: MissionContext
    mission_result.py           ← CRIAR: MissionResult

graphs/factory.py               ← MODIFICAR: adicionar create_mission_graph()
orchestrator/delegation/engine.py ← MODIFICAR: usar MissionLauncher
```

---

## 🔧 Implementação Passo a Passo

### Passo 1 — `execution/missions/mission_context.py`

```python
# execution/missions/mission_context.py
"""
MissionContext — Estado e dependências injetados em cada missão autônoma.

Passado ao execution graph como input state.
Contém: agent_id, tipo de missão, task, session, bus de comunicação.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


@dataclass
class MissionContext:
    """
    Contexto injetado no execution graph durante uma missão autônoma.
    
    Carrega tudo que o graph precisa: identidade do agente, tarefa, session,
    bus de comunicação e configurações de execução.
    """
    
    agent_id: str
    mission_type: MissionGraphType
    task: str
    session_id: str
    
    comm_bus: "CommunicationBus | None" = None
    """Bus de comunicação P2P — pode ser None se não disponível."""
    
    memory_scope: str = "universal"
    """Escopo de memória: 'universal' (compartilhada) ou 'local' (só para esta missão)."""
    
    parent_mission_id: str | None = None
    """ID da missão pai, se esta é sub-missão."""
    
    mission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Identificador único desta missão."""
    
    max_duration_seconds: float = 300.0
    """Timeout máximo da missão em segundos."""
    
    max_iterations: int = 500
    """Iterações máximas para graphs com loops."""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """Metadados extras injetados pelo orquestrador."""
    
    def to_graph_state(self) -> dict[str, Any]:
        """Converte para dict compatível com GraphState."""
        return {
            "agent_id": self.agent_id,
            "mission_id": self.mission_id,
            "mission_type": self.mission_type.value,
            "task": self.task,
            "session_id": self.session_id,
            "memory_scope": self.memory_scope,
            "max_iterations": self.max_iterations,
            "max_duration_seconds": self.max_duration_seconds,
            "iteration": 0,
            "confidence": 0.0,
            "annotations": [],
            "messages_sent": [],
            "comm_bus": self.comm_bus,
            **self.metadata,
        }
```

**Arquivo:** `python/mindflow_backend/execution/missions/mission_context.py`

---

### Passo 2 — `execution/missions/mission_result.py`

```python
# execution/missions/mission_result.py
"""
MissionResult — Resultado estruturado de uma missão autônoma.

Retornado pelo MissionLauncher após graph.execute() completar.
Inclui: resultado textual, anotações de memória, mensagens P2P enviadas.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mindflow_backend.communication.protocols.p2p_protocol import P2PMessage
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


@dataclass
class MemoryAnnotationRef:
    """Referência a anotação criada durante a missão."""
    content: str
    importance: float = 0.5
    iteration: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)


@dataclass
class MissionResult:
    """
    Resultado de uma missão autônoma.
    
    Retornado pelo MissionLauncher e passado ao DelegationEngine
    para ser convertido em DelegationResult.
    """
    
    agent_id: str
    mission_type: MissionGraphType
    mission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    success: bool = False
    result: str = ""
    """Conteúdo textual principal do resultado."""
    
    annotations: list[MemoryAnnotationRef] = field(default_factory=list)
    """Anotações gravadas na memória universal durante a missão."""
    
    messages_sent: list[dict[str, Any]] = field(default_factory=list)
    """Mensagens P2P enviadas durante a missão (serialized)."""
    
    duration_seconds: float = 0.0
    iterations: int = 0
    error: str | None = None
    
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_graph_state(
        cls,
        state: dict[str, Any],
        agent_id: str,
        mission_type: MissionGraphType,
        started_at: datetime,
    ) -> "MissionResult":
        """Cria MissionResult a partir do estado final do graph."""
        now = datetime.now()
        return cls(
            agent_id=agent_id,
            mission_type=mission_type,
            mission_id=state.get("mission_id", str(uuid.uuid4())),
            success=not bool(state.get("error")),
            result=state.get("report", state.get("result", "")),
            annotations=state.get("annotations", []),
            messages_sent=state.get("messages_sent", []),
            duration_seconds=(now - started_at).total_seconds(),
            iterations=state.get("iteration", 0),
            error=state.get("error"),
            started_at=started_at,
            completed_at=now,
        )
    
    def to_delegation_result_data(self) -> dict[str, Any]:
        """Converte para formato compatível com DelegationResult."""
        return {
            "result": self.result,
            "success": self.success,
            "error": self.error,
            "metadata": {
                "mission_id": self.mission_id,
                "mission_type": self.mission_type.value,
                "iterations": self.iterations,
                "duration_seconds": self.duration_seconds,
                "annotations_count": len(self.annotations),
                **self.metadata,
            },
        }
```

**Arquivo:** `python/mindflow_backend/execution/missions/mission_result.py`

---

### Passo 3 — `execution/missions/mission_launcher.py`

```python
# execution/missions/mission_launcher.py
"""
MissionLauncher — Seleciona, configura e lança execution graphs para missões.

Dado um agent_id e mission_type, instancia o graph correto,
prepara o MissionContext e retorna MissionResult.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, TYPE_CHECKING

from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.graphs.factory import get_graph_factory
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.communication import MissionGraphType

from .mission_context import MissionContext
from .mission_result import MissionResult

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus

_logger = get_logger(__name__)

# Mapping: MissionGraphType → GraphType string (para o factory)
_MISSION_TO_GRAPH_TYPE: dict[MissionGraphType, str] = {
    MissionGraphType.ANALYSIS: "analysis",
    MissionGraphType.DEEP_INVESTIGATION: "deep_investigation",
    MissionGraphType.SECURITY_AUDIT: "security_audit",
    MissionGraphType.CODE_REVIEW: "code_review",
    MissionGraphType.IDEATION: "analysis",              # reutiliza AnalysisGraph
    MissionGraphType.MULTI_PASS_ANALYSIS: "deep_investigation",
    MissionGraphType.VULNERABILITY_SCAN: "security_audit",
    MissionGraphType.EXPLORATION: "analysis",
    MissionGraphType.CODING_TASK: "coding_task",
    MissionGraphType.BUG_FIX: "bug_fix",
    MissionGraphType.REFACTOR: "refactor",
    MissionGraphType.IMPLEMENTATION: "coding_task",     # reutiliza CodingGraph
    MissionGraphType.ARCHITECTURE_DESIGN: "coding_task",
    MissionGraphType.STRUCTURAL_REFACTOR: "refactor",
    MissionGraphType.WEB_RESEARCH: "web_research",
    MissionGraphType.DOCUMENTATION_LOOKUP: "web_research",
    MissionGraphType.COMPARISON_ANALYSIS: "comparison",
}


class MissionLauncher:
    """
    Lança missões autônomas para agentes especializados.
    
    Valida que o agente pode executar o mission_type,
    cria o MissionContext com todas as dependências,
    e executa o execution graph correto.
    """

    def __init__(
        self,
        comm_bus: "CommunicationBus | None" = None,
    ) -> None:
        self._factory = get_graph_factory()
        self._comm_bus = comm_bus

    async def launch_mission(
        self,
        agent_id: str,
        mission_type: MissionGraphType,
        task: str,
        session_id: str,
        context: dict[str, Any] | None = None,
        max_duration_seconds: float = 300.0,
        max_iterations: int | None = None,
    ) -> MissionResult:
        """
        Lança uma missão autônoma para um agente.
        
        Args:
            agent_id: ID do agente (e.g. "analyst", "coder:arch_tech")
            mission_type: Tipo de missão (MissionGraphType enum)
            task: Descrição textual da tarefa
            session_id: ID da sessão pai
            context: Metadados extras injetados no MissionContext
            max_duration_seconds: Timeout da missão
            max_iterations: Override de iterações máximas
        
        Returns:
            MissionResult com resultado, anotações e métricas
        """
        
        started_at = datetime.now()
        
        # 1. Validar que o agente pode executar este mission_type
        try:
            policy = get_agent_runtime_policy(agent_id=agent_id)
        except KeyError:
            _logger.error("mission_unknown_agent", agent_id=agent_id)
            return self._error_result(agent_id, mission_type, "Unknown agent")
        
        if mission_type not in policy.available_mission_graphs:
            _logger.warning(
                "mission_type_not_available",
                agent_id=agent_id,
                mission_type=mission_type.value,
                available=[m.value for m in policy.available_mission_graphs],
            )
            return self._error_result(
                agent_id, mission_type,
                f"Agent {agent_id} cannot run {mission_type.value}",
            )
        
        # 2. Resolver GraphType
        graph_type_str = _MISSION_TO_GRAPH_TYPE.get(mission_type)
        if not graph_type_str:
            return self._error_result(agent_id, mission_type, "No graph mapped for mission_type")
        
        # 3. Criar MissionContext
        iterations = max_iterations or policy.max_iterations
        mission_ctx = MissionContext(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
            comm_bus=self._comm_bus,
            max_duration_seconds=max_duration_seconds,
            max_iterations=iterations,
            metadata=context or {},
        )
        
        _logger.info(
            "mission_launched",
            agent_id=agent_id,
            mission_type=mission_type.value,
            mission_id=mission_ctx.mission_id,
            session_id=session_id,
        )
        
        # 4. Criar graph e executar com timeout
        try:
            from mindflow_backend.graphs.base.types import GraphType
            graph_type_enum = GraphType(graph_type_str)
            graph = self._factory.create_graph(
                graph_type=graph_type_enum,
                graph_id=f"{mission_ctx.mission_id[:8]}_{graph_type_str}",
            )
            
            initial_state = mission_ctx.to_graph_state()
            
            async with asyncio.timeout(max_duration_seconds):
                final_state = await graph.execute(initial_state)
            
            result = MissionResult.from_graph_state(
                state=final_state,
                agent_id=agent_id,
                mission_type=mission_type,
                started_at=started_at,
            )
            
            _logger.info(
                "mission_completed",
                agent_id=agent_id,
                mission_id=mission_ctx.mission_id,
                success=result.success,
                duration=result.duration_seconds,
                iterations=result.iterations,
            )
            
            return result
        
        except TimeoutError:
            _logger.warning(
                "mission_timeout",
                agent_id=agent_id,
                mission_id=mission_ctx.mission_id,
                timeout=max_duration_seconds,
            )
            return self._error_result(
                agent_id, mission_type,
                f"Mission timed out after {max_duration_seconds}s",
            )
        
        except Exception as exc:
            _logger.error(
                "mission_failed",
                agent_id=agent_id,
                mission_type=mission_type.value,
                error=str(exc),
            )
            return self._error_result(agent_id, mission_type, str(exc))
        
        finally:
            # Cleanup: remover graph instance do factory após uso
            self._factory.remove_graph(f"{mission_ctx.mission_id[:8]}_{graph_type_str}")

    def can_agent_run(self, agent_id: str, mission_type: MissionGraphType) -> bool:
        """Verifica se o agente pode executar o tipo de missão."""
        try:
            policy = get_agent_runtime_policy(agent_id=agent_id)
            return mission_type in policy.available_mission_graphs
        except KeyError:
            return False

    @staticmethod
    def _error_result(
        agent_id: str,
        mission_type: MissionGraphType,
        error: str,
    ) -> MissionResult:
        return MissionResult(
            agent_id=agent_id,
            mission_type=mission_type,
            success=False,
            result="",
            error=error,
        )


# ---------------------------------------------------------------------------
# Singleton global
# ---------------------------------------------------------------------------

_global_launcher: MissionLauncher | None = None


def get_mission_launcher() -> MissionLauncher:
    """Retorna instância global do MissionLauncher."""
    global _global_launcher
    if _global_launcher is None:
        try:
            from mindflow_backend.communication.bus.communication_bus import (
                get_communication_bus,
            )
            _global_launcher = MissionLauncher(comm_bus=get_communication_bus())
        except Exception:
            _global_launcher = MissionLauncher(comm_bus=None)
    return _global_launcher
```

**Arquivo:** `python/mindflow_backend/execution/missions/mission_launcher.py`

---

### Passo 4 — `execution/missions/__init__.py` e `execution/__init__.py`

```python
# execution/missions/__init__.py
from .mission_launcher import MissionLauncher, get_mission_launcher
from .mission_context import MissionContext
from .mission_result import MissionResult, MemoryAnnotationRef

__all__ = [
    "MissionLauncher",
    "get_mission_launcher",
    "MissionContext",
    "MissionResult",
    "MemoryAnnotationRef",
]
```

```python
# execution/__init__.py
from .missions import MissionLauncher, MissionContext, MissionResult, get_mission_launcher

__all__ = [
    "MissionLauncher",
    "MissionContext",
    "MissionResult",
    "get_mission_launcher",
]
```

---

### Passo 5 — Integrar ao `DelegationEngine`

**Arquivo:** `python/mindflow_backend/orchestrator/delegation/engine.py`

```python
class DelegationEngine(ExecutionMemoryMixin):
    def __init__(self, *, execution_memory: Any | None = None):
        # ... código existente ...
        
        # NOVO: MissionLauncher (lazy, não bloqueia startup)
        self._mission_launcher: Any | None = None

    def _get_mission_launcher(self):
        if self._mission_launcher is None:
            try:
                from mindflow_backend.execution.missions import get_mission_launcher
                self._mission_launcher = get_mission_launcher()
            except Exception:
                pass
        return self._mission_launcher

    async def delegate_task(self, task: DelegationTask, ...) -> DelegationResult:
        
        # NOVO: verificar se task tem mission_type e launcher disponível
        launcher = self._get_mission_launcher()
        
        if (
            task.mission_type
            and launcher
            and launcher.can_agent_run(
                task.agent_id or task.agent.value,
                task.mission_type,
            )
        ):
            _logger.info(
                "delegation_using_mission_launcher",
                agent_id=task.agent_id or task.agent.value,
                mission_type=task.mission_type.value,
            )
            
            mission_result = await launcher.launch_mission(
                agent_id=task.agent_id or task.agent.value,
                mission_type=task.mission_type,
                task=task.objective,
                session_id=session_id or "unknown",
                context={"scope": list(task.scope or [])},
            )
            
            return DelegationResult(
                task_id=task.task_id,
                agent=task.agent,
                result=mission_result.result,
                success=mission_result.success,
                error=mission_result.error,
                metadata=mission_result.to_delegation_result_data()["metadata"],
            )
        
        # Fallback: comportamento existente de delegação
        return await self._legacy_delegate(task, ...)
```

> **Nota:** `DelegationTask` precisará de um campo opcional `mission_type: MissionGraphType | None = None`.

---

## ✅ Checklist de Conclusão

### Semana 3 (Dias 1–3)
- [ ] Criar `execution/__init__.py`
- [ ] Criar `execution/missions/__init__.py`
- [ ] Criar `execution/missions/mission_context.py`
  - [ ] Todos os campos definidos com defaults
  - [ ] `to_graph_state()` funcional
- [ ] Criar `execution/missions/mission_result.py`
  - [ ] `from_graph_state()` classmethod
  - [ ] `to_delegation_result_data()` funcional

### Semana 3–4 (Dias 4–7)
- [ ] Criar `execution/missions/mission_launcher.py`
  - [ ] Validação `can_agent_run()`
  - [ ] `launch_mission()` com timeout
  - [ ] Mapeamento `_MISSION_TO_GRAPH_TYPE` completo
  - [ ] Singleton `get_mission_launcher()`
  - [ ] Graceful degradation se graph não registrado
- [ ] Adicionar `mission_type: MissionGraphType | None` ao `DelegationTask`
- [ ] Integrar ao `DelegationEngine`

### Testes
- [ ] `test_mission_launcher.py`
  - [ ] `test_launch_analysis_mission()`
  - [ ] `test_launch_fails_if_agent_cannot_run_type()`
  - [ ] `test_launch_returns_error_on_timeout()`
  - [ ] `test_delegation_engine_uses_launcher_when_mission_type_set()`
  - [ ] `test_delegation_engine_fallback_when_no_launcher()`

---

## 📊 Métricas de Sucesso

| Métrica | Target |
|---|---|
| `MissionLauncher.can_agent_run()` | 100% de acurácia vs. RuntimePolicy |
| Timeout não propaga exceção | `MissionResult.success=False` retornado |
| Fallback ao legacy delegate funciona | 100% dos casos sem mission_type |
| Graph cleanup após missão | `factory.remove_graph()` chamado em `finally` |
