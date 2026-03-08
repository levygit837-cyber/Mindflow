# Arquitetura: Fluxo de Conversa, Chains e Graphs

## 1. Fluxo de Conversa Atual

### 1.1 Visão Geral

O sistema atual opera em **modo ChatBot** com decisão centralizada pelo Orquestrador:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUXO ATUAL (Simple ChatBot)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  POST /v1/agent/chat/stream                                                 │
│         │                                                                    │
│         ▼                                                                    │
│  AgentController.stream_chat()                                                │
│         │                                                                    │
│         ▼                                                                    │
│  LocalAgentClient.stream_chat()  ──► gRPC / Runtime                          │
│         │                                                                    │
│         ▼                                                                    │
│  build_simple_orchestrator_flow()                                             │
│         │                                                                    │
│         ├──► route_node: route_message_intelligently()                       │
│         │         │                                                          │
│         │         ├── analyze_intent_with_llm()  (LLM analisa intent)        │
│         │         ├── Se needs_code_context → delegate Analyst               │
│         │         ├── is_multi_agent? → _handle_multi_agent_task()           │
│         │         └── else → _handle_single_agent_task()                     │
│         │                                                                    │
│         ├──► execute_node:                                                   │
│         │         ├── thinking_mode == DECOMPOSITION?                         │
│         │         │       └── _run_task_pipeline() (Tasker→Scheduler→Resolver│
│         │         │           →Synthesizer) — DAG interno                    │
│         │         └── else: get_agent(decision.agent) → LLM.ainvoke()         │
│         │                                                                    │
│         └──► respond_node: pass-through                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Componentes Principais

| Componente | Responsabilidade | Localização |
|------------|-----------------|-------------|
| **Orquestrador** | Decisor central: analisa intent, escolhe agente, delega | `orchestrator/routing/intelligent_router.py` |
| **Router** | `route_message()` → `route_message_intelligently()` | `orchestrator/routing/router.py` |
| **Graph** | `SimpleOrchestratorGraph`: route → execute → respond (linear) | `graphs/implementations/orchestrator/simple_flow.py` |
| **Decomposition** | Pipeline interno para tarefas complexas (Tasker→Scheduler→Resolver→Synthesizer) | `orchestrator/graph.py` + `decomposition/pipeline/` |
| **Especialistas** | Coder, Analyst, Researcher (catálogo em `agents/_registry`) | `agents/specialists/` |

### 1.3 Modos de Execução Atuais

1. **Single Agent (ChatBot simples)**
   - Router escolhe 1 agente → Execute invoca LLM com prompt do agente → Resposta

2. **Decomposition Thinking** (quando `complexity_score` alto)
   - Tasker decompõe em sub-tarefas
   - Scheduler ordena (topological sort)
   - Resolver executa cada sub-tarefa com contexto semântico
   - Synthesizer combina resultados
   - **É um DAG interno**, mas não exposto como Graph reutilizável

3. **Multi-Agent (parcial)**
   - `IntentAnalysis.is_multi_agent` e `agent_sequence` existem
   - `_handle_multi_agent_task()` executa **apenas o primeiro agente** da sequência
   - TODO: "Implement full multi-agent coordination in Phase 2"

### 1.4 Schemas Relevantes

- **OrchestratorDecision** (`schemas/orchestration/orchestrator.py`):
  - `agent`, `task`, `thinking_mode`, `tools`, `chain: list[ChainStep]`
  - O campo `chain` existe mas **não é usado** no fluxo atual

- **ChainStep** (orchestrator): `agent`, `task`, `tools` — passo em uma chain multi-agente

---

## 2. O que Já Existe: Chains e Graphs

### 2.1 Módulo Chains (`chains/`)

| Classe/Conceito | Descrição | Status |
|-----------------|-----------|--------|
| **BaseChain** | ABC para chains com `add_step`, `execute`, `validate` | ✅ Implementado |
| **ChainType** | SEQUENTIAL, PARALLEL, CONDITIONAL, LOOPING, ADAPTIVE | ✅ Definido |
| **ChainStep** (chains) | `step_id`, `step_type`, `agent`, `depends_on`, `condition` | ✅ Definido |
| **SequentialChain** | Executa steps em ordem | ✅ Parcial (placeholder em `_execute_step`) |
| **SequentialChainBuilder** | Builder para chains sequenciais | ✅ Implementado |
| **ConditionalChainBuilder** | Builder para chains condicionais | ✅ Exportado |
| **CodingChain** | Template: analyze → design → implement → review → test | ✅ Template |
| **ResearchChain** | Template para pesquisa | ✅ Exportado |
| **ChainManager** | Gerenciamento de instâncias | ✅ Exportado |

**Problema**: Chains não estão **conectadas** ao fluxo de orquestração. O Orquestrador não usa `ChainManager` nem `BaseChain`.

### 2.2 Módulo Graphs (`graphs/`)

| Classe/Conceito | Descrição | Status |
|-----------------|-----------|--------|
| **BaseGraph** | ABC com `add_node`, `add_connection`, `execute` | ✅ Implementado |
| **GraphType** | SIMPLE, CONDITIONAL, PARALLEL, CYCLIC, DECOMPOSITION | ✅ Definido |
| **SimpleOrchestratorGraph** | route → execute → respond (linear) | ✅ Em uso |
| **SequentialWorkflowGraph** | Workflow sequencial | ✅ Implementado |
| **ParallelWorkflowGraph** | Workflow paralelo | ✅ Implementado |
| **ConditionalWorkflowGraph** | Workflow condicional | ✅ Implementado |
| **MultiAgentGraph** | Graph multi-agente | ❌ Importado mas **arquivo não existe** |
| **DecompositionGraph** | Graph de decomposição | ❌ Importado mas **arquivo não existe** |

**Problema**: `MultiAgentGraph` e `DecompositionGraph` são importados em `graphs/implementations/orchestrator/__init__.py` mas os arquivos `multi_agent.py` e `decomposition.py` **não existem** (provavelmente causando ImportError).

---

## 3. Diferença Conceitual: ChatBot vs Chains vs Graphs

### 3.1 ChatBot (Estado Atual)

- **Fluxo**: 1 mensagem → 1 decisão → 1 agente → 1 resposta
- **Características**:
  - Linear, stateless por turno
  - Orquestrador decide uma vez por mensagem
  - Exceção: Decomposition usa pipeline interno (DAG) mas é transparente

### 3.2 Chains (Sequências Predefinidas)

- **Fluxo**: Sequência fixa ou condicional de passos
- **Características**:
  - Steps com `depends_on`, `condition`
  - Output de um step → input do próximo
  - **Predefinido**: CodingChain = analyze → design → implement → review
  - Orquestrador pode **selecionar uma Chain** em vez de um agente único

**Exemplo de uso**:
```
User: "Implemente um módulo de autenticação"
→ Orquestrador escolhe CodingChain
→ Chain: Analyst (requirements) → Coder (implement) → Analyst (review) → Coder (tests)
```

### 3.3 Graphs (Fluxos com Topologia)

- **Fluxo**: DAG ou grafo com ramificações, paralelismo, ciclos controlados
- **Características**:
  - Nós = agentes ou sub-graphs
  - Arestas = dependências ou condições
  - **Dinâmico**: estrutura pode ser gerada (ex: decomposição)
  - Suporta paralelismo (vários agentes ao mesmo tempo)

**Exemplo de uso**:
```
User: "Analise segurança, performance e documentação do projeto"
→ Orquestrador gera DecompositionGraph
→ Tasker decompõe em 3 sub-tarefas independentes
→ Graph: [Analyst(security) | Analyst(perf) | Researcher(docs)] → Synthesizer
```

---

## 4. Proposta: Como Integrar Chains e Graphs

### 4.1 Decisão do Orquestrador (Expandida)

O `OrchestratorDecision` ou um novo schema deve suportar:

```python
class ExecutionStrategy(StrEnum):
    SINGLE_AGENT = "single_agent"      # ChatBot atual
    CHAIN = "chain"                     # Executar uma Chain predefinida
    GRAPH = "graph"                     # Executar um Graph (DAG)

class OrchestratorDecision(BaseModel):
    # ... campos existentes ...
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SINGLE_AGENT
    chain_id: str | None = None         # Se CHAIN: qual chain
    graph_id: str | None = None         # Se GRAPH: qual graph
    chain: list[ChainStep] = []         # Se CHAIN dinâmica: passos
```

### 4.2 Fluxo Proposto no execute_node

```python
async def execute_node(state: OrchestratorState) -> dict[str, Any]:
    decision = state["decision"]
    
    if decision.execution_strategy == ExecutionStrategy.SINGLE_AGENT:
        return await _execute_single_agent(state, decision)
    
    elif decision.execution_strategy == ExecutionStrategy.CHAIN:
        chain = get_chain_manager().get_chain(decision.chain_id) or _build_chain_from_steps(decision.chain)
        context = {"message": state["message"], "session_id": state["session_id"], ...}
        result = await chain.execute(context)
        return {"response": result.get("final_response"), "error": None}
    
    elif decision.execution_strategy == ExecutionStrategy.GRAPH:
        graph = get_graph_factory().get_graph(decision.graph_id) or _build_decomposition_graph(state)
        graph_state = graph.create_state(...)
        result = await graph.execute(graph_state)
        return {"response": result.get("response"), "error": None}
```

### 4.3 Quando Usar Cada Estratégia

| Critério | Single Agent | Chain | Graph |
|----------|--------------|-------|-------|
| Complexidade | Baixa | Média (workflow conhecido) | Alta (multi-facetada) |
| Estrutura | 1 agente | Sequência fixa/condicional | DAG com paralelismo |
| Exemplo | "Corrija este bug" | "Implemente feature X" | "Audite projeto completo" |
| IntentAnalysis | `is_multi_agent=False` | `suggested_chain="coding"` | `requires_decomposition=True` |

### 4.4 Integração com IntentAnalysis

O `IntentAnalysis` do intelligent_router já tem:
- `is_multi_agent`
- `agent_sequence`

Proposta de extensão:
```python
class IntentAnalysis(BaseModel):
    # ... existentes ...
    suggested_chain: str | None = None      # "coding", "research", "review"
    requires_decomposition: bool = False    # Gerar DAG dinâmico
    parallelizable_subtasks: list[str] = [] # Para Graph paralelo
```

---

## 5. Roadmap de Implementação

### Fase 1: Corrigir e Conectar (Prioridade Alta)

1. **Criar `MultiAgentGraph`** e **`DecompositionGraph`** (ou remover imports quebrados)
2. **Conectar Chains ao Orquestrador**: quando `chain` em `OrchestratorDecision` não vazio, executar como Chain
3. **Implementar `_handle_multi_agent_task` completo**: iterar sobre `agent_sequence` e passar contexto entre agentes

### Fase 2: Estratégias Explícitas

1. Adicionar `ExecutionStrategy` e `chain_id`/`graph_id` em `OrchestratorDecision`
2. Estender `IntentAnalysis` com `suggested_chain` e `requires_decomposition`
3. Atualizar `execute_node` para ramificar por estratégia

### Fase 3: Chains e Graphs Completos

1. **Chains**: Garantir que `SequentialChain._execute_step` invoque agentes reais (não placeholder)
2. **Graphs**: `DecompositionGraph` deve encapsular o pipeline Tasker→Scheduler→Resolver→Synthesizer
3. **MultiAgentGraph**: Graph com nós = agentes, arestas = dependências de contexto

---

## 6. Resumo Visual

```
                    ┌─────────────────────────────────────┐
                    │         ORQUESTRADOR (Decisor)       │
                    │  route_message_intelligently()       │
                    └─────────────────┬───────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  SINGLE AGENT    │       │     CHAIN        │       │     GRAPH       │
│  (ChatBot)       │       │  (Sequência)     │       │  (DAG)          │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ 1 msg → 1 agent │       │ Step1 → Step2 →  │       │  [A]──┐         │
│ → 1 resposta    │       │ Step3 → ...       │       │   │   ├→[Synth] │
│                 │       │                  │       │  [B]──┤         │
│ Estado atual ✅  │       │ ChainManager     │       │   │   │         │
│                 │       │ CodingChain, etc  │       │  [C]──┘         │
│                 │       │                  │       │                 │
│                 │       │ Parcial ⚠️       │       │ Decomposition   │
│                 │       │                  │       │ pipeline ✅     │
│                 │       │                  │       │ MultiAgent ❌   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

---

## 7. Referências no Código

| Conceito | Arquivo |
|----------|---------|
| Fluxo principal | `orchestrator/graph.py` (route_node, execute_node) |
| Router inteligente | `orchestrator/routing/intelligent_router.py` |
| Decomposition pipeline | `orchestrator/graph.py` (_run_task_pipeline) |
| Tasker/Scheduler/Resolver | `decomposition/pipeline/` |
| Chains base | `chains/base/chain.py`, `chains/base/step.py` |
| Chain templates | `chains/templates/coding_chain.py` |
| Graphs base | `graphs/base/graph.py`, `graphs/base/types.py` |
| Simple flow | `graphs/implementations/orchestrator/simple_flow.py` |
