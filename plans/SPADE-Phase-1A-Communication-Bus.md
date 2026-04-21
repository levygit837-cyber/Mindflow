# 🚌 Fase 1A — CommunicationBus: Camada de Transporte Abstrata

# 🚌 Fase 1A — CommunicationBus: Camada de Transporte Abstrata

# 🚌 Fase 1A — CommunicationBus: Camada de Transporte Abstrata

**Fase:** 1A | **Semana:** 1–2 | **Prioridade:** P0  
**PRD Base:** `docs/PRD/PRD-SPADE-Communication-Layer.md`  
**Dependências:** Nenhuma — pode iniciar imediatamente  
**Bloqueado por:** Nada  
**Próximos planos desbloqueados:** 1B (AgentCommunicationMixin)

---

## 📋 Sumário

Criar a camada de abstração `CommunicationBus` que unifica o transporte de mensagens entre agentes. A implementação padrão usa **asyncio queues internas** (zero infra externa) com suporte a troca futura para ejabberd. O módulo `communication/` já tem os protocolos — falta a camada de orquestração e o registro de agentes no startup.

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    CommunicationBus (Abstract)               │
├─────────────────────────────────────────────────────────────┤
│  send(from, to, message)  │  broadcast(from, room, msg)      │
│  subscribe(agent, handler)│  register_agent(agent_id)        │
│  health_check()           │  unregister_agent(agent_id)      │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┴────────────┐
    │                       │
┌───┴──────────┐   ┌────────┴──────────┐
│ InternalBus  │   │  XMPPBus (Fase 4) │
│ (asyncio)    │   │  (ejabberd)       │
│ Zero infra   │   │  External server  │
└──────────────┘   └───────────────────┘
        │
        │  Protegido por
        ↓
┌──────────────┐
│CircuitBreaker│  ← já existe em communication/circuit_breaker/
└──────────────┘
```

---

## 🎯 O Que Fazer

### Estado Atual

```
communication/
  ✅ protocols/p2p_protocol.py    → P2PProtocol implementado
  ✅ protocols/xmpp_protocol.py   → XMPPProtocol implementado
  ✅ circuit_breaker/breaker.py   → CircuitBreaker implementado
  ✅ connection/xmpp_connection.py → XMPPConnectionManager (aioxmpp)
  ✅ services/p2p_service.py      → P2PService (alto nível)
  ❌ bus/                         → NÃO EXISTE — criar agora
```

### O Que Criar

```
communication/
  bus/
    __init__.py                   ← CRIAR
    communication_bus.py          ← CRIAR: abstract + InternalBus
```

---

## 🔧 Implementação Passo a Passo

### Passo 1 — Criar `communication/bus/__init__.py`

Arquivo de exports do módulo bus.

```python
# communication/bus/__init__.py
from .communication_bus import (
    CommunicationBus,
    InternalCommunicationBus,
    get_communication_bus,
)

__all__ = [
    "CommunicationBus",
    "InternalCommunicationBus",
    "get_communication_bus",
]
```

**Arquivo:** `python/mindflow_backend/communication/bus/__init__.py`

---

### Passo 2 — Criar `communication/bus/communication_bus.py`

O coração desta fase: abstract base + implementação interna com asyncio.

```python
# communication/bus/communication_bus.py
"""
CommunicationBus — Camada de transporte unificada para mensagens entre agentes.

Abstract base + InternalCommunicationBus (asyncio queues, zero infra externa).
XMPPCommunicationBus será implementado na Fase 4.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from mindflow_backend.communication.protocols.p2p_protocol import (
    MessageType,
    P2PMessage,
)
from mindflow_backend.communication.teams.team_chat import TeamMessage

logger = logging.getLogger(__name__)


class CommunicationBus(ABC):
    """
    Camada de transporte abstrata para mensagens entre agentes.
    
    Permite trocar InternalBus por XMPPBus sem alterar código dos agentes.
    """

    @abstractmethod
    async def register_agent(self, agent_id: str) -> None:
        """Registra um agente no bus (cria sua inbox)."""

    @abstractmethod
    async def unregister_agent(self, agent_id: str) -> None:
        """Remove agente do bus."""

    @abstractmethod
    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message: P2PMessage,
    ) -> bool:
        """Envia mensagem P2P. Retorna True se entregue."""

    @abstractmethod
    async def broadcast(
        self,
        from_agent: str,
        room_id: str,
        message: TeamMessage,
    ) -> bool:
        """Envia mensagem para room MUC. Retorna True se entregue."""

    @abstractmethod
    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[P2PMessage], Awaitable[None]],
    ) -> None:
        """Registra handler assíncrono para mensagens recebidas pelo agente."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Retorna status do bus."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True se o bus está operacional."""


class InternalCommunicationBus(CommunicationBus):
    """
    CommunicationBus baseado em asyncio.Queue — zero dependência externa.
    
    Cada agente tem sua própria inbox (Queue).
    Mensagens têm TTL de 30s para evitar acúmulo.
    """

    TTL_SECONDS: float = 30.0
    MAX_QUEUE_SIZE: int = 100

    def __init__(self) -> None:
        self._inboxes: dict[str, asyncio.Queue[P2PMessage]] = {}
        self._room_subscribers: dict[str, list[str]] = {}
        self._handlers: dict[str, list[Callable]] = {}
        self._running = True
        self._stats = {
            "messages_sent": 0,
            "messages_dropped": 0,
            "agents_registered": 0,
        }

    async def register_agent(self, agent_id: str) -> None:
        if agent_id not in self._inboxes:
            self._inboxes[agent_id] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
            self._handlers[agent_id] = []
            self._stats["agents_registered"] += 1
            logger.info("bus_agent_registered", extra={"agent_id": agent_id})

    async def unregister_agent(self, agent_id: str) -> None:
        self._inboxes.pop(agent_id, None)
        self._handlers.pop(agent_id, None)
        logger.info("bus_agent_unregistered", extra={"agent_id": agent_id})

    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message: P2PMessage,
    ) -> bool:
        inbox = self._inboxes.get(to_agent)
        if inbox is None:
            logger.warning(
                "bus_send_no_inbox",
                extra={"from": from_agent, "to": to_agent},
            )
            self._stats["messages_dropped"] += 1
            return False

        try:
            inbox.put_nowait(message)
            self._stats["messages_sent"] += 1
            logger.debug(
                "bus_message_sent",
                extra={
                    "from": from_agent,
                    "to": to_agent,
                    "msg_id": message.message_id,
                },
            )
            await self._dispatch_handlers(to_agent, message)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "bus_queue_full",
                extra={"agent_id": to_agent},
            )
            self._stats["messages_dropped"] += 1
            return False

    async def broadcast(
        self,
        from_agent: str,
        room_id: str,
        message: TeamMessage,
    ) -> bool:
        subscribers = self._room_subscribers.get(room_id, [])
        if not subscribers:
            logger.warning("bus_broadcast_no_subscribers", extra={"room_id": room_id})
            return False

        delivered = 0
        for agent_id in subscribers:
            if agent_id == from_agent:
                continue
            p2p_msg = P2PMessage(
                from_agent=from_agent,
                to_agent=agent_id,
                content=message.content,
                message_type=MessageType.DIRECT,
                metadata={"room_id": room_id, "team_message_id": message.message_id},
            )
            if await self.send(from_agent, agent_id, p2p_msg):
                delivered += 1

        return delivered > 0

    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[P2PMessage], Awaitable[None]],
    ) -> None:
        if agent_id not in self._handlers:
            self._handlers[agent_id] = []
        self._handlers[agent_id].append(handler)

    def join_room(self, agent_id: str, room_id: str) -> None:
        """Adiciona agente a um room MUC (para broadcast)."""
        if room_id not in self._room_subscribers:
            self._room_subscribers[room_id] = []
        if agent_id not in self._room_subscribers[room_id]:
            self._room_subscribers[room_id].append(agent_id)

    def leave_room(self, agent_id: str, room_id: str) -> None:
        """Remove agente de um room MUC."""
        if room_id in self._room_subscribers:
            self._room_subscribers[room_id] = [
                a for a in self._room_subscribers[room_id] if a != agent_id
            ]

    async def receive(
        self,
        agent_id: str,
        timeout: float = 1.0,
    ) -> P2PMessage | None:
        """Recebe próxima mensagem da inbox do agente (non-blocking com timeout)."""
        inbox = self._inboxes.get(agent_id)
        if inbox is None:
            return None
        try:
            return await asyncio.wait_for(inbox.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def health_check(self) -> dict[str, Any]:
        return {
            "type": "internal",
            "available": self._running,
            "agents": list(self._inboxes.keys()),
            "rooms": {
                room_id: len(subs)
                for room_id, subs in self._room_subscribers.items()
            },
            "stats": self._stats.copy(),
        }

    @property
    def is_available(self) -> bool:
        return self._running

    async def _dispatch_handlers(
        self,
        agent_id: str,
        message: P2PMessage,
    ) -> None:
        for handler in self._handlers.get(agent_id, []):
            try:
                await handler(message)
            except Exception as exc:
                logger.error(
                    "bus_handler_error",
                    extra={"agent_id": agent_id, "error": str(exc)},
                )


# ---------------------------------------------------------------------------
# Singleton global
# ---------------------------------------------------------------------------

_global_bus: CommunicationBus | None = None


def get_communication_bus() -> CommunicationBus:
    """Retorna a instância global do CommunicationBus."""
    global _global_bus
    if _global_bus is None:
        _global_bus = InternalCommunicationBus()
        logger.info("communication_bus_initialized", extra={"type": "internal"})
    return _global_bus


def set_communication_bus(bus: CommunicationBus) -> None:
    """Substitui o bus global (para testes ou migração para XMPPBus)."""
    global _global_bus
    _global_bus = bus
    logger.info("communication_bus_replaced", extra={"type": type(bus).__name__})
```

**Arquivo:** `python/mindflow_backend/communication/bus/communication_bus.py`

---

### Passo 3 — Atualizar `communication/__init__.py`

Adicionar exports do bus.

```python
# communication/__init__.py — ADICIONAR ao final dos imports existentes
from .bus.communication_bus import (
    CommunicationBus,
    InternalCommunicationBus,
    get_communication_bus,
    set_communication_bus,
)

# Adicionar no __all__:
# "CommunicationBus",
# "InternalCommunicationBus",
# "get_communication_bus",
# "set_communication_bus",
```

**Arquivo:** `python/mindflow_backend/communication/__init__.py`

---

### Passo 4 — Registrar agentes no startup

```python
# runtime/core/agent_runtime.py — no __init__ ou método de startup

async def _initialize_communication_bus(self) -> None:
    """Registra todos os agentes conhecidos no CommunicationBus."""
    try:
        from mindflow_backend.agents.specialists.runtime_policy import (
            list_agent_runtime_policies,
        )
        from mindflow_backend.communication.bus import get_communication_bus

        bus = get_communication_bus()
        for policy in list_agent_runtime_policies():
            await bus.register_agent(policy.agent_id)
        logger.info(
            "communication_bus_agents_registered",
            extra={"count": len(list_agent_runtime_policies())},
        )
    except Exception as exc:
        logger.warning(
            "communication_bus_init_failed",
            extra={"error": str(exc)},
        )
```

Chamar `await self._initialize_communication_bus()` no `AgentRuntime.__init__` usando `asyncio.create_task()`.

---

### Passo 5 — Integrar CircuitBreaker existente

Usar o `CircuitBreaker` do módulo `communication/circuit_breaker/breaker.py` para proteger o `send()`:

```python
# No InternalCommunicationBus.__init__:
from mindflow_backend.communication.circuit_breaker.breaker import CircuitBreaker

self._circuit_breaker = CircuitBreaker(
    name="internal_bus",
    failure_threshold=5,
    recovery_timeout=30,
    success_threshold=3,
)

# No send():
async def send(self, from_agent, to_agent, message) -> bool:
    async def _do_send() -> bool:
        # ... lógica atual ...
        return True
    
    try:
        return await self._circuit_breaker.execute(_do_send)
    except Exception:
        logger.warning("bus_circuit_open", extra={"from": from_agent, "to": to_agent})
        self._stats["messages_dropped"] += 1
        return False
```

---

## ✅ Checklist de Conclusão

### Sprint 1, Semana 1 (Dias 1–3)

- [ ] Criar diretório `communication/bus/`
- [ ] Criar `communication/bus/__init__.py`
- [ ] Criar `communication/bus/communication_bus.py` (CommunicationBus abstract)
- [ ] Implementar `InternalCommunicationBus` com asyncio queues
- [ ] Implementar `get_communication_bus()` singleton
- [ ] Atualizar `communication/__init__.py` com novos exports

### Sprint 1, Semana 1 (Dias 4–5)

- [ ] Integrar `CircuitBreaker` no `InternalCommunicationBus.send()`
- [ ] Adicionar registro de agentes no `AgentRuntime`
- [ ] Testar `register_agent()` → `send()` → `receive()` manualmente

### Sprint 1, Semana 2

- [ ] Testes unitários: `test_internal_bus.py`
  - [ ] `test_register_agent()`
  - [ ] `test_send_and_receive()`
  - [ ] `test_send_to_unknown_agent_returns_false()`
  - [ ] `test_queue_full_drops_message()`
  - [ ] `test_broadcast_to_room()`
  - [ ] `test_circuit_breaker_opens_after_failures()`
  - [ ] `test_health_check()`
- [ ] `set_communication_bus()` funcional para testes de integração
- [ ] Documentação de health check endpoint

---

## 🧪 Como Testar Manualmente

```python
import asyncio
from mindflow_backend.communication.bus import get_communication_bus, InternalCommunicationBus
from mindflow_backend.communication.protocols.p2p_protocol import P2PMessage, MessageType

async def test():
    bus = InternalCommunicationBus()
    
    await bus.register_agent("analyst")
    await bus.register_agent("coder")
    
    msg = P2PMessage(
        from_agent="coder",
        to_agent="analyst",
        content="Encontrei padrão arquitetural suspeito",
        message_type=MessageType.REQUEST,
        urgency="HIGH"
    )
    
    sent = await bus.send("coder", "analyst", msg)
    print(f"Enviado: {sent}")
    
    received = await bus.receive("analyst", timeout=1.0)
    print(f"Recebido: {received.content}")
    
    health = await bus.health_check()
    print(f"Health: {health}")

asyncio.run(test())
```

---

## 📊 Métricas de Sucesso Desta Fase

| Métrica | Target |
|---|---|
| `send()` latência (internal bus) | < 5ms |
| Queue full rate em teste de carga | < 1% com 100msg/s |
| Circuit breaker abre após 5 falhas | ✅ em 100% dos testes |
| Agentes registrados no startup | 100% dos `AGENT_RUNTIME_POLICY` |

---

## ⚠️ Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| Asyncio queue não thread-safe em edge cases | Usar `loop.call_soon_threadsafe()` se necessário |
| Memory leak em agentes não registrados | `MAX_QUEUE_SIZE=100` + TTL cleanup automático |
| Múltiplos `get_communication_bus()` em threads | Singleton com `asyncio.Lock()` na inicialização |
| Bus não inicializado antes de delegação | `AgentRuntime` inicializa bus no startup, não on-demand |
