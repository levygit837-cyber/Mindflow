# 🧠 Fase 3B — Memory Observer: Anotação Contínua em Tempo Real

**Fase:** 3B | **Semana:** 7–8 | **Prioridade:** P1  
**PRD Base:** `docs/PRD/PRD-Team-Protocol-Collaborative-Missions.md`  
**Depende de:** `3A` (TeamSession deve existir), `1A` (CommunicationBus)  
**Bloqueia:** Nada — última fase antes de 4  
**Paralelo a:** Nada nesta fase

---

## 📋 Sumário

Implementar o padrão **Memory Observer**: agentes com `can_observe=True` (conforme `AgentRuntimePolicy`) monitoram execuções em andamento de outros agentes e anotam a memória universal com insights importantes em tempo real. O agente em modo observer nunca bloqueia — apenas escuta e escreve.

Isso cria inteligência cumulativa: cada missão enriquece a memória para sessões futuras.

---

## 🏗️ Arquitetura

```
TeamSession — Phase MISSIONS
│
├── Researcher → ACTIVE (executa ResearchGraph)
│       │ eventos → AgentLogBus
│       │               ↓
├── Analyst → OBSERVER (concluiu AnalysisGraph)
│       │   Assina AgentLogBus do Researcher
│       │   is_important(evento)?
│       │     YES → memory.save_annotation()
│       │     NO  → ignora
│
└── Coder → ACTIVE (executa CodingGraph)
        │ eventos → AgentLogBus
        │               ↓
        Orchestrator → OBSERVER (monitora todos)
                    → anota insights de alto nível
```

---

## 🎯 O Que Criar

```
execution/observers/
  __init__.py               ← CRIAR
  memory_observer.py        ← CRIAR: MemoryObserver

schemas/memory/
  annotation.py             ← CRIAR: MemoryAnnotation

memory/facade.py            ← MODIFICAR: adicionar save_annotation()
runtime/monitoring/log_bus.py ← VERIFICAR: precisa de subscribe por mission_id
```

---

## 🔧 Implementação Passo a Passo

### Passo 1 — `schemas/memory/annotation.py`

```python
# schemas/memory/annotation.py
"""
MemoryAnnotation — Schema para anotações de memória universal criadas por observers.

Diferente de memory saves normais: anotações têm importance score,
source_agent_id (quem gerou o evento original) e observer_agent_id (quem anotou).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryAnnotation:
    """
    Anotação de memória criada por um agente em modo observer.
    
    Salva na memória universal com contexto de quem observou + quem gerou.
    """
    
    annotation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    observer_agent_id: str = ""
    """Agente que criou a anotação (estava em modo OBSERVER)."""
    
    source_agent_id: str = ""
    """Agente cujo evento gerou a anotação."""
    
    mission_id: str = ""
    """ID da missão sendo observada."""
    
    session_id: str = ""
    """ID da sessão pai."""
    
    content: str = ""
    """Conteúdo da anotação — interpretação do observer sobre o evento."""
    
    raw_event_type: str = ""
    """Tipo do evento original (e.g. 'tool_result', 'agent_decision')."""
    
    importance: float = 0.5
    """Score 0.0–1.0. Anotações com importance < 0.3 são filtradas."""
    
    annotation_type: str = "observation"
    """Categoria: 'observation' | 'finding' | 'warning' | 'insight'"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    
    def to_memory_content(self) -> str:
        """Formata para salvar na memória universal."""
        return (
            f"[Observer: {self.observer_agent_id}] "
            f"[Source: {self.source_agent_id}] "
            f"[Type: {self.annotation_type}] "
            f"{self.content}"
        )
    
    def is_significant(self) -> bool:
        """True se deve ser salva (acima do threshold de importância)."""
        return self.importance >= 0.3


IMPORTANCE_THRESHOLDS = {
    "observation": 0.3,
    "finding": 0.5,
    "warning": 0.7,
    "insight": 0.4,
}

EVENT_IMPORTANCE_MAP = {
    "tool_result": 0.4,
    "agent_decision": 0.6,
    "mission_complete": 0.8,
    "finding": 0.7,
    "error": 0.9,
    "WARNING": 0.8,
    "progress": 0.2,
    "debug": 0.1,
}
```

**Arquivo:** `python/mindflow_backend/schemas/memory/annotation.py`

---

### Passo 2 — `execution/observers/memory_observer.py`

```python
# execution/observers/memory_observer.py
"""
MemoryObserver — Agente em modo passivo que monitora missões e anota memória.

Ativado quando agente com can_observe=True conclui sua missão em uma TeamSession.
Nunca bloqueia execução — apenas escuta AgentLogBus e grava anotações significativas.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

from mindflow_backend.schemas.memory.annotation import (
    MemoryAnnotation,
    EVENT_IMPORTANCE_MAP,
    IMPORTANCE_THRESHOLDS,
)

if TYPE_CHECKING:
    from mindflow_backend.memory.facade import MemoryService

_logger = logging.getLogger(__name__)

ANNOTATION_RATE_LIMIT = 10
"""Máximo de anotações por minuto por observer."""


class MemoryObserver:
    """
    Monitor passivo que anota memória durante execução de outros agentes.
    
    Roda em background (asyncio task).
    Nunca bloqueia o agente sendo observado.
    Filtro de importância: só anota eventos com score >= threshold.
    """

    def __init__(
        self,
        observer_agent_id: str,
        memory_service: "MemoryService",
        session_id: str,
    ) -> None:
        self._observer_id = observer_agent_id
        self._memory = memory_service
        self._session_id = session_id
        self._running = False
        self._task: asyncio.Task | None = None
        self._annotations_count = 0
        self._annotations_this_minute = 0
        self._observed_missions: set[str] = set()
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    async def start_observing(
        self,
        mission_ids: list[str],
    ) -> None:
        """
        Inicia observação em background de uma ou mais missões.
        
        Retorna imediatamente — observação ocorre em asyncio Task separada.
        """
        self._observed_missions.update(mission_ids)
        self._running = True
        self._task = asyncio.create_task(
            self._observation_loop(),
            name=f"observer_{self._observer_id}",
        )
        _logger.info(
            "observer_started",
            observer=self._observer_id,
            missions=mission_ids,
        )

    async def stop_observing(self) -> None:
        """Para a observação gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        _logger.info(
            "observer_stopped",
            observer=self._observer_id,
            total_annotations=self._annotations_count,
        )

    async def receive_event(self, event: dict[str, Any]) -> None:
        """
        Recebe evento do AgentLogBus.
        
        Chamado pelo AgentLogBus quando há evento nas missões observadas.
        Enfileira para processamento assíncrono.
        """
        if not self._running:
            return
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            _logger.debug("observer_queue_full", observer=self._observer_id)

    async def _observation_loop(self) -> None:
        """Loop principal de processamento de eventos."""
        rate_limit_reset_task = asyncio.create_task(self._rate_limit_reset_loop())
        
        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0,
                    )
                    await self._process_event(event)
                except TimeoutError:
                    continue
                except Exception as exc:
                    _logger.debug("observer_event_error", error=str(exc))
        finally:
            rate_limit_reset_task.cancel()

    async def _process_event(self, event: dict[str, Any]) -> None:
        """Processa um evento e anota memória se relevante."""
        # Rate limiting
        if self._annotations_this_minute >= ANNOTATION_RATE_LIMIT:
            return
        
        importance = self._score_importance(event)
        if importance < 0.3:
            return
        
        annotation_type = self._classify_event(event)
        threshold = IMPORTANCE_THRESHOLDS.get(annotation_type, 0.3)
        if importance < threshold:
            return
        
        content = self._summarize_event(event)
        if not content:
            return
        
        annotation = MemoryAnnotation(
            observer_agent_id=self._observer_id,
            source_agent_id=event.get("agent_id", ""),
            mission_id=event.get("mission_id", ""),
            session_id=self._session_id,
            content=content,
            raw_event_type=event.get("type", ""),
            importance=importance,
            annotation_type=annotation_type,
            tags=self._extract_tags(event),
        )
        
        if not annotation.is_significant():
            return
        
        try:
            await self._memory.save_annotation(annotation)
            self._annotations_count += 1
            self._annotations_this_minute += 1
            _logger.debug(
                "observer_annotated",
                observer=self._observer_id,
                type=annotation_type,
                importance=importance,
            )
        except Exception as exc:
            _logger.debug("observer_save_failed", error=str(exc))

    def _score_importance(self, event: dict[str, Any]) -> float:
        """Calcula score de importância do evento (0.0–1.0)."""
        event_type = event.get("type", "")
        level = event.get("level", "INFO")
        
        base_score = EVENT_IMPORTANCE_MAP.get(event_type, 0.2)
        
        # Boosts
        if level == "ERROR":
            base_score = max(base_score, 0.9)
        elif level == "WARNING":
            base_score = max(base_score, 0.7)
        
        if event.get("iteration", 1) > 10:
            base_score *= 0.8  # Eventos tardios têm menos novidade
        
        return min(base_score, 1.0)

    @staticmethod
    def _classify_event(event: dict[str, Any]) -> str:
        """Classifica evento em tipo de anotação."""
        event_type = event.get("type", "")
        level = event.get("level", "INFO")
        
        if level in ("ERROR", "WARNING"):
            return "warning"
        if event_type in ("agent_decision", "finding"):
            return "finding"
        if event_type == "mission_complete":
            return "insight"
        return "observation"

    @staticmethod
    def _summarize_event(event: dict[str, Any]) -> str:
        """Gera resumo textual do evento para memória."""
        agent_id = event.get("agent_id", "unknown")
        event_type = event.get("type", "event")
        message = event.get("message", "")
        data = event.get("data", {})
        
        if not message and not data:
            return ""
        
        summary = f"{agent_id} [{event_type}]: {message}"
        if data and isinstance(data, dict):
            key_data = {
                k: v for k, v in data.items()
                if k in ("result", "finding", "error", "file", "pattern")
            }
            if key_data:
                summary += f" | {key_data}"
        
        return summary[:500]  # Máximo 500 chars por anotação

    @staticmethod
    def _extract_tags(event: dict[str, Any]) -> list[str]:
        tags = []
        if event.get("type"):
            tags.append(f"event:{event['type']}")
        if event.get("agent_id"):
            tags.append(f"agent:{event['agent_id']}")
        if event.get("level") in ("ERROR", "WARNING"):
            tags.append(event["level"].lower())
        return tags

    async def _rate_limit_reset_loop(self) -> None:
        """Reseta contador de rate limit a cada 60s."""
        while True:
            await asyncio.sleep(60)
            self._annotations_this_minute = 0

    def get_stats(self) -> dict[str, Any]:
        return {
            "observer_id": self._observer_id,
            "running": self._running,
            "total_annotations": self._annotations_count,
            "rate_this_minute": self._annotations_this_minute,
            "observed_missions": list(self._observed_missions),
        }
```

**Arquivo:** `python/mindflow_backend/execution/observers/memory_observer.py`

---

### Passo 3 — Extensão de `memory/facade.py`

Adicionar `save_annotation()` ao facade de memória existente:

```python
# memory/facade.py — ADICIONAR método

async def save_annotation(self, annotation: "MemoryAnnotation") -> None:
    """
    Salva anotação de observer na memória universal.
    
    Usa o sistema de memória existente (agent_memory ou task_memory)
    com tags especiais para identificação de anotações de observers.
    """
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation
    
    if not annotation.is_significant():
        return
    
    content = annotation.to_memory_content()
    
    # Reutiliza o sistema existente de memory save
    await self.save_memory(
        content=content,
        session_id=annotation.session_id,
        agent_id=annotation.observer_agent_id,
        memory_type="annotation",
        metadata={
            "annotation_id": annotation.annotation_id,
            "source_agent": annotation.source_agent_id,
            "mission_id": annotation.mission_id,
            "importance": annotation.importance,
            "annotation_type": annotation.annotation_type,
            "tags": annotation.tags,
        },
    )
```

---

### Passo 4 — Integrar ao `TeamOrchestrator`

No `_phase_missions()` do `TeamOrchestrator`, ativar observers após cada agente completar:

```python
# execution/teams/team_orchestrator.py — na _phase_missions()

async def _start_observer_for_completed_agent(
    self,
    completed_agent_id: str,
    session: TeamSession,
    active_mission_ids: list[str],
) -> MemoryObserver | None:
    """Ativa modo observer para agente que completou sua missão."""
    
    from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver
    
    try:
        policy = get_agent_runtime_policy(agent_id=completed_agent_id)
        if not policy.can_observe:
            return None
        
        from mindflow_backend.memory import get_memory_service
        observer = MemoryObserver(
            observer_agent_id=completed_agent_id,
            memory_service=get_memory_service(),
            session_id=session.session_id,
        )
        await observer.start_observing(active_mission_ids)
        return observer
    except Exception as exc:
        _logger.debug("observer_start_failed", agent_id=completed_agent_id, error=str(exc))
        return None
```

---

### Passo 5 — Conectar `AgentLogBus` ao `MemoryObserver`

**Arquivo:** `python/mindflow_backend/runtime/monitoring/log_bus.py`

Verificar se o `AgentLogBus` existente suporta subscription por `mission_id`. Se não, adicionar:

```python
# runtime/monitoring/log_bus.py — ADICIONAR se necessário

class AgentLogBus:
    # ... código existente ...
    
    # ADICIONAR:
    _mission_observers: dict[str, list["MemoryObserver"]] = {}
    
    def subscribe_to_mission(
        self,
        mission_id: str,
        observer: "MemoryObserver",
    ) -> None:
        """Registra observer para receber eventos de uma missão."""
        if mission_id not in self._mission_observers:
            self._mission_observers[mission_id] = []
        self._mission_observers[mission_id].append(observer)
    
    async def _emit_to_observers(
        self,
        event: dict[str, Any],
        mission_id: str,
    ) -> None:
        """Emite evento aos observers registrados para esta missão."""
        observers = self._mission_observers.get(mission_id, [])
        for observer in observers:
            await observer.receive_event(event)
```

---

## ✅ Checklist de Conclusão

### Semana 7 (Dias 1–3)
- [ ] Criar `schemas/memory/annotation.py`
  - [ ] `MemoryAnnotation` dataclass
  - [ ] `EVENT_IMPORTANCE_MAP` e `IMPORTANCE_THRESHOLDS`
  - [ ] `is_significant()` funcional
- [ ] Criar `execution/observers/__init__.py`
- [ ] Criar `execution/observers/memory_observer.py`
  - [ ] `start_observing()` cria asyncio Task em background
  - [ ] `stop_observing()` cancela gracefully
  - [ ] `receive_event()` enfileira sem bloquear
  - [ ] `_observation_loop()` processa fila

### Semana 7–8 (Dias 4–10)
- [ ] Implementar `_score_importance()` com EVENT_IMPORTANCE_MAP
- [ ] Implementar rate limiting (10 anotações/min)
- [ ] Adicionar `save_annotation()` ao `memory/facade.py`
- [ ] Integrar `MemoryObserver` ao `TeamOrchestrator._phase_missions()`
- [ ] Verificar/estender `AgentLogBus` com subscription por mission_id
- [ ] Conectar `log_bus.subscribe_to_mission()` ao `MemoryObserver`

### Testes
- [ ] `test_memory_observer_starts_in_background()`
- [ ] `test_memory_observer_filters_low_importance()`
- [ ] `test_memory_observer_rate_limit()`
- [ ] `test_memory_annotation_is_significant()`
- [ ] `test_memory_facade_save_annotation()`
- [ ] `test_observer_stops_gracefully()`
- [ ] `test_team_orchestrator_activates_observer_after_mission()`

---

## 🧪 Teste Manual

```python
import asyncio
from execution.observers.memory_observer import MemoryObserver
from schemas.memory.annotation import MemoryAnnotation

class MockMemoryService:
    annotations = []
    async def save_annotation(self, ann):
        self.annotations.append(ann)
        print(f"✅ Anotação: [{ann.annotation_type}] {ann.content[:80]}")

async def test():
    memory = MockMemoryService()
    observer = MemoryObserver(
        observer_agent_id="analyst",
        memory_service=memory,
        session_id="test-session",
    )
    
    await observer.start_observing(["mission-123"])
    
    # Simular eventos
    events = [
        {"type": "tool_result", "agent_id": "coder", "mission_id": "mission-123",
         "level": "INFO", "message": "File auth.py modified", "data": {"file": "auth.py"}},
        {"type": "finding", "agent_id": "coder", "mission_id": "mission-123",
         "level": "WARNING", "message": "SQL injection pattern detected"},
        {"type": "progress", "agent_id": "coder", "mission_id": "mission-123",
         "level": "DEBUG", "message": "Step 3/10"},  # baixa importância — filtrado
    ]
    
    for event in events:
        await observer.receive_event(event)
    
    await asyncio.sleep(0.5)
    await observer.stop_observing()
    
    print(f"\nTotal anotações: {len(memory.annotations)}")
    print(f"(Esperado: 2 — progress é filtrado por importância baixa)")
    print(f"\nStats: {observer.get_stats()}")

asyncio.run(test())
```

---

## 📊 Métricas de Sucesso

| Métrica | Target |
|---|---|
| Eventos de baixa importância filtrados | ≥ 40% (debug/progress) |
| Rate limit respeitado | ≤ 10 anotações/min/observer |
| Observer não bloqueia agente executando | Confirmado por timing test |
| Anotações salvas na memória universal | Verificado via memory.get_annotations() |
| Observer para gracefully no stop | 100% dos testes |

---

## ⚠️ Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| Memory annotation flood | Rate limit 10/min + importance threshold 0.3 |
| Observer queue overflow | `maxsize=500` + `put_nowait()` descarta se cheio |
| Memory service não suporta `save_annotation()` | Fallback: usa `save_memory()` existente |
| `AgentLogBus` não tem subscription por mission_id | Adicionar minimal support (5 linhas) |
| Observer task não é coletada pelo GC | `asyncio.Task` referenciada em `TeamSession.observers` |
