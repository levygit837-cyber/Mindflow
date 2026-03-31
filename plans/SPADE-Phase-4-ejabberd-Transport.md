# ⚡ Fase 4 — ejabberd Transport: XMPP Real como Message Bus

**Fase:** 4 | **Semana:** 9+ | **Prioridade:** P2 (Condicional)  
**PRD Base:** `docs/PRD/PRD-SPADE-Communication-Layer.md`  
**Depende de:** Validação de P1/P2 nas Fases 1–3  
**Condição:** Só executar se métricas das Fases 1–3 justificarem ejabberd  
**Bloqueia:** Nada — é a fase terminal do roadmap

---

## 📋 Sumário

Esta fase é **condicional**: só deve ser executada se os testes de performance e confiabilidade das Fases 1–3 mostrarem que o `InternalCommunicationBus` (asyncio) **não é suficiente** para as demandas de produção.

O `communication/connection/xmpp_connection.py` já implementa o `XMPPConnectionManager` com `aioxmpp`. Esta fase o **ativa** criando o `XMPPCommunicationBus` que implementa a mesma interface `CommunicationBus` das fases anteriores.

A troca é transparente: apenas `set_communication_bus(XMPPCommunicationBus(...))` no startup.

---

## 🎯 Critério de Go/No-Go

### Executar esta fase SE:
| Critério | Threshold para Migrar |
|---|---|
| Volume de mensagens P2P por sessão | > 1000 msgs/sessão |
| Necessidade de persistência de mensagens | Sim (mensagens não devem se perder em restart) |
| Necessidade de audit trail | Log permanente de todas as comunicações |
| Multi-instância do MindFlow | ≥ 2 instâncias precisam se comunicar |
| InternalBus latência em produção | > 500ms consistentemente |

### Não executar SE:
- `InternalCommunicationBus` funciona bem em produção
- Não há multi-instância planejada
- Overhead operacional do ejabberd não compensa

---

## 🏗️ Arquitetura

```
Fase 4: InternalBus → XMPPBus (via feature flag)

startup:
  SE use_xmpp_transport == True:
    bus = XMPPCommunicationBus(ejabberd_config)
  ELSE:
    bus = InternalCommunicationBus()  ← padrão atual
  
  set_communication_bus(bus)

┌──────────────────────────────────────────────────────────────┐
│                       ejabberd server                         │
│  (Docker container: ghcr.io/processone/ejabberd:latest)      │
├──────────────────────────────────────────────────────────────┤
│  XMPP domain: mindflow.local                                  │
│  Agents JIDs: orchestrator@mindflow.local                    │
│               analyst@mindflow.local                          │
│               coder@mindflow.local                            │
│               researcher@mindflow.local                       │
│  MUC domain:  conference.mindflow.local                       │
└──────────────────────────────────────────────────────────────┘
        ↑
        │ aioxmpp client
        ↓
┌──────────────────────┐
│  XMPPCommunicationBus│  ← implementa CommunicationBus interface
│  (usa XMPPConnectionManager já existente)
└──────────────────────┘
```

---

## 🐳 Infrastructure Setup

### Docker Compose para ejabberd

```yaml
# docker/ejabberd/docker-compose.yml

version: '3.8'

services:
  ejabberd:
    image: ghcr.io/processone/ejabberd:latest
    container_name: mindflow_ejabberd
    environment:
      - EJABBERD_DOMAIN=mindflow.local
      - EJABBERD_ADMIN=admin@mindflow.local
      - EJABBERD_ADMIN_PASSWORD=mindflow_dev_pass
    ports:
      - "5222:5222"   # XMPP client connections
      - "5269:5269"   # Server-to-server
      - "5280:5280"   # HTTP admin + BOSH
    volumes:
      - ./ejabberd.yml:/opt/ejabberd/conf/ejabberd.yml
      - ejabberd_data:/opt/ejabberd/database
    healthcheck:
      test: ["CMD", "ejabberdctl", "status"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ejabberd_data:
```

### Configuração ejabberd.yml

```yaml
# docker/ejabberd/ejabberd.yml

hosts:
  - mindflow.local

loglevel: info

listen:
  -
    port: 5222
    ip: "::"
    module: ejabberd_c2s
    max_stanza_size: 262144
    shaper: c2s_shaper
    access: c2s
    starttls_required: false  # Dev only — enable TLS in prod

  -
    port: 5280
    ip: "::"
    module: ejabberd_http
    request_handlers:
      /api: mod_http_api
      /admin: ejabberd_web_admin

modules:
  mod_adhoc: {}
  mod_announce:
    access: announce
  mod_caps: {}
  mod_carboncopy: {}
  mod_client_state: {}
  mod_configure: {}
  mod_disco: {}
  mod_mam:
    db_type: mnesia
    default: always     # Persistência de mensagens
    request_activates_archiving: false
  mod_muc:
    access:
      - allow
    access_admin:
      - allow: admin
    access_create:
      - allow
    default_room_options:
      mam: true
      persistent: true
  mod_ping: {}
  mod_privacy: {}
  mod_private: {}
  mod_pubsub: {}
  mod_roster: {}
  mod_vcard: {}

# Permitir registro in-band (para criar accounts de agentes)
modules:
  mod_register:
    access: register
    welcome_message:
      subject: "MindFlow Agent"
      body: "Agent registered"

acl:
  admin:
    user:
      - "admin@mindflow.local"
  
access_rules:
  c2s:
    allow: all
  announce:
    allow: admin
  register:
    allow: all
```

---

## 🔧 Implementação: `XMPPCommunicationBus`

**Arquivo:** `python/mindflow_backend/communication/bus/xmpp_bus.py`

```python
# communication/bus/xmpp_bus.py
"""
XMPPCommunicationBus — Implementação do CommunicationBus usando ejabberd/XMPP.

Usa XMPPConnectionManager (já existente) como transport.
Registra agentes como JIDs no ejabberd.
Mensagens P2P = XMPP stanzas diretas.
Team broadcast = XMPP MUC messages.

Fase 4 — só ativar após validação das Fases 1-3.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from mindflow_backend.communication.bus.communication_bus import CommunicationBus
from mindflow_backend.communication.connection.xmpp_connection import (
    XMPPConfig,
    XMPPConnectionManager,
    XMPPConnectionConfig,
)
from mindflow_backend.communication.protocols.p2p_protocol import P2PMessage
from mindflow_backend.communication.teams.team_chat import TeamMessage

_logger = logging.getLogger(__name__)

MINDFLOW_XMPP_DOMAIN = "mindflow.local"
MINDFLOW_MUC_DOMAIN = "conference.mindflow.local"
DEFAULT_AGENT_PASSWORD = "agent_mindflow_2026"


class XMPPCommunicationBus(CommunicationBus):
    """
    CommunicationBus baseado em ejabberd/XMPP.
    
    Drop-in replacement para InternalCommunicationBus.
    Trocar via set_communication_bus(XMPPCommunicationBus(config)).
    """

    def __init__(self, config: XMPPConnectionConfig | None = None) -> None:
        self._config = config or XMPPConnectionConfig(
            server="localhost",
            port=5222,
            domain=MINDFLOW_XMPP_DOMAIN,
            use_tls=False,  # Dev — habilitar em prod
        )
        self._manager = XMPPConnectionManager(config=self._config)
        self._registered_agents: set[str] = set()
        self._message_handlers: dict[str, list[Callable]] = {}
        self._available = False

    async def connect(self) -> bool:
        """Inicia o manager XMPP."""
        try:
            result = await self._manager.start()
            self._available = result.get("success", False)
            _logger.info("xmpp_bus_connected", available=self._available)
            return self._available
        except Exception as exc:
            _logger.error("xmpp_bus_connect_failed", error=str(exc))
            return False

    async def register_agent(self, agent_id: str) -> None:
        """Registra agente no ejabberd como JID."""
        if agent_id in self._registered_agents:
            return
        
        try:
            result = await self._manager.register_agent(
                username=agent_id,
                password=DEFAULT_AGENT_PASSWORD,
            )
            if result.get("success"):
                self._registered_agents.add(agent_id)
                self._message_handlers[agent_id] = []
                _logger.info("xmpp_agent_registered", agent_id=agent_id)
            else:
                _logger.warning("xmpp_agent_register_failed", agent_id=agent_id)
        except Exception as exc:
            _logger.error("xmpp_register_error", agent_id=agent_id, error=str(exc))

    async def unregister_agent(self, agent_id: str) -> None:
        """Remove agente do ejabberd."""
        self._registered_agents.discard(agent_id)
        self._message_handlers.pop(agent_id, None)

    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message: P2PMessage,
    ) -> bool:
        """Envia mensagem P2P via XMPP stanza."""
        if not self._available:
            return False
        
        try:
            to_jid = self._config.get_jid(to_agent)
            result = await self._manager.send_message(
                from_username=from_agent,
                to_username=to_jid,
                content=message.content,
                urgency=message.urgency,
            )
            return result.get("success", False)
        except Exception as exc:
            _logger.warning("xmpp_send_failed", error=str(exc))
            return False

    async def broadcast(
        self,
        from_agent: str,
        room_id: str,
        message: TeamMessage,
    ) -> bool:
        """Envia mensagem para MUC room."""
        if not self._available:
            return False
        
        try:
            room_jid = f"{room_id}@{MINDFLOW_MUC_DOMAIN}"
            result = await self._manager.send_message(
                from_username=from_agent,
                to_username=room_jid,
                content=message.content,
                urgency="MEDIUM",
            )
            return result.get("success", False)
        except Exception as exc:
            _logger.warning("xmpp_broadcast_failed", error=str(exc))
            return False

    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[P2PMessage], Awaitable[None]],
    ) -> None:
        """Registra handler para mensagens XMPP recebidas."""
        if agent_id not in self._message_handlers:
            self._message_handlers[agent_id] = []
        self._message_handlers[agent_id].append(handler)
        
        # Registrar handler no manager XMPP
        async def xmpp_handler(raw_message: dict[str, Any]) -> None:
            msg = P2PMessage.from_dict(raw_message)
            await handler(msg)
        
        self._manager.register_message_handler(agent_id, xmpp_handler)

    async def health_check(self) -> dict[str, Any]:
        health = await self._manager.get_health_status()
        return {
            "type": "xmpp",
            "available": self._available,
            "domain": self._config.domain,
            "registered_agents": list(self._registered_agents),
            "manager_status": health,
        }

    @property
    def is_available(self) -> bool:
        return self._available
```

**Arquivo:** `python/mindflow_backend/communication/bus/xmpp_bus.py`

---

## 🔧 Feature Flag para Troca Transparente

**Arquivo:** `python/mindflow_backend/infra/config.py` — adicionar:

```python
# infra/config.py

class Settings(BaseSettings):
    # ... campos existentes ...
    
    # NOVO: Feature flag para transport de comunicação
    use_xmpp_transport: bool = False
    """Se True, usa ejabberd/XMPP. Se False, usa InternalBus (padrão)."""
    
    xmpp_server: str = "localhost"
    xmpp_port: int = 5222
    xmpp_domain: str = "mindflow.local"
    xmpp_use_tls: bool = False
```

**Arquivo:** `python/mindflow_backend/runtime/core/agent_runtime.py` — startup:

```python
async def _initialize_communication_bus(self) -> None:
    settings = get_settings()
    
    if settings.use_xmpp_transport:
        from mindflow_backend.communication.bus.xmpp_bus import XMPPCommunicationBus
        from mindflow_backend.communication.connection.xmpp_connection import XMPPConnectionConfig
        from mindflow_backend.communication.bus.communication_bus import set_communication_bus
        
        config = XMPPConnectionConfig(
            server=settings.xmpp_server,
            port=settings.xmpp_port,
            domain=settings.xmpp_domain,
            use_tls=settings.xmpp_use_tls,
        )
        xmpp_bus = XMPPCommunicationBus(config)
        connected = await xmpp_bus.connect()
        
        if connected:
            set_communication_bus(xmpp_bus)
            _logger.info("xmpp_transport_activated")
        else:
            _logger.warning("xmpp_transport_failed_fallback_to_internal")
            # Fallback automático para InternalBus
    
    # Registrar agentes (funciona para ambos os buses)
    from mindflow_backend.communication.bus.communication_bus import get_communication_bus
    from mindflow_backend.agents.specialists.runtime_policy import list_agent_runtime_policies
    
    bus = get_communication_bus()
    for policy in list_agent_runtime_policies():
        await bus.register_agent(policy.agent_id)
```

---

## ✅ Checklist de Conclusão

### Pré-requisito: Decisão Go/No-Go
- [ ] Revisar métricas das Fases 1–3 em produção
- [ ] Verificar se `InternalCommunicationBus` é suficiente
- [ ] Decisão documentada em ADR (Architecture Decision Record)

### Se Go — Infrastructure (Semana 9)
- [ ] Criar `docker/ejabberd/docker-compose.yml`
- [ ] Criar `docker/ejabberd/ejabberd.yml`
- [ ] Testar ejabberd em ambiente dev: `docker compose up ejabberd`
- [ ] Verificar JID registration via admin API
- [ ] Verificar MUC room creation funcional

### Código (Semana 9–10)
- [ ] Criar `communication/bus/xmpp_bus.py` (XMPPCommunicationBus)
- [ ] Adicionar `use_xmpp_transport` feature flag em `Settings`
- [ ] Atualizar `_initialize_communication_bus()` com feature flag
- [ ] Verificar que `XMPPConnectionManager` existente suporta todos os métodos necessários
- [ ] Atualizar `communication/bus/__init__.py` com `XMPPCommunicationBus`

### Circuit Breakers (já planejado em Phase-5-circuit-breakers.md)
- [ ] Aplicar `@circuit_protected` em `XMPPService.send_message()`
- [ ] Aplicar `@circuit_protected` em `XMPPService.connect_agent()`
- [ ] Fallback: se XMPP circuit abre → mensagem vai para internal queue temporária

### Testes
- [ ] `test_xmpp_bus_register_agent()` (integration, requires ejabberd)
- [ ] `test_xmpp_bus_send_message()`
- [ ] `test_xmpp_bus_fallback_to_internal_if_down()`
- [ ] `test_feature_flag_activates_xmpp_bus()`
- [ ] Performance test: XMPPBus latência vs. InternalBus latência

---

## 📊 Métricas de Sucesso

| Métrica | Target |
|---|---|
| XMPPBus latência P2P | < 200ms (vs. < 5ms internal) |
| Failover para InternalBus se XMPP down | < 500ms |
| Mensagens persistidas no ejabberd | 100% (via mod_mam) |
| Feature flag troca sem restart | ✅ |
| Circuit breaker protege XMPP calls | ✅ |

---

## ⚠️ Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| ejabberd overhead em dev | ALTA | BAIXO | Feature flag off por padrão |
| aioxmpp versão incompatível | MÉDIA | MÉDIO | Fixar versão no pyproject.toml |
| Latência XMPP > InternalBus | ALTA | MÉDIO | InternalBus permanece como fallback |
| ejabberd config complexa | MÉDIA | BAIXO | Docker Compose com config mínima |
| TLS setup em prod | BAIXA | ALTO | Certificado Let's Encrypt via ACME |

---

## 📌 Referência: Decisão ADR

Ao finalizar as Fases 1–3, criar o seguinte ADR antes de iniciar a Fase 4:

```markdown
# ADR-001: Transport de Comunicação Inter-Agente

## Decisão
[ ] Manter InternalCommunicationBus (asyncio) como transporte permanente
[ ] Migrar para XMPPCommunicationBus (ejabberd) como transporte de produção
[ ] Híbrido: InternalBus para dev, XMPPBus para prod

## Contexto
Métricas coletadas nas Fases 1–3:
- Volume máximo de mensagens/sessão: ___
- Latência InternalBus em produção: ___ms
- Necessidade de persistência: sim/não
- Multi-instância planejada: sim/não

## Consequências
...
```
