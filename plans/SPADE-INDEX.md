# 🗺️ SPADE Integration — Índice Master de Planos

**Projeto:** MindFlow — Integração SPADE/XMPP  
**Data:** 2026-03-31  
**Total de Fases:** 4 | **Total de Planos:** 8  
**Análise base:** `docs/analysis/ANALISE_SPADE_INTEGRATION.md`  
**PRDs base:** `docs/PRD/PRD-SPADE-*.md`

---

## 📋 Visão Geral do Roadmap

```
FASE 1 — FUNDAÇÃO (Semanas 1–4)
────────────────────────────────
  [1A] CommunicationBus           → Semana 1–2  (P0, sem dependências)
  [1B] AgentCommunicationMixin    → Semana 2–3  (depende de 1A)
  [1C] CommRoles + RuntimePolicy  → Semana 1–2  (P0, paralelo a 1A)
  ── Circuit Breakers ──────────── Semana 3     (usa Phase-5 existente)

FASE 2 — EXECUTION GRAPHS (Semanas 1–4, paralelo à Fase 1)
────────────────────────────────────────────────────────────
  [2A] Execution Graphs           → Semana 2–3  (paralelo a 1A/1C)
  [2B] MissionLauncher            → Semana 3–4  (depende de 2A + 1A)

FASE 3 — TEAM PROTOCOL (Semanas 5–8)
───────────────────────────────────────
  [3A] Team Protocol + Session    → Semana 5–6  (depende de 1A+1B+2B)
  [3B] Memory Observer            → Semana 7–8  (depende de 3A)

FASE 4 — TRANSPORTE (Semanas 9+, condicional)
──────────────────────────────────────────────
  [4]  ejabberd + XMPPBus         → Semana 9+   (depende de validação P1/P2)
```

---

## 📁 Planos Neste Diretório

| Arquivo | Fase | Prioridade | Semana | Status |
|---|---|---|---|---|
| [SPADE-Phase-1A-Communication-Bus.md](./SPADE-Phase-1A-Communication-Bus.md) | 1 | P0 | 1–2 | 🔄 Em Andamento |
| [SPADE-Phase-1B-Agent-Communication-Mixin.md](./SPADE-Phase-1B-Agent-Communication-Mixin.md) | 1 | P0 | 2–3 | ⬜ Pendente |
| [SPADE-Phase-1C-CommRoles-RuntimePolicy.md](./SPADE-Phase-1C-CommRoles-RuntimePolicy.md) | 1 | P0 | 1–2 | ✅ Completo |
| [SPADE-Phase-2A-Execution-Graphs.md](./SPADE-Phase-2A-Execution-Graphs.md) | 2 | P0 | 2–3 | ⬜ Pendente |
| [SPADE-Phase-2B-MissionLauncher.md](./SPADE-Phase-2B-MissionLauncher.md) | 2 | P0 | 3–4 | ⬜ Pendente |
| [SPADE-Phase-3A-Team-Protocol.md](./SPADE-Phase-3A-Team-Protocol.md) | 3 | P1 | 5–6 | ⬜ Pendente |
| [SPADE-Phase-3B-Memory-Observer.md](./SPADE-Phase-3B-Memory-Observer.md) | 3 | P1 | 7–8 | ⬜ Pendente |
| [SPADE-Phase-4-ejabberd-Transport.md](./SPADE-Phase-4-ejabberd-Transport.md) | 4 | P2 | 9+ | ⬜ Condicional |

---

## 🔗 Grafo de Dependências

```
[1C] CommRoles ──────────────────────────────────────────┐
                                                         ↓
[1A] CommunicationBus ──→ [1B] AgentCommMixin ──→ [2B] MissionLauncher ──→ [3A] TeamProtocol
                                   │                        ↑                      │
[2A] ExecutionGraphs ──────────────┘────────────────────────┘              [3B] MemObserver
                                                                                   │
                                                                          [4] ejabberd ←(condicional)
```

### Regras

- **1A** e **1C** podem iniciar em paralelo na Semana 1
- **1B** começa após **1A** ter o `CommunicationBus` funcional
- **2A** é paralelo a **1A/1C** — não há dependência de código
- **2B** depende de **2A** (precisa dos graphs) e **1A** (precisa do bus no MissionContext)
- **3A** depende de **1A+1B+2B** todos concluídos
- **3B** depende de **3A** ter TeamSession funcional
- **4** é condicional: só inicia se P1/P2 de Phase 3 validarem necessidade de XMPP real

---

## 🎯 Objetivos por Fase

### Fase 1 — Fundação

**Entregável:** Agentes conseguem trocar mensagens P2P diretamente durante execução, sem passar pelo Orchestrator LLM. Circuit breaker ativo para fault tolerance.

**Done When:**

- [ ] `InternalCommunicationBus` funcionando com asyncio queues
- [ ] `AgentCommunicationMixin` injetado pelo `DelegationEngine`
- [ ] Todos os agentes registrados no bus no startup
- [ ] `CommRole` definido para cada `AgentRuntimePolicy`
- [ ] Circuit breaker ativo protegendo P2P calls
- [ ] Teste de integração: Coder envia P2P ao Analyst durante delegação

### Fase 2 — Execution Graphs

**Entregável:** Cada agente executa no grafo especializado correto para o tipo de missão. `MissionLauncher` seleciona e lança o graph sem hardcode.

**Done When:**

- [ ] `AnalysisGraph`, `CodingGraph`, `ResearchGraph`, `SecurityAuditGraph` criados
- [ ] Todos registrados no `GraphFactory`
- [ ] `AgentRuntimePolicy` com `available_mission_graphs` por agente
- [ ] `MissionLauncher` funcional com `MissionContext` e `MissionResult`
- [ ] `DelegationEngine` usa `MissionLauncher` quando `mission_type` disponível
- [ ] Anotação contínua de memória em cada iteração dos graphs

### Fase 3 — Team Protocol

**Entregável:** Orchestrator cria times de agentes que discutem antes de executar missões paralelas. MemoryObserver anota contexto em tempo real.

**Done When:**

- [ ] `TeamSession` com 4 fases (Formation→Discussion→Missions→Synthesis)
- [ ] `TeamOrchestrator` facilita discussion e extrai `MissionDAG`
- [ ] Missões paralelas com sincronização via P2P signals
- [ ] `MemoryObserver` ativo: agentes que concluíram missão observam os demais
- [ ] `IntelligentRouter` decide `team_session` para tasks com complexity ≥ 0.7
- [ ] Resultado final sintetizado pelo Orchestrator

### Fase 4 — Transporte (Condicional)

**Entregável:** ejabberd como message bus real, substituindo `InternalCommunicationBus` quando validado.

**Done When (se aprovado):**

- [ ] ejabberd running em ambiente dev/staging
- [ ] `XMPPCommunicationBus` implementado e testado
- [ ] `InternalBus` substituível via config (feature flag)
- [ ] Performance ≥ Internal Bus em ambiente controlado

---

## 📊 Métricas de Sucesso Globais

| Métrica | Baseline | Target Fase 1 | Target Fase 2 | Target Fase 3 |
|---|---|---|---|---|
| Latência inter-agente | ~2-5s (LLM) | < 100ms (P2P) | < 50ms (missions) | < 100ms (team) |
| Graph types em produção | 1 | 1 | 8+ | 8+ |
| Memory annotations/sessão | 0 | 0 | ≥5 | ≥10 |
| Team sessions bem sucedidas | N/A | N/A | N/A | ≥80% |
| Falhas de comunicação P2P | N/A | <0.1% | <0.1% | <0.1% |

---

## 📋 Plano de Execução — Próximas Etapas (2026-03-31)

### ✅ Status Atual: Fases 1-3 COMPLETAS (código implementado)

**Testes executados:**

- Fase 1 (Communication): **16 passed** ✅
- Fase 2/3 (Missions, Teams, Memory): **49 passed** ✅
- Total: **65/66 testes passam** (1 bug de circular import em `test_mission_launcher.py`)

### 📌 Etapa Imediata: Correção do test_mission_launcher.py

| # | Tarefa | Arquivo | Responsável |
|---|---|---|---|
| I-1 | Resolver circular import em `test_mission_launcher.py` | `mindflow_backend/tests/unit/execution/test_mission_launcher.py` | Dev |
| I-2 | Verificar que todos os 65+ testes passam | CI | Dev |

### 📌 Etapa 1: Validação E2E (Semana 1)

| # | Tarefa | Critério de Sucesso |
|---|---|---|
| 1.1 | Teste de integração P2P: Coder → Analyst | Mensagem enviada e recebida < 100ms |
| 1.2 | Teste de MissionLauncher com graph real | Missão executa sem LLM durante delegação |
| 1.3 | Teste de TeamSession com 2+ agentes | Discussão → DAG → Missões paralelas |
| 1.4 | Teste de MemoryObserver | ≥5 memory annotations por sessão |
| 1.5 | Medir latência do InternalBus | < 50ms em dev |
| 1.6 | Coletar métricas de produção | Volume msgs/sessão, necessidade persistência |

### 📌 Etapa 2: Decisão Go/No-Go para Fase 4

| Critério | Threshold | Status Atual |
|---|---|---|
| Volume de mensagens P2P por sessão | > 1000 msgs | ⬜ A medir |
| Persistência de mensagens necessária | Sim | ⬜ Avaliar |
| Multi-instância MindFlow | ≥ 2 instâncias | ⬜ Planejar |
| InternalBus latência > 500ms | Consistentemente | ⬜ Medir |
| **Decisão** | | ⬜ **PENDENTE** |

### 📌 Etapa 3: Fase 4 — ejabberd (Só se Go/No-Go aprovar)

| # | Tarefa | Arquivo | Status |
|---|---|---|---|
| 3.1 | Criar ADR-001 com decisão de transporte | `docs/adr/ADR-001-transport.md` | ⬜ Pendente |
| 3.2 | Configurar ejabberd em Docker Compose | `docker/ejabberd/docker-compose.yml` | ⬜ Pendente |
| 3.3 | Criar `XMPPCommunicationBus` | `communication/bus/xmpp_bus.py` | ⬜ Pendente |
| 3.4 | Adicionar feature flag `use_xmpp_transport` | `infra/config.py` | ⬜ Pendente |
| 3.5 | Atualizar `_initialize_communication_bus()` | `runtime/core/agent_runtime.py` | ⬜ Pendente |
| 3.6 | Circuit breakers em XMPP calls | `communication/circuit_breaker/` | ⬜ Pendente |
| 3.7 | Testes de integração XMPP | `tests/integration/` | ⬜ Pendente |
| 3.8 | Teste de fallback (XMPP → InternalBus) | `tests/integration/` | ⬜ Pendente |

---

## 🧩 Arquivos que Serão Criados/Modificados

### Novos arquivos

```
communication/
  bus/
    __init__.py
    communication_bus.py          ← 1A
    xmpp_bus.py                   ← 4
  mixins/
    __init__.py
    agent_communication.py        ← 1B

graphs/implementations/
  analysis/
    __init__.py
    analysis_graph.py             ← 2A
    deep_investigation_graph.py   ← 2A
    security_audit_graph.py       ← 2A
    code_review_graph.py          ← 2A
  coding/
    __init__.py
    coding_graph.py               ← 2A
    refactor_graph.py             ← 2A
    bug_fix_graph.py              ← 2A
  research/
    __init__.py
    research_graph.py             ← 2A
    comparison_graph.py           ← 2A

execution/
  __init__.py
  missions/
    __init__.py
    mission_launcher.py           ← 2B
    mission_context.py            ← 2B
    mission_result.py             ← 2B
  teams/
    __init__.py
    team_session.py               ← 3A
    team_orchestrator.py          ← 3A
    mission_dag.py                ← 3A
  observers/
    __init__.py
    memory_observer.py            ← 3B

schemas/orchestration/
  communication.py                ← 1C (CommRole, MissionGraphType)
  annotation.py                   ← 3B (MemoryAnnotation)
```

### Arquivos modificados

```
agents/specialists/runtime_policy.py  ← 1C (CommRole + available_mission_graphs)
graphs/base/types.py                   ← 2A (MissionGraphType enum)
graphs/factory.py                      ← 2A (registrar novos graph types)
orchestrator/delegation/engine.py      ← 1B + 2B (injetar mixin + usar launcher)
orchestrator/routing/intelligent_router.py ← 3A (team_session strategy)
schemas/orchestration/orchestrator.py  ← 3A (ExecutionStrategy.TEAM_SESSION)
memory/facade.py                       ← 2A + 3B (streaming annotations)
runtime/core/agent_runtime.py          ← 1A (startup registration)
main.py                                ← 1A (bus startup)
```

---

## 📌 Referências

- **Análise completa:** `docs/analysis/ANALISE_SPADE_INTEGRATION.md`
- **PRD Comunicação:** `docs/PRD/PRD-SPADE-Communication-Layer.md`
- **PRD Graphs:** `docs/PRD/PRD-Agent-Roles-Execution-Graphs.md`
- **PRD Team:** `docs/PRD/PRD-Team-Protocol-Collaborative-Missions.md`
- **Plano Circuit Breakers:** `plans/Phase-5-circuit-breakers.md` ← usado na Fase 1
- **Plano Message Bus:** `plans/Phase-4-message-bus-message-protocol.md` ← referência para 1A
