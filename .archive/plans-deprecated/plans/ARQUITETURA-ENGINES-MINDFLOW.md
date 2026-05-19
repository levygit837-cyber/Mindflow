# Arquitetura de Engines no MindFlow

## Visão Geral

O MindFlow tem múltiplas camadas de execução que trabalham juntas, mas não são hierárquicas - cada uma tem um propósito específico.

## 1. QueryEngine (`query/engine.py`)

**Propósito:** Engine unificada para execução de agentes com contexto e delegação.

**Responsabilidades:**
- Context building (GitProvider, FileProvider, MemoryProvider, MCPProvider)
- Token budget enforcement
- File caching via SessionFileCache
- Auto-compact service
- Agent task delegation (herdado do DelegationEngine)
- Workspace isolation via WorkTreeService (herdado do DelegationEngine)
- CommunicationBus para P2P (herdado do DelegationEngine)
- MissionLauncher integration (herdado do DelegationEngine)
- Fallback management (herdado do DelegationEngine)
- Memory-grounded optimization (herdado do DelegationEngine)
- A2A external calls (herdado do DelegationEngine)

**Conexão com outros engines:**
- **NÃO** conecta diretamente ao DecompositionEngine
- Usa MissionLauncher para lançar missões autônomas
- Usa UnifiedExecutionEngine (indiretamente via runtime)

**Status:** ✅ ATIVO - Engine principal para execução de agentes

---

## 2. DecompositionEngine (`decomposition/engine.py`)

**Propósito:** Coordena o pipeline de decomposição de tarefas em DAG (Tasker → Scheduler → Resolver → Synthesizer).

**Responsabilidades:**
- TaskDecomposer: Quebra mensagem do usuário em MainTaskContract + SubTaskContracts
- TaskScheduler: Ordena SubTaskContracts respeitando o grafo de dependências
- TaskResolver: Executa SubTaskContract individual e retorna resultado
- TaskSynthesizerBase: Combina resultados validados em SynthesisContract

**Conexão com outros engines:**
- **NÃO** conecta diretamente ao QueryEngine
- É um sistema separado para decomposição complexa de tarefas
- Pode ser usado por Execution Graphs (graphs/implementations/orchestrator/decomposition.py - atualmente stub)

**Status:** ⚠️ PARCIALMENTE IMPLEMENTADO - Engine existe mas o graph de decomposition é apenas stub

---

## 3. UnifiedExecutionEngine (`execution/unified_engine.py`)

**Propósito:** Engine centralizada para todas as estratégias de execução (DELEGATE, TEAM_SESSION, CHAIN, GRAPH, DIRECT_RESPONSE).

**Responsabilidades:**
- ExecutionCoordinator: Controle de iteração global
- ToolExecutionLoop: Padrão ReAct
- TeamExecutionLoop: Sessões colaborativas
- WorkExecutionLoop: Deep work

**Conexão com outros engines:**
- **NÃO** conecta diretamente ao QueryEngine
- É usado pelo runtime (runtime/streaming/stream.py, runtime/execution/executor.py)
- Usa MissionLauncher para missões autônomas
- Usa TeamOrchestrator para sessões colaborativas

**Status:** ✅ ATIVO - Engine central para execução de estratégias

---

## 4. MissionLauncher (`execution/missions/mission_launcher.py`)

**Propósito:** Lança missões autônomas via Execution Graphs.

**Responsabilidades:**
- Seleciona graph correto baseado em MissionGraphType
- Valida se agente pode executar mission_type via RuntimePolicy
- Cria contexto de execução
- Executa graph e retorna resultado estruturado

**Conexão com outros engines:**
- Usado por QueryEngine (lazy init)
- Usado por TeamOrchestrator
- Usado por UnifiedExecutionEngine
- **NÃO** conecta ao DecompositionEngine

**Status:** ✅ ATIVO - Componente para lançamento de missões

---

## 5. TeamOrchestrator (`execution/teams/team_orchestrator.py`)

**Propósito:** Coordena sessões colaborativas multi-agente (Formation → Discussion → Missions → Synthesis).

**Responsabilidades:**
- TeamManager: Gerenciamento de times
- MissionDAG: Grafo de dependências de missões
- MemoryObserver: Integração com memória

**Conexão com outros engines:**
- Usa MissionLauncher para lançar missões
- Usado por UnifiedExecutionEngine (estratégia TEAM_SESSION)
- **NÃO** conecta ao QueryEngine diretamente
- **NÃO** conecta ao DecompositionEngine

**Status:** ✅ ATIVO - Coordenação de sessões colaborativas

---

## 6. DelegationEngine (REMOVIDO)

**Propósito:** Engine legada para delegação de tarefas a agentes especialistas.

**Status:** ❌ REMOVIDO - Funcionalidade migrada para QueryEngine

---

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         Runtime Layer                             │
│  (runtime/streaming/stream.py, runtime/execution/executor.py)    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   UnifiedExecutionEngine                          │
│         (execution/unified_engine.py)                             │
│  - Coordena estratégias: DELEGATE, TEAM_SESSION, CHAIN, GRAPH  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
│  QueryEngine     │ │ TeamOrchestrator │ │ MissionLauncher │
│ (query/engine.py)│ │ (teams/team_     │ │ (missions/       │
│                 │ │  orchestrator.py) │ │  mission_        │
│ - Context build │ │ - Formation       │ │  launcher.py)   │
│ - Token budget   │ │ - Discussion      │ │ - Launch graphs  │
│ - Agent delegate │ │ - Missions        │ │ - Validate agent │
│ - MissionLauncher│ │ - Synthesis       │ │                 │
└──────────────────┘ └────────┬───────┘ └────────┬─────────┘
                            │                   │
                            │                   ▼
                            │         ┌─────────────────────┐
                            │         │ Execution Graphs    │
                            │         │ (graphs/...)          │
                            │         │ - Analysis           │
                            │         │ - Deep Investigation │
                            │         │ - Coding Task        │
                            │         │ - Bug Fix            │
                            │         └─────────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ DecompositionEngine   │
                 │ (decomposition/       │
                 │  engine.py)            │
                 │ - Tasker             │
                 │ - Scheduler           │
                 │ - Resolver            │
                 │ - Synthesizer         │
                 │                       │
                 │ STATUS: ⚠️ PARCIAL    │
                 │ (graph é stub)        │
                 └─────────────────────┘
```

## Conclusão

1. **QueryEngine** é o engine principal para execução de agentes com contexto e delegação. Ele **NÃO** conecta diretamente ao DecompositionEngine.

2. **DecompositionEngine** é um sistema separado para decomposição complexa de tarefas em DAG. Atualmente está parcialmente implementado (o graph é apenas stub).

3. **UnifiedExecutionEngine** é a engine central que coordena todas as estratégias de execução. É usado pelo runtime e conecta MissionLauncher e TeamOrchestrator.

4. **MissionLauncher** é um componente compartilhado usado por QueryEngine, UnifiedExecutionEngine e TeamOrchestrator para lançar missões autônomas via Execution Graphs.

5. **TeamOrchestrator** coordena sessões colaborativas multi-agente e usa MissionLauncher para lançar missões.

6. **DelegationEngine** foi removido e sua funcionalidade foi migrada para QueryEngine.

## Próximos Passos Sugeridos

1. Completar a implementação do DecompositionGraph (atualmente é stub)
2. Integrar DecompositionEngine com Execution Graphs
3. Decidir se DecompositionEngine deve ser integrado ao QueryEngine ou manter separado
4. Documentar melhor as conexões entre os engines
