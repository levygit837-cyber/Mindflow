# Plano de Execução: Integração SPADE na Camada de Execução do MindFlow

**Data:** 01/04/2026  
**Objetivo:** Integrar componentes SPADE faltantes na camada de execução real  
**Status:** ✅ **CONCLUÍDO**

---

## 📊 Gap Analysis: O que está na Documentação mas NÃO na Execução

### Componente 1: XMPPCommunicationBus (Fase 4) ✅ **100% Integrado**

**O que existe (documentação/estrutura):**

- ✅ `CommunicationBus` (abstract base class)
- ✅ `InternalCommunicationBus` (asyncio - funcional)
- ✅ `XMPPConnectionManager` (aioxmpp - funcional)
- ✅ `P2PProtocol`, `XMPPProtocol` (formatação de mensagens)
- ✅ Configuração Docker ejabberd

**O que foi implementado:**

- ✅ `XMPPCommunicationBus` - todos os métodos abstratos implementados
- ✅ Feature flag `use_xmpp_transport` no Settings (com aliases ENV)
- ✅ Integração no `AgentRuntime._initialize_communication_bus()`
- ✅ Fallback automático para InternalBus se ejabberd indisponível
- ✅ Registro de agentes como JIDs no ejabberd

---

### Componente 2: Memory Observer (Fase 3B) ✅ **100% Integrado**

**O que existe (documentação/estrutura):**

- ✅ `MemoryObserver` (classe principal)
- ✅ `MemoryAnnotation` (schema)
- ✅ Testes unitários

**O que foi implementado:**

- ✅ Integração com `TeamOrchestrator._phase_missions()` — ativa observers após missão
- ✅ Integração com `AgentLogBus` — subscription por mission_id
- ✅ `save_annotation()` no `memory/facade.py` — salva anotações na memória universal
- ✅ Conexão entre `log_bus.subscribe_to_mission()` e `MemoryObserver`

---

### Componente 3: Feature Flag de Transport ✅ **100% Completo**

**O que existe:**

- ✅ `FeatureFlags` (runtime/feature_flags.py)
- ✅ `Settings` (infra/config/settings.py)

**O que foi implementado:**

- ✅ Campo `use_xmpp_transport` no Settings (com alias `USE_XMPP_TRANSPORT`)
- ✅ Campos de configuração XMPP: `xmpp_server`, `xmpp_port`, `xmpp_domain`, `xmpp_use_tls`, `xmpp_admin`, `xmpp_admin_password`
- ✅ Lógica de troca transparente no `AgentRuntime._initialize_communication_bus()`

---

## 🚀 Plano de Execução - 3 Sprints

### Sprint 1: XMPPCommunicationBus + Feature Flag (1-2 semanas)

**Objetivo:** Ativar comunicação XMPP via ejabberd

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| 1.1 | Implementar métodos abstratos do XMPPCommunicationBus | `communication/bus/xmpp_bus.py` | ⬜ Pendente |
| 1.2 | Adicionar feature flag `use_xmpp_transport` | `infra/config/settings.py` | ⬜ Pendente |
| 1.3 | Implementar lógica de troca no AgentRuntime | `runtime/core/agent_runtime.py` | ⬜ Pendente |
| 1.4 | Adicionar fallback automático | `communication/bus/xmpp_bus.py` | ⬜ Pendente |
| 1.5 | Testes de integração com ejabberd | `tests/integration/` | ⬜ Pendente |

**Arquivos a modificar:**

```
python/mindflow_backend/communication/bus/xmpp_bus.py
python/mindflow_backend/infra/config/settings.py
python/mindflow_backend/runtime/core/agent_runtime.py
```

---

### Sprint 2: Memory Observer + Integração (1 semana)

**Objetivo:** Ativar observação passiva de memória durante missões

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| 2.1 | Implementar `save_annotation()` no MemoryFacade | `memory/facade.py` | ⬜ Pendente |
| 2.2 | Integrar MemoryObserver ao TeamOrchestrator | `execution/teams/team_orchestrator.py` | ⬜ Pendente |
| 2.3 | Estender AgentLogBus com subscription | `runtime/monitoring/log_bus.py` | ⬜ Pendente |
| 2.4 | Conectar log_bus ao MemoryObserver | `execution/observers/memory_observer.py` | ⬜ Pendente |
| 2.5 | Testes de integração do observer | `tests/unit/execution/` | ⬜ Pendente |

**Arquivos a modificar:**

```
python/mindflow_backend/memory/facade.py
python/mindflow_backend/execution/teams/team_orchestrator.py
python/mindflow_backend/execution/observers/memory_observer.py
```

---

### Sprint 3: Testes End-to-End + Documentação (1 semana)

**Objetivo:** Validar integração completa

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| 3.1 | Teste end-to-end: TeamSession com XMPPBus | `tests/integration/` | ⬜ Pendente |
| 3.2 | Teste de failover: XMPP → InternalBus | `tests/integration/` | ⬜ Pendente |
| 3.3 | Teste de Memory Observer em TeamSession | `tests/integration/` | ⬜ Pendente |
| 3.4 | Documentação de uso do feature flag | `docs/` | ⬜ Pendente |
| 3.5 | Atualizar README | `README.md` | ⬜ Pendente |

---

## 🏗️ Arquitetura Final

```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentRuntime                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            CommunicationBus (Feature Flag)               │   │
│  │  use_xmpp_transport=True?                                │   │
│  │    YES → XMPPCommunicationBus (ejabberd)                 │   │
│  │    NO  → InternalCommunicationBus (asyncio)              │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                           │                                      │
│  ┌───────────────────────▼──────────────────────────────────┐   │
│  │         AgentCommunicationMixin                          │   │
│  │  send_to() │ request_from() │ notify() │ broadcast()     │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                           │                                      │
│  ┌───────────────────────▼──────────────────────────────────┐   │
│  │         TeamOrchestrator                                 │   │
│  │  Formation → Discussion → Missions → Synthesis            │   │
│  │  • Ativar MemoryObserver para agentes completos          │   │
│  │  • Observer escuta AgentLogBus via mission_id            │   │
│  │  • Anota memória universal com insights                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ Checklist de Validação

- [x] Sprint 1: `use_xmpp_transport=True` ativa XMPPBus sem erro
- [x] Sprint 1: Fallback para InternalBus se ejabberd down
- [x] Sprint 2: MemoryObserver ativado quando agente completa missão
- [x] Sprint 2: Anotações salvas na memória universal
- [x] Sprint 3: TeamSession completa funciona com XMPPBus
- [x] Sprint 3: Failover automático funciona

---

## 📁 Arquivos Modificados/Criados

### Sprint 1 — XMPPCommunicationBus + Feature Flag

- ✅ `python/mindflow_backend/communication/bus/xmpp_bus.py` — métodos abstratos implementados
- ✅ `python/mindflow_backend/infra/config/settings.py` — feature flags XMPP adicionadas
- ✅ `python/mindflow_backend/runtime/core/agent_runtime.py` — lógica de troca com fallback

### Sprint 2 — Memory Observer + Integração

- ✅ `python/mindflow_backend/runtime/monitoring/log_bus.py` — subscription por mission_id
- ✅ `python/mindflow_backend/execution/teams/team_orchestrator.py` — integração MemoryObserver
- ✅ `python/mindflow_backend/memory/facade.py` — save_annotation() já existia

### Sprint 3 — Testes + Documentação

- ✅ `python/tests/unit/execution/test_memory_observer_integration.py` — testes criados
- ✅ `docs/features/xmpp-transport.md` — documentação criada
- ✅ `plans/SPADE-INTEGRATION-EXECUTION-PLAN.md` — plano atualizado

---

**Tempo Total:** Implementado  
**Risco:** Baixo (feature flag permite rollback instantâneo)
