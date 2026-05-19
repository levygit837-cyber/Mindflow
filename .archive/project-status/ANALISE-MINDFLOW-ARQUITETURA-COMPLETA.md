# ANÁLISE COMPLETA DA ARQUITETURA MINDFLOW

## Visão Geral

O MindFlow é um sistema de orquestração de agentes de IA com arquitetura multi-camada. Esta análise mapeia todos os componentes, identifica o fluxo de execução atual e aponta implementações que **não estão integradas ao fluxo principal** — candidatas à transformação do `IntelligentRouter` em fluxo descentralizado.

---

## 1. FLUXO DE EXECUÇÃO ATUAL

### 1.1 Ponto de Entrada: `AgentRuntime.stream_chat()`

```
API Request → AgentChatRequest → AgentRuntime.stream_chat()
```

O `AgentRuntime` é o ponto central que coordena tudo:

- **`RuntimeRouter`** — resolve modo de execução (orchestrated/direct/legacy)
- **`RuntimeExecutor`** — executa estratégias de streaming
- **`StreamManager`** — gerencia eventos SSE
- **`MemoryIntegration`** — integra memória durante execução

### 1.2 Três Modos de Execução

| Modo | Gatilho | Fluxo |
|------|---------|-------|
| **Orchestrated** | `payload.orchestrate=True` ou analyst+folder_path | RouteNode → ExecuteNode → RespondNode (LangGraph) |
| **Direct** | `agent_type` definido sem orchestrate | Agente específico chamado diretamente |
| **Legacy** | Sem agent_type, sem orchestrate | LLM simples sem orquestração |

### 1.3 Fluxo Orquestrado (Principal)

```
UserMessage → RuntimeRouter.resolve_execution_mode()
    ↓
AgentRuntime.stream_chat_orchestrated()
    ↓
build_simple_orchestrator_flow() [LangGraph StateGraph]
    ↓
RouteNode: IntelligentRouter.route_message_intelligently()
    ├── LLM analisa intenção → IntentAnalysis
    ├── Retorna OrchestratorDecision (agent, specialist, strategy, tools)
    └── Auto-ativa TEAM_SESSION se complexity ≥ 0.7 e multi-agent
    ↓
ExecuteNode: AgentBridge.execute()
    ├── Deep Work Loop (até 1000 iterações)
    ├── Cria agente com runtime_policy
    ├── Executa com ferramentas
    └── Supervisão via SupervisorNode (retry 2x)
    ↓
RespondNode: Gera resposta final
```

### 1.4 Estratégias de Execução (OrchestratorDecision)

```python
class ExecutionStrategy(StrEnum):
    DIRECT_RESPONSE = "direct_response"  # Orquestrador responde direto
    DELEGATE = "delegate"                # Delega para 1+ agentes
    CHAIN = "chain"                      # Pipeline de agentes
    GRAPH = "graph"                      # Grafo de execução
    TEAM_SESSION = "team_session"        # Sessão colaborativa
```

**PROBLEMA IDENTIFICADO:** O `IntelligentRouter` é o **gargalo centralizado** — toda decisão de roteamento passa por uma chamada LLM que decide TUDO (agente, estratégia, ferramentas). Os agentes não têm autonomia para sugerir o que podem fazer.

---

## 2. SISTEMA DE MEMÓRIAS

### 2.1 Arquitetura de Memórias (3 Camadas)

| Camada | Módulo | Persistência | Busca |
|--------|--------|--------------|-------|
| **Session Memory** | `memory/session_memory/` | SQLite/PostgreSQL | Semântica via embeddings |
| **Task Memory** | `memory/task_memory/` | PostgreSQL | Cross-task semântica |
| **Project Memory** | `memory/project_memory/` | Índice persistente | Exata + Semântica |

### 2.2 Ferramentas de Memória (Agent Tools)

```python
# agents/tools/integration/memory_tools.py
store_fact       → Salva fatos no AgenticMemoryStore
search_facts     → Busca semântica em memórias longas
retrieve_task_context → Recupera contexto cross-task
recall_session_memory → Busca semântica na sessão
```

### 2.3 Memory Observer (Passivo)

```python
# execution/observers/memory_observer.py
MemoryObserver:
    - Monitora execução de outros agentes em background
    - Nunca bloqueia o agente observado
    - Filtra por importância (score ≥ threshold)
    - Categoriza por diretório (DirectoryMapper)
    - Anota memória com MemoryFacade
```

### 2.4 Memory Protocol (Prompt)

O protocolo de memória está **no prompt** (`agents/prompts/specialized/memory_protocol.py`):

- **ANTES** de cada resposta: buscar `search_facts`, `recall_session_memory`, `retrieve_task_context`
- **DEPOIS** de cada tarefa: salvar decisões, soluções, padrões, preferências

**STATUS:** ✅ Implementado, mas depende do agente seguir o protocolo via prompt.

---

## 3. GERENCIAMENTO DE CONTEXTO

### 3.1 ContextPlus (Codebase Intelligence)

```
contextplus/
├── core/
│   ├── walker.py        → Percorre codebase
│   ├── parser.py        → Parseia arquivos
│   ├── memory_graph.py  → Grafo de conhecimento
│   └── embeddings.py    → Embeddings semânticos
├── tools/
│   ├── discovery/
│   │   ├── context_tree.py     → Árvore de contexto
│   │   ├── file_skeleton.py    → Skeleton de arquivos
│   │   └── semantic_search.py  → Busca semântica
│   ├── analysis/
│   │   └── blast_radius.py     → Análise de impacto
│   └── memory/
│       └── (memory tools integration)
└── integration/
    └── registry.py → Registro de ferramentas
```

### 3.2 ContextPlus Fallback Chain

```python
# agents/tools/contextplus_fallback.py
semantic_code_search → get_context_tree → get_file_skeleton
```

Implementa padrão **circuit breaker** com fallback automático.

### 3.3 Prompt Assembler (Multi-layer)

```python
# agents/prompts/assembler.py
Layer 1: Base (Preamble + Personality + Persistence)  ← Maior prioridade
Layer 2: Tool Descriptions
Layer 3: Environment Context (OS, shell, CWD)
Layer 4: Git Context (branch, staged files)
Layer 5: Memory/MCP Context
Layer 6: Additional Instructions                    ← Menor prioridade
```

### 3.4 Context Builder

```python
# query/context_builder.py
ContextBuilder:
    - Providers: Git, File, Memory, MCP
    - Token budget: 100k tokens (default)
    - Per-provider limits
    - Truncation automática
```

**STATUS:** ✅ Implementado, mas **NÃO integrado ao fluxo principal de roteamento**. O ContextPlus é usado apenas como ferramenta dentro dos agentes, não como parte do pipeline de decisão.

---

## 4. SISTEMA DE ERROS E CIRCUIT BREAKERS

### 4.1 Error Classifier

```python
# infra/error_handling/classifier.py
Classifica erros em categorias para decisão automatizada:
- Transient vs Permanent
- Network vs Auth vs Rate Limit
- Recomenda ação (retry, fallback, escalate)
```

### 4.2 Circuit Breaker (3 Estados)

```
CLOSED ──(failures ≥ 5)──► OPEN ──(60s timeout)──► HALF_OPEN ──(successes ≥ 3)──► CLOSED
```

**Dois circuit breakers independentes:**

| Breaker | Módulo | Escopo |
|---------|--------|--------|
| **Infra** | `infra/resilience/circuit_breaker/core.py` | LLM providers, serviços externos |
| **Communication** | `communication/circuit_breaker/breaker.py` | XMPP, message bus |

### 4.3 Retry/Fallback

```python
# infra/resilience/retry_fallback.py
- Exponential backoff
- Automatic fallback entre providers
- Remote config para thresholds
```

### 4.4 Resilience Dashboard

```python
# api/v1/resilience_dashboard.py
REST API para monitorar estado dos circuit breakers em tempo real
```

**STATUS:** ✅ Implementado e integrado ao infra layer, mas **NÃO conectado ao IntelligentRouter** para decisões de roteamento baseadas em saúde dos agentes.

---

## 5. HOOKS SYSTEM

### 5.1 Arquitetura (27 Eventos)

```python
# hooks/types.py - HookEvent
Tool Lifecycle:     PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest
Session Lifecycle:  SessionStart, SessionEnd, Stop, StopFailure
Agent Lifecycle:    AgentStart, AgentStop
Subagent Lifecycle: SubagentStart, SubagentStop
User Interaction:   UserPromptSubmit, PermissionDenied
Compaction:         PreCompact, PostCompact
Notification:       Notification
Task Lifecycle:     TaskCreated, TaskCompleted
Config/Setup:       Setup, ConfigChange
File System:        FileChanged, CwdChanged
Teammate:           TeammateIdle
MCP:                Elicitation, ElicitationResult
Worktree:           WorktreeCreate, WorktreeRemove
Instructions:       InstructionsLoaded
MindFlow Exclusive: MissionStart, MissionStop
```

### 5.2 Componentes

```
hooks/
├── __init__.py          → API pública
├── types.py             → HookEvent enum (27 eventos)
├── context.py           → HookContext (dados do evento)
├── result.py            → HookResult, AggregatedHookResult
├── registry.py          → HookRegistry (4 fontes: config, plugin, agent, function)
├── manager.py           → HookManager (singleton, execução async)
├── helpers.py           → Match query extraction
├── event_broadcaster.py → Broadcast para UI/transcript
├── config_loader.py     → Carrega hooks de settings.yaml
├── plugin_loader.py     → Carrega hooks de plugins
├── builtin/             → Hooks built-in (format, lint, test, git)
└── handlers/            → 17 handlers específicos
    ├── pre_tool_use.py
    ├── post_tool_use.py
    ├── post_tool_failure.py
    ├── session_start.py / session_end.py
    ├── stop.py / stop_failure.py
    ├── pre_compact.py / post_compact.py
    ├── notification.py
    ├── task_lifecycle.py
    ├── config_change.py
    ├── setup.py
    ├── file_watcher.py
    ├── user_prompt_submit.py
    ├── permission_hook.py
    └── instructions_loaded.py
```

### 5.3 Fluxo de Execução

```python
HookManager.execute(event, context) → AsyncGenerator[HookResult]
    ├── 1. Busca matchers no registry
    ├── 2. Executa command hooks (subprocess)
    ├── 3. Executa function hooks (callbacks)
    └── Cada resultado pode: block, allow, add_context
```

**STATUS:** ✅ Sistema completo implementado, mas **integração com o fluxo principal é parcial**. Os hooks de tool são chamados, mas hooks de agent lifecycle, team, missão não estão conectados ao orquestration flow.

---

## 6. EXECUÇÃO DE TAREFAS E DECOMPOSIÇÃO DAG

### 6.1 UnifiedExecutionEngine

```python
# execution/unified_engine.py
UnifiedExecutionEngine:
    ├─ ExecutionCoordinator (controle de iteração)
    ├─ ToolExecutionLoop (padrão ReAct)
    ├─ TeamExecutionLoop (sessões colaborativas)
    └─ WorkExecutionLoop (deep work)
```

**Dispatch por estratégia:**

```python
DELEGATE     → _execute_single_agent()
TEAM_SESSION → _execute_team_session()
CHAIN        → _execute_chain()
GRAPH        → _execute_graph()
```

### 6.2 Team Orchestration (4 Fases)

```python
# execution/teams/team_orchestrator.py
TeamOrchestrator:
    Fase 1: DISCUSSION → Agentes discutem e declaram missões
    Fase 2: DAG_BUILD  → Extrai MissionDAG das declarações
    Fase 3: EXECUTION  → Executa missões em paralelo/topológica
    Fase 4: SYNTHESIS   → Sintetiza resultados
```

### 6.3 MissionDAG

```python
# execution/teams/mission_dag.py
MissionDAG:
    - Grafo acíclico direcionado de missões
    - Extraído automaticamente das declarações dos agentes
    - Execução topológica com dependências
```

### 6.4 DecompositionEngine

```python
# decomposition/engine.py
Pipeline: Tasker → Scheduler → Resolver → Synthesizer
- Decompõe tarefas complexas em sub-tarefas
- Agenda execução
- Resolve dependências
- Sintetiza resultados
```

**STATUS:** ✅ Implementado, mas **TEAM_SESSION é auto-ativado apenas por feature flag** e a integração com o IntelligentRouter é condicional (complexity ≥ 0.7).

---

## 7. COMUNICAÇÃO ENTRE AGENTES

### 7.1 CommunicationBus (2 Implementações)

| Implementação | Tecnologia | Status | Uso |
|---------------|------------|--------|-----|
| `InternalCommunicationBus` | asyncio.Queue | ✅ Production Ready | Zero-dependency default |
| `XMPPCommunicationBus` | ejabberd/XMPP | ✅ Implementado | Distributed deployments |

### 7.2 P2P Protocol

```python
# communication/protocols/p2p_protocol.py
P2PMessage:
    - Types: DIRECT, REQUEST, RESPONSE, NOTIFICATION, URGENT
    - Request-response correlation via UUID
    - Urgency levels
    - Message history
```

### 7.3 Team Chat (MUC)

```python
# communication/teams/
team.py       → Team entity
team_chat.py  → Multi-User Chat
team_manager.py → Lifecycle management
```

### 7.4 Agent Communication Mixin

```python
# communication/mixins/agent_communication.py
AgentCommunicationMixin:
    - send_to_teammate() → P2P direto
    - broadcast_to_team() → MUC
    - request_from_teammate() → Request-response
```

### 7.5 Runtime Message Bus

```python
# runtime/message_bus/
protocol.py    → Interface abstrata
redis_bus.py   → Redis pub/sub
rabbitmq_bus.py → RabbitMQ
adapter.py     → Adaptador entre implementações
```

**STATUS:** ✅ Infraestrutura completa implementada, mas **NÃO integrada ao fluxo de roteamento**. O CommunicationBus é inicializado no AgentRuntime mas os agentes não usam ativamente para se comunicar durante orquestração — a comunicação é feita via prompt/delegation, não via message bus real.

---

## 8. IMPLEMENTAÇÕES NÃO INTEGRADAS AO FLUXO PRINCIPAL

### 8.1 Tabela de Integração

| Componente | Implementado | No Fluxo Principal | Gap |
|------------|:---:|:---:|-----|
| IntelligentRouter | ✅ | ✅ | **Centralizado** — gargalo LLM |
| CommunicationBus | ✅ | ❌ | Não usado para roteamento |
| ContextPlus | ✅ | ❌ | Usado só como tool, não no routing |
| Circuit Breakers | ✅ | ❌ | Não informa decisão de roteamento |
| Team Session | ✅ | ⚠️ | Auto-ativado por flag, não por agentes |
| MissionDAG | ✅ | ⚠️ | Usado só em team_session |
| MemoryObserver | ✅ | ❌ | Background, não integrado ao routing |
| DecompositionEngine | ✅ | ⚠️ | Só em thinking_mode=DECOMPOSITION |
| UnifiedExecutionEngine | ✅ | ⚠️ | Adaptador existe mas não é default |
| AgentCommunicationMixin | ✅ | ❌ | Agentes não usam para sugerir tarefas |
| Hook System | ✅ | ⚠️ | Tool hooks sim, agent/team hooks não |
| Runtime Policy | ✅ | ✅ | Usado para definir tools por agente |

### 8.2 Gaps Críticos para o Novo Fluxo

#### GAP 1: IntelligentRouter como Gargalo

**Problema:** O `IntelligentRouter.analyze_intent_with_llm()` é uma chamada LLM centralizada que decide TUDO — agente, estratégia, ferramentas. Os agentes são passivos.

**Solução Proposta:** Transformar o router em um **coordenador de opiniões** onde:

1. Cada agente recebe o contexto e **sugere** o que pode fazer
2. Agentes comunicam via CommunicationBus (já implementado)
3. O Orchestrator coleta as sugestões e decide a tarefa final

#### GAP 2: CommunicationBus Desconectado

**Problema:** O `CommunicationBus` é inicializado mas os agentes não o usam ativamente para propor tarefas ou colaborar durante orquestração.

**Solução Proposta:** Conectar o CommunicationBus ao fluxo de roteamento para que agentes possam:

- Receber broadcast da mensagem do usuário
- Responder com sugestões de tarefas
- Negociar responsabilidades

#### GAP 3: Circuit Breakers Não Informam Roteamento

**Problema:** Os circuit breakers monitoram saúde dos serviços mas não influenciam a decisão de roteamento.

**Solução Proposta:** O IntelligentRouter deve consultar o estado dos circuit breakers antes de delegar para um agente, para evitar rotear para agentes "doentes".

#### GAP 4: ContextPlus Desconectado do Routing

**Problema:** O ContextPlus fornece inteligência de codebase mas é usado apenas como ferramenta dentro dos agentes, não como input para decisão de roteamento.

**Solução Proposta:** O IntelligentRouter deve usar ContextPlus para entender melhor o contexto antes de decidir — ex: "o usuário está perguntando sobre um arquivo específico, o ContextPlus mostra que é um arquivo de teste, então rotear para agente de análise".

#### GAP 5: Agent Communication Mixin Não Utilizado

**Problema:** O `AgentCommunicationMixin` permite P2P e broadcast mas os agentes não usam para sugerir tarefas ao orquestrador.

**Solução Proposta:** Agentes devem poder:

- Receber mensagem do usuário via broadcast
- Avaliar se podem contribuir
- Enviar sugestão ao orquestrador via P2P
- O orquestrador coleta e decide

---

## 9. PROPOSTA: INTELLIGENT ROUTER DESCENTRALIZADO

### 9.1 Arquitetura Atual (Centralizada)

```
User → IntelligentRouter (LLM) → Decision → Agent → Response
              ↑
        Tudo passa aqui
```

### 9.2 Arquitetura Proposta (Descentralizada)

```
User → Router Coordinator
         ↓
    Broadcast via CommunicationBus
         ↓
    ┌─────────┬─────────┬─────────┐
    │ Agent A  │ Agent B  │ Agent C  │
    │ sugere   │ sugere   │ sugere   │
    │ tarefa X │ tarefa Y │ tarefa Z │
    └────┬─────┴────┬─────┴────┬─────┘
         ↓          ↓          ↓
    Router Coordinator coleta sugestões
         ↓
    Orchestrator decide (pode usar LLM para desempate)
         ↓
    Delega para agente(s) escolhido(s)
         ↓
    Agentes executam (podem colaborar via CommunicationBus)
```

### 9.3 Componentes Necessários

1. **AgentProposalProtocol** — Protocolo para agentes enviarem propostas
2. **ProposalCollector** — Coleta propostas via CommunicationBus
3. **ProposalEvaluator** — Avalia propostas (pode usar LLM leve ou heurística)
4. **DecentralizedRouter** — Substitui o IntelligentRouter centralizado

### 9.4 Fluxo de Execução Proposto

```python
async def route_message_decentralized(message, context):
    # 1. Broadcast para todos os agentes
    proposals = await communication_bus.broadcast_and_collect(
        message=message,
        context=context,
        timeout=5.0,
        collect_fn=lambda agent_id, response: Proposal.from_response(agent_id, response)
    )
    
    # 2. Agentes enviam propostas (async, paralelo)
    # Cada agente usa seu runtime_policy para avaliar:
    #   - "Posso resolver isso?"
    #   - "Que ferramentas preciso?"
    #   - "Qual minha confiança?"
    #   - "Preciso de ajuda de outro agente?"
    
    # 3. Avaliar propostas
    if len(proposals) == 1:
        return proposals[0]  # Caso simples
    
    if len(proposals) > 1:
        # Usar LLM leve para desempate OU heurística
        return await evaluate_proposals(proposals, message, context)
    
    # 4. Nenhum agente se propôs → fallback para Orchestrator direto
    return OrchestratorDecision(execution_strategy=DIRECT_RESPONSE)
```

---

## 10. RESUMO EXECUTIVO

### O que está funcionando bem

- ✅ Sistema de memórias (3 camadas) completo
- ✅ Hooks system (27 eventos) robusto
- ✅ Circuit breakers implementados
- ✅ CommunicationBus com 2 implementações
- ✅ Team Orchestration com 4 fases
- ✅ MissionDAG para decomposição
- ✅ ContextPlus para inteligência de codebase

### O que precisa ser integrado

- ❌ CommunicationBus → Roteamento descentralizado
- ❌ Circuit Breakers → Decisão de roteamento
- ❌ ContextPlus → Input para routing
- ❌ Agent Communication Mixin → Sugestão de tarefas
- ⚠️ Team Session → Auto-ativado mas não por agentes
- ⚠️ Hooks de agent/team → Não conectados ao orquestração

### Próximos Passos Recomendados

1. Criar `AgentProposalProtocol` no CommunicationBus
2. Criar `ProposalCollector` e `ProposalEvaluator`
3. Modificar agentes para enviar propostas via CommunicationBus
4. Integrar circuit breaker state no roteamento
5. Integrar ContextPlus como input de contexto para routing
6. Substituir IntelligentRouter centralizado por DecentralizedRouter
