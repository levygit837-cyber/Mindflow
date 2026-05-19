# 🔌 Fase 1B — AgentCommunicationMixin: Injetando P2P nos Agentes

**Fase:** 1B | **Semana:** 2–3 | **Prioridade:** P0  
**PRD Base:** `docs/PRD/PRD-SPADE-Communication-Layer.md`  
**Depende de:** `1A` (CommunicationBus deve estar funcional)  
**Bloqueia:** `2B` (MissionLauncher usa `comm_bus` no `MissionContext`)  
**Paralelo a:** `1C` (CommRoles podem ser definidos ao mesmo tempo)

---

## 📋 Sumário

Criar o `AgentCommunicationMixin` — um objeto injetado nos agentes durante delegação para que eles possam enviar mensagens P2P sem conhecer a implementação do bus. Depois, estender o `DelegationEngine` para injetar o mixin automaticamente quando o bus estiver disponível.

O design é **opt-in e graceful-degrading**: se o bus não estiver disponível, o agente executa normalmente sem P2P.

---

## 🏗️ Arquitetura

```
DelegationEngine.delegate_task()
        │
        │ 1. get_agent(role, specialist)
        │ 2. SE bus disponível:
        ↓
 AgentCommunicationMixin(agent_id, bus)
        │
        │ injetado como agent.comm
        ↓
┌─────────────────────────────────────────┐
│        AgentCommunicationMixin          │
│                                         │
│  send_to(to, content, urgency)          │  ← P2P direto
│  request_from(to, content, timeout)     │  ← request/response
│  notify(to, event, data)                │  ← notificação assíncrona
│  broadcast_to_team(room_id, content)    │  ← team broadcast
│                                         │
│  [protegido por CommunicationBus]       │
└─────────────────────────────────────────┘
        │
        ↓
CommunicationBus.send() → InternalBus / XMPPBus
```

---

## 🎯 O Que Fazer

### Estado Atual
```
communication/
  ✅ bus/communication_bus.py     → CommunicationBus pronto (Fase 1A)
  ❌ mixins/                      → NÃO EXISTE — criar agora

orchestrator/delegation/
  ✅ engine.py                    → DelegationEngine funcional
  ❌ engine.py (inject comm mixin)→ MODIFICAR para injetar mixin
```

### O Que Criar/Modificar
```
communication/
  mixins/
    __init__.py                   ← CRIAR
    agent_communication.py        ← CRIAR: AgentCommunicationMixin

orchestrator/delegation/
  engine.py                       ← MODIFICAR: injetar mixin
```

---

## 🔧 Implementação Passo a Passo

### Passo 1 — Criar `communication/mixins/__init__.py`

```python
# communication/mixins/__init__.py
from .agent_communication import AgentCommunicationMixin

__all__ = ["AgentCommunicationMixin"]
```

**Arquivo:** `python/mindflow_backend/communication/mixins/__init__.py`

---

### Passo 2 — Criar `communication/mixins/agent_communication.py`

```python
# communication/mixins/agent_communication.py
"""
AgentCommunicationMixin — Capacidade de comunicação P2P injetada nos agentes.

Injetado pelo DelegationEngine durante delegate_task().
Agentes acessam via self.comm (ou agent.comm no contexto do engine).
Gracefully degrades: se bus não disponível, métodos retornam None/False sem erro.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mindflow_backend.communication.bus.communication_bus import CommunicationBus
from mindflow_backend.communication.protocols.p2p_protocol import (
    MessageType,
    P2PMessage,
)

logger = logging.getLogger(__name__)


class AgentCommunicationMixin:
    """
    Capacidade de comunicação P2P para agentes em execução.
    
    Injetado pelo DelegationEngine. Nunca instanciado diretamente pelo agente.
    Todos os métodos são gracefully degrading.
    """

    def __init__(self, agent_id: str, bus: CommunicationBus) -> None:
        self._agent_id = agent_id
        self._bus = bus
        self._messages_sent: int = 0
        self._messages_failed: int = 0

    # ------------------------------------------------------------------
    # API pública para uso pelos agentes
    # ------------------------------------------------------------------

    async def send_to(
        self,
        to_agent: str,
        content: str,
        urgency: str = "MEDIUM",
    ) -> bool:
        """
        Envia mensagem direta a outro agente.
        
        Retorna True se entregue, False se falhou ou bus unavailable.
        Não propaga exceção — sempre retorna.
        """
        if not self._bus.is_available:
            logger.debug("comm_send_skipped_no_bus", extra={"to": to_agent})
            return False

        msg = P2PMessage(
            from_agent=self._agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.DIRECT,
            urgency=urgency,
        )
        try:
            result = await self._bus.send(self._agent_id, to_agent, msg)
            if result:
                self._messages_sent += 1
                logger.debug(
                    "comm_sent",
                    extra={
                        "from": self._agent_id,
                        "to": to_agent,
                        "urgency": urgency,
                    },
                )
            else:
                self._messages_failed += 1
            return result
        except Exception as exc:
            logger.warning(
                "comm_send_error",
                extra={"to": to_agent, "error": str(exc)},
            )
            self._messages_failed += 1
            return False

    async def request_from(
        self,
        to_agent: str,
        content: str,
        timeout: float = 30.0,
    ) -> str | None:
        """
        Envia request e aguarda resposta com timeout.
        
        Retorna conteúdo da resposta ou None se timeout/falha.
        Nunca bloqueia além do timeout.
        """
        if not self._bus.is_available:
            logger.debug("comm_request_skipped_no_bus", extra={"to": to_agent})
            return None

        msg = P2PMessage(
            from_agent=self._agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.REQUEST,
            urgency="HIGH",
            requires_response=True,
        )

        try:
            sent = await self._bus.send(self._agent_id, to_agent, msg)
            if not sent:
                return None

            # Aguardar resposta na própria inbox com timeout
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                incoming = await self._bus.receive(
                    self._agent_id,
                    timeout=min(1.0, remaining),
                )
                if incoming and incoming.in_reply_to == msg.message_id:
                    logger.debug(
                        "comm_response_received",
                        extra={"from": to_agent, "msg_id": msg.message_id},
                    )
                    return incoming.content

            logger.warning(
                "comm_request_timeout",
                extra={"to": to_agent, "timeout": timeout},
            )
            return None

        except Exception as exc:
            logger.warning(
                "comm_request_error",
                extra={"to": to_agent, "error": str(exc)},
            )
            return None

    async def notify(
        self,
        to_agent: str,
        event: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Envia notificação fire-and-forget.
        
        Não aguarda resposta. Usado para progress updates ao Orchestrator.
        """
        if not self._bus.is_available:
            return

        import json

        payload = json.dumps({"event": event, "data": data or {}})
        msg = P2PMessage(
            from_agent=self._agent_id,
            to_agent=to_agent,
            content=payload,
            message_type=MessageType.NOTIFICATION,
            urgency="LOW",
            requires_response=False,
        )
        try:
            await self._bus.send(self._agent_id, to_agent, msg)
        except Exception as exc:
            logger.debug(
                "comm_notify_failed",
                extra={"to": to_agent, "event": event, "error": str(exc)},
            )

    async def broadcast_to_team(
        self,
        room_id: str,
        content: str,
    ) -> bool:
        """
        Envia mensagem para todos os membros do room/team.
        
        Retorna True se pelo menos 1 membro recebeu.
        """
        if not self._bus.is_available:
            return False

        from mindflow_backend.communication.teams.team_chat import TeamMessage

        team_msg = TeamMessage(
            team_id=room_id,
            sender_jid=self._agent_id,
            content=content,
        )
        try:
            return await self._bus.broadcast(self._agent_id, room_id, team_msg)
        except Exception as exc:
            logger.warning(
                "comm_broadcast_error",
                extra={"room_id": room_id, "error": str(exc)},
            )
            return False

    async def notify_progress(
        self,
        percentage: int,
        current_step: str = "",
    ) -> None:
        """
        Shortcut: notifica Orchestrator de progresso da missão.
        
        Uso: await agent.comm.notify_progress(60, "investigando módulo X")
        """
        await self.notify(
            to_agent="orchestrator",
            event="mission_progress",
            data={"pct": percentage, "step": current_step, "agent": self._agent_id},
        )

    def get_stats(self) -> dict[str, Any]:
        """Estatísticas de comunicação deste agente."""
        return {
            "agent_id": self._agent_id,
            "messages_sent": self._messages_sent,
            "messages_failed": self._messages_failed,
            "bus_available": self._bus.is_available,
        }
```

**Arquivo:** `python/mindflow_backend/communication/mixins/agent_communication.py`

---

### Passo 3 — Atualizar `communication/__init__.py`

```python
# Adicionar ao communication/__init__.py
from .mixins.agent_communication import AgentCommunicationMixin

# Adicionar no __all__:
# "AgentCommunicationMixin",
```

---

### Passo 4 — Modificar `DelegationEngine`

Injetar o mixin após instanciar o agente.

**Arquivo:** `python/mindflow_backend/orchestrator/delegation/engine.py`

```python
# orchestrator/delegation/engine.py

# ADICIONAR no __init__ do DelegationEngine:
from mindflow_backend.communication.bus.communication_bus import (
    CommunicationBus,
    get_communication_bus,
)

class DelegationEngine(ExecutionMemoryMixin):
    def __init__(self, *, execution_memory: Any | None = None):
        # ... código existente ...
        
        # NOVO: bus de comunicação (opcional, graceful degradation)
        self._comm_bus: CommunicationBus | None = None
        try:
            self._comm_bus = get_communication_bus()
        except Exception:
            pass  # Bus não disponível — continua sem P2P

    async def delegate_task(self, task: DelegationTask, ...) -> DelegationResult:
        # ... código existente até get_agent() ...
        
        agent = get_agent(task.agent_role or task.agent, specialist=task.specialist, ...)
        
        # NOVO: injetar capacidade de comunicação P2P
        if self._comm_bus and self._comm_bus.is_available:
            from mindflow_backend.communication.mixins.agent_communication import (
                AgentCommunicationMixin,
            )
            agent_id = task.agent_id or (
                f"{task.agent.value}:{task.specialist.value}"
                if task.specialist
                else task.agent.value
            )
            agent.comm = AgentCommunicationMixin(
                agent_id=agent_id,
                bus=self._comm_bus,
            )
            _logger.debug(
                "delegation_comm_injected",
                agent_id=agent_id,
                task_id=str(task.task_id),
            )
        
        # ... resto do código existente ...
```

> **Nota:** A injeção é condicional. Se `comm_bus` não existir ou não estiver disponível, `agent.comm` simplesmente não é setado — o agente executa normalmente sem P2P.

---

### Passo 5 — Atualizar `BaseAgent` para suportar `.comm`

Adicionar atributo opcional ao `BaseAgent`:

**Arquivo:** `python/mindflow_backend/agents/_base.py`

```python
# agents/_base.py — ADICIONAR ao BaseAgent

class BaseAgent:
    # ... campos existentes ...
    
    def __init__(self, ...):
        # ... init existente ...
        
        # NOVO: atributo de comunicação, injetado pelo DelegationEngine
        # TYPE: AgentCommunicationMixin | None
        self.comm = None
    
    @property
    def has_p2p(self) -> bool:
        """True se o agente tem capacidade de comunicação P2P ativa."""
        return self.comm is not None and self.comm._bus.is_available
```

---

## ✅ Checklist de Conclusão

### Semana 2 (Dias 1–3)
- [ ] Criar diretório `communication/mixins/`
- [ ] Criar `communication/mixins/__init__.py`
- [ ] Criar `communication/mixins/agent_communication.py`
  - [ ] `send_to()` implementado
  - [ ] `request_from()` com timeout implementado
  - [ ] `notify()` fire-and-forget implementado
  - [ ] `broadcast_to_team()` implementado
  - [ ] `notify_progress()` shortcut implementado
  - [ ] `get_stats()` implementado
- [ ] Atualizar `communication/__init__.py`

### Semana 2 (Dias 4–5) / Semana 3
- [ ] Adicionar `comm = None` ao `BaseAgent`
- [ ] Adicionar `has_p2p` property ao `BaseAgent`
- [ ] Modificar `DelegationEngine.__init__` para obter bus
- [ ] Modificar `DelegationEngine.delegate_task()` para injetar mixin
- [ ] Injeção é condicional — não quebra se bus unavailable

### Testes
- [ ] `test_agent_communication_mixin.py`
  - [ ] `test_send_to_success()`
  - [ ] `test_send_to_fails_gracefully_no_bus()`
  - [ ] `test_request_from_returns_response()`
  - [ ] `test_request_from_timeout_returns_none()`
  - [ ] `test_notify_progress_fires_and_forgets()`
  - [ ] `test_broadcast_to_team()`
- [ ] `test_delegation_engine_injects_comm()`
- [ ] `test_delegation_engine_without_bus_still_works()`

---

## 🧪 Como Testar Manualmente

```python
import asyncio
from mindflow_backend.communication.bus import InternalCommunicationBus
from mindflow_backend.communication.mixins import AgentCommunicationMixin

async def test():
    bus = InternalCommunicationBus()
    await bus.register_agent("coder")
    await bus.register_agent("analyst")
    
    coder_comm = AgentCommunicationMixin(agent_id="coder", bus=bus)
    analyst_comm = AgentCommunicationMixin(agent_id="analyst", bus=bus)
    
    # Handler no analyst para auto-responder
    from mindflow_backend.communication.protocols.p2p_protocol import P2PMessage, MessageType
    
    async def analyst_handler(msg: P2PMessage):
        if msg.message_type == MessageType.REQUEST:
            response = P2PMessage(
                from_agent="analyst",
                to_agent=msg.from_agent,
                content="Encontrei padrão Factory no módulo X",
                message_type=MessageType.RESPONSE,
                in_reply_to=msg.message_id,
            )
            await bus.send("analyst", msg.from_agent, response)
    
    await bus.subscribe("analyst", analyst_handler)
    
    # Coder faz request ao Analyst
    response = await coder_comm.request_from(
        to_agent="analyst",
        content="Que padrão usar para este módulo?",
        timeout=5.0,
    )
    print(f"Resposta do Analyst: {response}")
    
    # Notificação de progresso
    await coder_comm.notify_progress(75, "implementando método principal")
    
    print(f"Stats Coder: {coder_comm.get_stats()}")

asyncio.run(test())
```

---

## 📊 Métricas de Sucesso Desta Fase

| Métrica | Target |
|---|---|
| `request_from()` latência (internal bus) | < 200ms (inclui roundtrip) |
| Injeção do mixin não aumenta latência de delegação | < 5ms overhead |
| Agentes sem bus executam normalmente | 100% dos casos |
| `notify_progress()` não bloqueia execução | fire-and-forget < 1ms |

---

## ⚠️ Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| `request_from()` blocks agente indefinidamente | Timeout hard-coded + asyncio.wait_for() |
| `agent.comm` acessado antes de injeção | Property `has_p2p` + None check defensivo |
| Circular import: agent ↔ mixin ↔ bus | Imports lazy dentro dos métodos |
| Bus inicializado em thread errada | Singleton usa `asyncio.get_event_loop()` correto |
