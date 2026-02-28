# Stream Filter, Ordering & Structured Output — Design Doc

**Data:** 2026-02-24
**Escopo:** Correção de repetição de mensagens + ordenação correta de eventos + categorização de output para visualização futura

---

## 1. Diagnóstico dos Problemas

### 1.1 Repetição de mensagens no segundo turno

**Causa raiz:** O LangGraph no modo `messages` re-emite **todas as mensagens do thread** a cada turno — não só as novas. O `processMessageMode` do normalizer processa tudo sem distinguir se a mensagem pertence ao turno atual ou a um turno anterior.

**Evidência no código:**
```
route.ts → agent.stream({ messages: [new HumanMessage(msg)] }, { streamMode: ["messages", "updates"] })
         ↓
LangGraph emite: [msg_antiga_1, meta], [msg_antiga_2, meta], [novo_token, meta]
         ↓
normalizer.process() → emite tudo para o frontend → frontend exibe histórico novamente ❌
```

O `run_id` no metadata de cada evento identifica o turno atual — hoje não é usado para filtragem.

### 1.2 Tool aparece abaixo da resposta (ordering errado)

**Causa raiz:** O LangGraph entrega eventos em duas ondas:
1. **`messages` mode** — tokens do LLM chegam em tempo real (incluindo `tool_call_chunks` parciais)
2. **`updates` mode** — estado consolidado do nó chega depois, com as `tool_calls` completas

O normalizer processa na ordem de chegada. Resultado: a `tool_call` emitida via `updates` chega *depois* dos tokens de resposta emitidos via `messages`, fazendo o bloco de ferramenta aparecer embaixo da resposta no frontend.

### 1.3 Output do modelo "seco" sem categorização

**Causa raiz:** Toda resposta textual é tratada como `type: "response"` genérico. Um agente de código produz tipos muito distintos de output (explicação, decisão, código executado, resumo de resultado) mas o frontend os renderiza todos igual.

---

## 2. Arquitetura da Solução

### 2.1 Turn-Scoped Stream Filter

**Mecanismo:** O `route.ts` captura o `run_id` do **primeiro evento** do stream (disponível em `metadata.run_id` nos eventos `messages`). Esse `run_id` é o identificador único do turno atual. Ele é passado ao normalizer como `currentTurnRunId`.

O normalizer filtra na camada `processMessageMode`: qualquer evento cujo `metadata.run_id` não bata com `currentTurnRunId` é ignorado para emissão SSE — mas **ainda é logado** via `logBus.publish()` para rastreabilidade completa.

```
Turno 2:
  [msg_antiga, { run_id: "run-aaa" }]  → run_id ≠ currentTurnRunId → LOG ONLY, não emite SSE
  [msg_antiga, { run_id: "run-aaa" }]  → run_id ≠ currentTurnRunId → LOG ONLY, não emite SSE
  [novo_token, { run_id: "run-bbb" }]  → run_id = currentTurnRunId → EMITE SSE ✓
```

**Por que isso não quebra o contexto:** O histórico vive no `PostgresSaver` (checkpoint do LangGraph). A filtragem é puramente na camada de transporte SSE. O agente continua recebendo o thread completo internamente.

**Captura do `run_id`:** O `route.ts` usa o primeiro item do stream para extrair o `run_id` antes de iniciar o processamento, ou o normalizer detecta o primeiro `run_id` visto e o adota como `currentTurnRunId` (lazy detection — mais simples, sem mudança na assinatura do `route.ts`).

### 2.2 Event Priority Queue com Retroactive Insert

**Mecanismo:** O normalizer mantém uma fila interna de eventos por turno com dois canais:

- **Canal live (streaming):** `thought` e `response` são emitidos imediatamente ao chegar (token-a-token). Não esperam.
- **Canal deferred (batch):** `tool_call` e `tool_result` vindos de `updates` são enfileirados com um timestamp de "quando deveriam ter aparecido" (antes do primeiro `response` do turno).

Ao emitir um `tool_call` do canal deferred, o evento SSE carrega `meta.insertBefore: <id_do_primeiro_response>`. O frontend usa esse campo para inserir o bloco de ferramenta na posição correta na lista de `contentParts`, em vez de appended no final.

```
Stream de eventos SSE para o frontend (ordem de chegada):
  1. thought "vou usar search_web..."           → emite imediatamente
  2. response "Com base na pesquisa..."         → emite imediatamente, id: "part-5"
  3. tool_call search_web { insertBefore: "part-5" }  → frontend insere ANTES de part-5 ✓
  4. tool_result search_web                     → frontend insere APÓS tool_call ✓
```

O `agent-store.ts` ganha uma ação `insertPartBefore(messageId, targetPartId, newPart)` que percorre `contentParts` e insere na posição correta.

### 2.3 Structured Output Categories

**Mecanismo:** Um novo módulo `output-categorizer.ts` analisa o texto de resposta e atribui uma categoria heurística. Isso roda no normalizer antes de emitir o evento `response`.

**Categorias definidas:**

| Categoria | Critério heurístico | Exemplo |
|-----------|--------------------|---------|
| `explanation` | texto informativo puro, sem ação | "O LangGraph usa checkpoints para..." |
| `decision` | começa com "I'll", "Let me", "I'm going to", "Vou" | "Vou usar o search_web para..." |
| `code_result` | contém bloco de código ```...``` | resultado de ferramenta com código |
| `summary` | começa com "Here's", "Aqui está", "The result", "O resultado" | "Aqui está o que encontrei:" |
| `response` | fallback genérico | qualquer outro |

A categoria vai em `meta.category` do `StreamEvent`. O frontend pode usar para estilização futura — hoje renderiza igual, sem breaking change.

**Nota sobre futuro:** Quando quiser categorias precisas (para grafos customizados ou sub-agent progress), substitui o heurístico por structured output com `withStructuredOutput()` do LangChain — a interface `meta.category` já estará no contrato.

---

## 3. Mapeamento Completo dos Stream Modes do LangGraph

Para o logger ter acesso a tudo:

| Stream Mode | O que emite | Shape do item | Uso atual | No logger |
|------------|------------|--------------|-----------|-----------|
| `messages` | Tokens LLM + metadata | `[MessageChunk, { run_id, langgraph_node, langgraph_step, ... }]` | ✅ processMessageMode | ✅ já logado |
| `updates`  | Estado delta por nó | `{ nodeName: { messages: [...] } }` | ✅ processUpdatesMode | ✅ já logado |
| `custom`   | Dados arbitrários de nodes/tools | qualquer objeto | ✅ processCustomMode | ✅ já logado |
| `values`   | Estado completo após cada step | `{ messages: [...], ... }` | ❌ não usado | deve ser logado |
| `debug`    | Info detalhada de execução | `{ type: "task"|"task_result"|"checkpoint", ... }` | ❌ não usado | deve ser logado |

**Metadata disponível em `messages` mode:**
```typescript
{
  run_id: string,           // ID único do turno atual ← chave do Turn Filter
  langgraph_node: string,   // nome do nó que emitiu
  langgraph_step: number,   // número do step no grafo
  langgraph_triggers: string[],
  langgraph_path: string[],
  langgraph_checkpoint_ns: string,
  ls_model_name?: string,
  ls_provider?: string,
}
```

**Eventos do `debug` mode:**
```
{ type: "task",        payload: { id, name, input, ... } }
{ type: "task_result", payload: { id, name, result, ... } }
{ type: "checkpoint",  payload: { config, metadata, values, ... } }
```

**Plano para o logger:** Adicionar `values` e `debug` ao `streamMode` do `route.ts` somente para o `logBus` — o normalizer ignora esses modos para emissão SSE.

---

## 4. Contratos de Interface

### 4.1 StreamEvent (adições apenas — sem breaking change)

```typescript
export interface StreamEvent {
  id: string;
  seq: number;
  type: StreamEventType;
  mode: StreamModeName;
  data: string;
  meta?: {
    // existentes
    runId?: string;
    parentRunId?: string;
    node?: string;
    nodeCategory?: string;
    toolCallId?: string;
    provider?: LLMProvider;
    model?: string;
    status?: "start" | "update" | "end";
    path?: string[];
    // NOVOS
    turnRunId?: string;       // run_id do turno atual (para debug)
    insertBefore?: string;    // id do ContentPart antes do qual inserir
    category?: OutputCategory; // categoria heurística do output
  };
}

export type OutputCategory =
  | "explanation"
  | "decision"
  | "code_result"
  | "summary"
  | "response"; // fallback
```

### 4.2 StreamModeName (expansão)

```typescript
export type StreamModeName = "updates" | "messages" | "custom" | "values" | "debug";
```

### 4.3 AgentStore — nova ação

```typescript
insertPartBefore: (messageId: string, targetPartId: string, newPart: ContentPart) => void;
```

### 4.4 ChatStreamNormalizerOptions (adições)

```typescript
export interface ChatStreamNormalizerOptions {
  provider: LLMProvider;
  emitUpdateSteps?: boolean;
  emit: (...) => void;
  // NOVO — se omitido, o normalizer detecta automaticamente pelo primeiro run_id visto
  currentTurnRunId?: string;
}
```

---

## 5. Estrutura de Arquivos

```
src/
  lib/agent/
    chat-stream-normalizer.ts     ← turn filter + lazy run_id detection
    stream-event-queue.ts         ← NOVO: deferred queue com insertBefore
    output-categorizer.ts         ← NOVO: heurísticas de categoria
  types/
    agent.ts                      ← OutputCategory, insertBefore, turnRunId, values/debug modes
  stores/
    agent-store.ts                ← nova ação insertPartBefore
  hooks/
    use-agent-chat.ts             ← handler para insertBefore no case "tool_call"/"tool_result"
```

Nenhum arquivo novo na camada de API (`route.ts` recebe mudança mínima apenas para expandir `streamMode` com `values`/`debug` logados).

---

## 6. Fluxo Completo Após as Mudanças

```
Usuario envia msg 2
        ↓
route.ts → agent.stream({ streamMode: ["messages", "updates", "values", "debug"] })
        ↓
LangGraph emite todos os eventos do thread
        ↓
normalizer.process(item)
  ├─ mode: "messages"
  │    ├─ detecta run_id → seta currentTurnRunId na primeira vez
  │    ├─ SE run_id ≠ currentTurnRunId → logBus.publish() APENAS, return
  │    ├─ SE thought → emite SSE imediatamente
  │    ├─ SE response → emite SSE imediatamente + categoriza
  │    └─ SE tool tokens → enfileira no stream-event-queue
  │
  ├─ mode: "updates"
  │    ├─ tool_call completo → stream-event-queue.enqueue(tool_call, { insertBefore: firstResponsePartId })
  │    └─ tool_result → stream-event-queue.enqueue(tool_result)
  │
  ├─ mode: "values"  → logBus.publish() APENAS
  └─ mode: "debug"   → logBus.publish() APENAS
        ↓
normalizer.flush()
  └─ stream-event-queue.drain() → emite tool_calls/results com meta.insertBefore
        ↓
Frontend (use-agent-chat.ts)
  ├─ case "response"    → store.appendToAssistant() [igual a hoje]
  ├─ case "thought"     → store.appendThought() [igual a hoje]
  ├─ case "tool_call"
  │    ├─ SE meta.insertBefore → store.insertPartBefore(assistantId, meta.insertBefore, toolCallPart)
  │    └─ SE não → store.addToolCall() [igual a hoje, fallback]
  └─ case "tool_result"
       └─ store.updateToolResult() [igual a hoje]
```

---

## 7. O que NÃO muda

- Contrato base do `StreamEvent` (sem remoção de campos)
- Store do Zustand (só adição de `insertPartBefore`)
- Checkpoint do LangGraph — contexto do agente intacto
- `node-registry.ts`, `dynamic-prompt.ts` — não tocados
- Testes existentes — sem regressão esperada

---

## 8. Critérios de Sucesso

1. Enviar 3 mensagens seguidas — nenhuma repete conteúdo de turno anterior
2. Usar `search_web` — bloco da ferramenta aparece **acima** da resposta final
3. Logs contêm todos os stream modes (`values`, `debug`, `updates`, `messages`, `custom`)
4. `meta.category` presente em todos os eventos `response` emitidos
5. Testes unitários passando: `turn-filter`, `stream-event-queue`, `output-categorizer`
6. Nenhum breaking change no frontend observado nas respostas sem tool calls
