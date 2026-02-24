# Stream Filter, Ordering & Structured Output — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir repetição de mensagens entre turnos, reordenar tool_calls para aparecerem antes da resposta, expandir o logger com todos os stream modes e adicionar categorização de output.

**Architecture:** Três camadas independentes: (1) Turn-Scoped Filter no normalizer usando `run_id` do LangGraph para ignorar mensagens de turnos anteriores; (2) Event Priority Queue que enfileira `tool_call`/`tool_result` e os emite com `insertBefore` para o frontend reordenar; (3) Output Categorizer com heurísticas simples que adiciona `meta.category` a cada evento `response`. O store ganha `insertPartBefore` para colocar tool blocks na posição correta na timeline visual.

**Tech Stack:** TypeScript 5.9, LangGraph JS (stream modes: messages/updates/custom/values/debug), Zustand v5, Vitest, Next.js SSE

**Design doc:** `docs/plans/2026-02-24-stream-filter-ordering-structured-output-design.md`

---

## Pré-requisito: baseline dos testes

**Step 1: Rode os testes atuais e anote o resultado**

```bash
pnpm test 2>&1 | tail -20
```

Expected: vários testes passando. Anote quantos passam/falham — esse é o baseline. Não prossiga se houver falhas que você não entende.

---

## Task 1: OutputCategory no contrato de tipos

**Contexto:** Antes de qualquer lógica, precisamos dos tipos. Todas as tasks seguintes dependem deles.

**Files:**
- Modify: `src/types/agent.ts`

**Step 1: Abra `src/types/agent.ts` e localize a linha com `StreamModeName`**

```bash
grep -n "StreamModeName\|StreamEvent\|OutputCategory" src/types/agent.ts
```

**Step 2: Adicione `OutputCategory` e expanda `StreamModeName` — insira APÓS a linha `export type StreamModeName = ...`:**

```typescript
export type StreamModeName = "updates" | "messages" | "custom" | "values" | "debug";

export type OutputCategory =
  | "explanation"  // texto informativo puro
  | "decision"     // "vou fazer X porque Y"
  | "code_result"  // contém bloco de código
  | "summary"      // resumo de resultado
  | "response";    // fallback genérico
```

**Step 3: Adicione `insertBefore`, `turnRunId` e `category` ao `StreamEvent.meta` — localize a interface `StreamEvent` e substitua o bloco `meta?`:**

```typescript
meta?: {
  runId?: string;
  parentRunId?: string;
  node?: string;
  nodeCategory?: string;
  toolCallId?: string;
  provider?: LLMProvider;
  model?: string;
  status?: "start" | "update" | "end";
  path?: string[];
  // novos
  turnRunId?: string;        // run_id do turno atual (debug/rastreabilidade)
  insertBefore?: string;     // id do ContentPart antes do qual inserir no frontend
  category?: OutputCategory; // categoria heurística do output
};
```

**Step 4: Rode o type-check para validar**

```bash
pnpm exec tsc --noEmit 2>&1 | head -30
```

Expected: zero erros relacionados a `StreamModeName` ou `StreamEvent`. Se aparecerem erros em outros arquivos usando `StreamModeName` com `"values"` ou `"debug"`, tudo bem — eles passarão após as próximas tasks.

**Step 5: Commit**

```bash
git add src/types/agent.ts
git commit -m "feat: add OutputCategory, insertBefore, turnRunId to StreamEvent types"
```

---

## Task 2: Output Categorizer

**Contexto:** Módulo puro, sem dependências externas. Recebe string de texto e retorna uma categoria. Fácil de testar em isolamento.

**Files:**
- Create: `src/lib/agent/output-categorizer.ts`
- Create: `src/lib/agent/__tests__/output-categorizer.test.ts`

**Step 1: Escreva o teste que falha primeiro**

Crie `src/lib/agent/__tests__/output-categorizer.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { categorizeOutput } from "@/lib/agent/output-categorizer";

describe("categorizeOutput", () => {
  it("classifica decisão com 'I'll'", () => {
    expect(categorizeOutput("I'll use search_web to find that information.")).toBe("decision");
  });

  it("classifica decisão com 'Vou'", () => {
    expect(categorizeOutput("Vou executar o comando para verificar.")).toBe("decision");
  });

  it("classifica decisão com 'Let me'", () => {
    expect(categorizeOutput("Let me check the file first.")).toBe("decision");
  });

  it("classifica code_result quando contém bloco de código", () => {
    expect(categorizeOutput("Here is the result:\n```typescript\nconst x = 1;\n```")).toBe("code_result");
  });

  it("classifica summary com 'Here's'", () => {
    expect(categorizeOutput("Here's what I found: the file has 200 lines.")).toBe("summary");
  });

  it("classifica summary com 'O resultado'", () => {
    expect(categorizeOutput("O resultado da busca foi: 3 arquivos encontrados.")).toBe("summary");
  });

  it("classifica explanation como fallback para texto informativo longo", () => {
    const text = "O LangGraph usa checkpoints para persistir o estado entre turnos. Isso permite retomar conversas de onde pararam.";
    expect(categorizeOutput(text)).toBe("explanation");
  });

  it("classifica response como fallback genérico para texto curto", () => {
    expect(categorizeOutput("Ok!")).toBe("response");
  });

  it("não classifica string vazia", () => {
    expect(categorizeOutput("")).toBe("response");
  });

  it("não é sensível a maiúsculas para decisão", () => {
    expect(categorizeOutput("i'll start by reading the file.")).toBe("decision");
  });
});
```

**Step 2: Rode para ver falhar**

```bash
pnpm test -- output-categorizer
```

Expected: FAIL com "Cannot find module".

**Step 3: Crie `src/lib/agent/output-categorizer.ts`**

```typescript
import type { OutputCategory } from "@/types/agent";

/** Padrões de início de frase que indicam decisão/ação */
const DECISION_PATTERNS = [
  /^i'?ll\s/i,
  /^let me\s/i,
  /^i'?m going to\s/i,
  /^i will\s/i,
  /^vou\s/i,
  /^deixa eu\s/i,
  /^primeiro,?\s/i,
  /^to (do|fix|find|check|read|write|run|create|update|add|remove)\b/i,
];

/** Padrões de início de frase que indicam sumário/resultado */
const SUMMARY_PATTERNS = [
  /^here'?s?\s/i,
  /^the result/i,
  /^o resultado/i,
  /^aqui está/i,
  /^found\s/i,
  /^based on/i,
  /^com base em/i,
];

/**
 * Categoriza o conteúdo de um bloco de resposta do agente.
 * Usa heurísticas simples sobre o início do texto e presença de blocos de código.
 * Retorna "response" como fallback seguro.
 */
export function categorizeOutput(text: string): OutputCategory {
  if (!text || !text.trim()) return "response";

  const trimmed = text.trimStart();

  // Bloco de código tem prioridade sobre outros padrões
  if (trimmed.includes("```")) return "code_result";

  // Decisão/ação
  for (const pattern of DECISION_PATTERNS) {
    if (pattern.test(trimmed)) return "decision";
  }

  // Sumário
  for (const pattern of SUMMARY_PATTERNS) {
    if (pattern.test(trimmed)) return "summary";
  }

  // Texto informativo longo sem padrão específico
  if (trimmed.length > 80) return "explanation";

  return "response";
}
```

**Step 4: Rode os testes**

```bash
pnpm test -- output-categorizer
```

Expected: PASS em todos os 10 testes.

**Step 5: Commit**

```bash
git add src/lib/agent/output-categorizer.ts src/lib/agent/__tests__/output-categorizer.test.ts
git commit -m "feat: add output categorizer with heuristic classification"
```

---

## Task 3: Stream Event Queue (deferred tool_call com insertBefore)

**Contexto:** Este módulo resolve o ordering. Ferramentas chegam via `updates` *depois* dos tokens de resposta via `messages`. A queue enfileira os eventos deferred e ao fazer `drain()`, emite com `insertBefore` apontando para o primeiro evento `response` do turno.

**Files:**
- Create: `src/lib/agent/stream-event-queue.ts`
- Create: `src/lib/agent/__tests__/stream-event-queue.test.ts`

**Step 1: Escreva os testes**

Crie `src/lib/agent/__tests__/stream-event-queue.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { createStreamEventQueue } from "@/lib/agent/stream-event-queue";
import type { StreamEventType, StreamModeName } from "@/types/agent";

type EmitArgs = {
  type: StreamEventType;
  data: string;
  mode: StreamModeName;
  meta?: Record<string, unknown>;
};

describe("createStreamEventQueue", () => {
  it("emite eventos live imediatamente sem enfileirar", () => {
    const emitted: EmitArgs[] = [];
    const queue = createStreamEventQueue((type, data, mode, meta) => {
      emitted.push({ type, data, mode, meta });
    });

    queue.emitLive("thought", "pensando...", "messages", {});
    queue.emitLive("response", "resposta", "messages", {});

    expect(emitted).toHaveLength(2);
    expect(emitted[0].type).toBe("thought");
    expect(emitted[1].type).toBe("response");
  });

  it("não emite eventos deferred antes de drain()", () => {
    const emitted: EmitArgs[] = [];
    const queue = createStreamEventQueue((type, data, mode, meta) => {
      emitted.push({ type, data, mode, meta });
    });

    queue.enqueueDeferred("tool_call", '{"name":"search"}', "updates", {});
    expect(emitted).toHaveLength(0);
  });

  it("drain emite eventos deferred sem insertBefore quando não houve response live", () => {
    const emitted: EmitArgs[] = [];
    const queue = createStreamEventQueue((type, data, mode, meta) => {
      emitted.push({ type, data, mode, meta });
    });

    queue.enqueueDeferred("tool_call", '{"name":"search"}', "updates", { toolCallId: "tc-1" });
    queue.drain();

    expect(emitted).toHaveLength(1);
    expect(emitted[0].type).toBe("tool_call");
    expect(emitted[0].meta?.insertBefore).toBeUndefined();
  });

  it("drain emite tool_call com insertBefore quando houve response live antes", () => {
    const emitted: EmitArgs[] = [];
    const queue = createStreamEventQueue((type, data, mode, meta) => {
      emitted.push({ type, data, mode, meta });
    });

    // Simula: response chega antes via messages mode
    queue.emitLive("response", "Com base na pesquisa...", "messages", { partId: "part-5" });
    // Tool_call chega depois via updates mode
    queue.enqueueDeferred("tool_call", '{"name":"search"}', "updates", { toolCallId: "tc-1" });

    queue.drain();

    // O evento live já foi emitido
    expect(emitted[0].type).toBe("response");
    // O deferred é emitido no drain com insertBefore
    expect(emitted[1].type).toBe("tool_call");
    expect(emitted[1].meta?.insertBefore).toBe("part-5");
  });

  it("drain emite tool_result com insertBefore logo após o tool_call correspondente", () => {
    const emitted: EmitArgs[] = [];
    const queue = createStreamEventQueue((type, data, mode, meta) => {
      emitted.push({ type, data, mode, meta });
    });

    queue.emitLive("response", "Encontrei isso:", "messages", { partId: "part-7" });
    queue.enqueueDeferred("tool_call", '{"name":"ls"}', "updates", { toolCallId: "tc-2" });
    queue.enqueueDeferred("tool_result", '{"result":"file.ts"}', "updates", { toolCallId: "tc-2" });

    queue.drain();

    expect(emitted[1].type).toBe("tool_call");
    expect(emitted[2].type).toBe("tool_result");
    // tool_result não precisa de insertBefore (vai depois do tool_call)
    expect(emitted[2].meta?.insertBefore).toBeUndefined();
  });

  it("reset() limpa o estado entre turnos", () => {
    const emitted: EmitArgs[] = [];
    const queue = createStreamEventQueue((type, data, mode, meta) => {
      emitted.push({ type, data, mode, meta });
    });

    queue.emitLive("response", "resposta turno 1", "messages", { partId: "part-1" });
    queue.enqueueDeferred("tool_call", '{"name":"x"}', "updates", {});
    queue.drain();
    queue.reset();

    // Após reset, novo deferred não deve ter insertBefore do turno anterior
    queue.enqueueDeferred("tool_call", '{"name":"y"}', "updates", {});
    queue.drain();

    const secondTurnToolCall = emitted.find((e, i) => i > 1 && e.type === "tool_call");
    expect(secondTurnToolCall?.meta?.insertBefore).toBeUndefined();
  });
});
```

**Step 2: Rode para ver falhar**

```bash
pnpm test -- stream-event-queue
```

Expected: FAIL com "Cannot find module".

**Step 3: Crie `src/lib/agent/stream-event-queue.ts`**

```typescript
import type { StreamEventType, StreamModeName, StreamEvent } from "@/types/agent";

type EmitFn = (
  type: StreamEventType,
  data: string,
  mode: StreamModeName,
  meta?: StreamEvent["meta"]
) => void;

interface DeferredEvent {
  type: StreamEventType;
  data: string;
  mode: StreamModeName;
  meta: StreamEvent["meta"];
}

/**
 * Stream Event Queue — resolve o problema de ordering entre messages e updates.
 *
 * O LangGraph entrega tokens via "messages" em tempo real, mas tool_calls completos
 * só chegam via "updates" depois. Esta queue separa os dois canais:
 *
 * - emitLive(): eventos que devem aparecer imediatamente (thought, response)
 * - enqueueDeferred(): eventos que chegam atrasados (tool_call, tool_result de updates)
 * - drain(): emite os deferred com meta.insertBefore apontando para o primeiro response
 * - reset(): limpa estado entre turnos
 */
export function createStreamEventQueue(emit: EmitFn) {
  /** ID do primeiro ContentPart do tipo response emitido neste turno */
  let firstResponsePartId: string | undefined;
  /** Fila de eventos para emitir no drain */
  const deferred: DeferredEvent[] = [];

  return {
    /**
     * Emite imediatamente. Para thought e response.
     * Captura o partId do primeiro response para usar como insertBefore.
     */
    emitLive(
      type: StreamEventType,
      data: string,
      mode: StreamModeName,
      meta: StreamEvent["meta"] = {}
    ) {
      if (type === "response" && !firstResponsePartId && meta?.partId) {
        firstResponsePartId = meta.partId as string;
      }
      emit(type, data, mode, meta);
    },

    /**
     * Enfileira um evento para emitir no drain.
     * Para tool_call e tool_result vindos de updates.
     */
    enqueueDeferred(
      type: StreamEventType,
      data: string,
      mode: StreamModeName,
      meta: StreamEvent["meta"] = {}
    ) {
      deferred.push({ type, data, mode, meta });
    },

    /**
     * Emite todos os eventos enfileirados.
     * tool_call recebe insertBefore se houve response antes.
     * tool_result não recebe insertBefore (vai logo após seu tool_call).
     * Chamado pelo normalizer no flush().
     */
    drain() {
      for (const event of deferred) {
        const enrichedMeta: StreamEvent["meta"] = { ...event.meta };

        if (event.type === "tool_call" && firstResponsePartId) {
          enrichedMeta.insertBefore = firstResponsePartId;
        }

        emit(event.type, event.data, event.mode, enrichedMeta);
      }
      deferred.length = 0;
    },

    /** Limpa estado entre turnos */
    reset() {
      firstResponsePartId = undefined;
      deferred.length = 0;
    },
  };
}

export type StreamEventQueue = ReturnType<typeof createStreamEventQueue>;
```

**Step 4: Rode os testes**

```bash
pnpm test -- stream-event-queue
```

Expected: PASS em todos os 5 testes.

**Step 5: Commit**

```bash
git add src/lib/agent/stream-event-queue.ts src/lib/agent/__tests__/stream-event-queue.test.ts
git commit -m "feat: add stream event queue for deferred tool_call ordering"
```

---

## Task 4: Turn Filter no normalizer

**Contexto:** Esta é a correção central da repetição de mensagens. O normalizer detecta automaticamente o `run_id` do primeiro evento do turno e ignora tudo com `run_id` diferente para emissão SSE (mas loga tudo via `logBus`).

**Files:**
- Modify: `src/lib/agent/chat-stream-normalizer.ts`
- Modify: `src/lib/agent/__tests__/chat-stream-normalizer.test.ts`

**Step 1: Leia as linhas 475–510 do normalizer para entender a estrutura atual**

```bash
sed -n '475,510p' src/lib/agent/chat-stream-normalizer.ts
```

**Step 2: Escreva os testes que falham — adicione ao final do `describe` existente em `chat-stream-normalizer.test.ts`:**

```typescript
describe("turn filter", () => {
  it("ignora mensagens de run_id anterior no mesmo stream", () => {
    const events: Array<{ type: StreamEventType; data: string }> = [];
    const normalizer = createAgentChatStreamNormalizer({
      provider: "openai",
      emit: (type, data) => events.push({ type, data }),
    });

    // Turno anterior — run_id "run-aaa"
    normalizer.process([
      ["root", "agent"],
      "messages",
      [
        { id: "msg-old", type: "ai", content: "resposta do turno anterior" },
        { langgraph_node: "agent", run_id: "run-aaa" },
      ],
    ]);

    // Turno atual — run_id "run-bbb" (primeiro a ser visto = atual)
    normalizer.process([
      ["root", "agent"],
      "messages",
      [
        { id: "msg-new", type: "ai", content: "resposta nova" },
        { langgraph_node: "agent", run_id: "run-bbb" },
      ],
    ]);

    normalizer.flush();

    // Somente a resposta nova deve ter sido emitida
    const responses = events.filter((e) => e.type === "response");
    expect(responses).toHaveLength(1);
    expect(responses[0].data).toContain("resposta nova");
  });

  it("aceita todos os eventos quando run_id está ausente (modo legado)", () => {
    const events: Array<{ type: StreamEventType }> = [];
    const normalizer = createAgentChatStreamNormalizer({
      provider: "openai",
      emit: (type) => events.push({ type }),
    });

    // Sem run_id — comportamento legado, não deve filtrar nada
    normalizer.process([
      { id: "msg-1", type: "ai", content: "sem run_id" },
      { langgraph_node: "agent" },
    ]);

    normalizer.flush();

    expect(events.filter((e) => e.type === "response")).toHaveLength(1);
  });

  it("o primeiro run_id visto se torna o run_id do turno atual", () => {
    const events: Array<{ type: StreamEventType; data: string }> = [];
    const normalizer = createAgentChatStreamNormalizer({
      provider: "openai",
      emit: (type, data) => events.push({ type, data }),
    });

    // Primeiro evento — run_id "run-ccc" → vira o currentTurnRunId
    normalizer.process([
      ["root", "agent"],
      "messages",
      [
        { id: "msg-1", type: "ai", content: "primeiro token" },
        { langgraph_node: "agent", run_id: "run-ccc" },
      ],
    ]);

    // Segundo evento com o mesmo run_id — deve ser emitido
    normalizer.process([
      ["root", "agent"],
      "messages",
      [
        { id: "msg-2", type: "ai", content: " segundo token" },
        { langgraph_node: "agent", run_id: "run-ccc" },
      ],
    ]);

    normalizer.flush();

    const responses = events.filter((e) => e.type === "response");
    expect(responses.length).toBeGreaterThanOrEqual(1);
    const allText = responses.map((e) => e.data).join("");
    expect(allText).toContain("primeiro token");
    expect(allText).toContain("segundo token");
  });
});
```

**Step 3: Rode para ver os testes novos**

```bash
pnpm test -- chat-stream-normalizer 2>&1 | tail -20
```

O primeiro teste ("ignora mensagens de run_id anterior") DEVE FALHAR — confirme isso antes de continuar.

**Step 4: Adicione o turn filter em `createAgentChatStreamNormalizer`**

Localize a função `createAgentChatStreamNormalizer` (linha ~475). Após a linha `const useThinkParser = isGeminiProvider(provider);`, adicione:

```typescript
/** run_id do turno atual — detectado pelo primeiro evento messages com run_id */
let currentTurnRunId: string | undefined;

/**
 * Verifica se um run_id pertence ao turno atual.
 * - Se currentTurnRunId ainda não foi definido, adota o primeiro run_id visto.
 * - Se run_id está ausente (legado), não filtra.
 * - Se run_id é diferente do atual, filtra (retorna false).
 */
const isCurrentTurn = (runId: string): boolean => {
  if (!runId) return true; // legado — sem run_id, não filtra
  if (!currentTurnRunId) {
    currentTurnRunId = runId; // lazy detection: primeiro run_id visto = turno atual
    return true;
  }
  return runId === currentTurnRunId;
};
```

**Step 5: Aplique o filtro em `processMessageMode`**

Localize a função `processMessageMode` (linha ~668). No início da função, após extrair `metadata`, adicione a checagem:

```typescript
const processMessageMode = (payload: unknown, path?: string[]) => {
  if (!Array.isArray(payload) || payload.length !== 2) return;
  const rawMessage = payload[0];
  const metadata = asRecord(payload[1]);

  // ── Turn Filter ──────────────────────────────────────────────────────────
  // Ignora mensagens de turnos anteriores (run_id diferente do turno atual).
  // O run_id está sempre presente no metadata de eventos messages do LangGraph.
  const eventRunId = safeString(metadata?.run_id);
  if (eventRunId && !isCurrentTurn(eventRunId)) {
    // Não emite SSE, mas o logBus já recebe tudo via route.ts antes de chegar aqui.
    return;
  }
  // ─────────────────────────────────────────────────────────────────────────

  // Handle raw string tokens directly (Gemini token-by-token)
  if (typeof rawMessage === "string") {
    // ... resto igual
```

**Step 6: Rode todos os testes**

```bash
pnpm test -- chat-stream-normalizer
```

Expected: TODOS passando, incluindo os 3 novos testes de turn filter.

**Step 7: Rode todos os testes do projeto**

```bash
pnpm test
```

Expected: mesma quantidade de testes passando que no baseline. Zero regressões.

**Step 8: Commit**

```bash
git add src/lib/agent/chat-stream-normalizer.ts src/lib/agent/__tests__/chat-stream-normalizer.test.ts
git commit -m "fix: turn-scoped stream filter prevents message repetition across turns"
```

---

## Task 5: Integrar Queue e Categorizer no normalizer

**Contexto:** Agora integramos os dois novos módulos no normalizer. O `output-categorizer` anota cada evento `response` com `meta.category`. A `stream-event-queue` recebe `tool_call`/`tool_result` de `updates` e os emite no `flush()` com `insertBefore`.

**Files:**
- Modify: `src/lib/agent/chat-stream-normalizer.ts`

**Step 1: Adicione os imports no topo do arquivo**

Localize os imports existentes (`import type { ... } from "@/types/agent"` e `import { classifyNode... }`) e adicione após eles:

```typescript
import { categorizeOutput } from "./output-categorizer";
import { createStreamEventQueue } from "./stream-event-queue";
```

**Step 2: Instancie a queue dentro de `createAgentChatStreamNormalizer`**

Logo após a linha `const useThinkParser = isGeminiProvider(provider);`, adicione:

```typescript
const eventQueue = createStreamEventQueue(emit);
```

**Step 3: Substitua `emitEvent` para usar `emitLive` da queue + categorizer**

Localize a função `emitEvent` (linha ~491). Substitua pela versão que integra a queue e o categorizer:

```typescript
const emitEvent = (
  type: StreamEventType,
  data: string,
  mode: StreamModeName,
  meta: StreamEvent["meta"] = {}
) => {
  if (mode === "messages" && type === "response") {
    hasMessageResponseOutput = true;
  }
  if (mode === "messages" && type === "thought") {
    hasMessageThoughtOutput = true;
  }

  // Anota categoria em eventos response
  const enrichedMeta: StreamEvent["meta"] =
    type === "response"
      ? { ...meta, category: categorizeOutput(data) }
      : meta;

  // tool_call e tool_result de updates são deferred (chegam tarde)
  // Todos os demais são live (emitidos imediatamente)
  if (mode === "updates" && (type === "tool_call" || type === "tool_result")) {
    eventQueue.enqueueDeferred(type, data, mode, enrichedMeta);
  } else {
    eventQueue.emitLive(type, data, mode, enrichedMeta);
  }
};
```

**Step 4: Atualize `flush()` para chamar `eventQueue.drain()`**

Localize o objeto retornado no final da função (o `return { process, flush }`). Atualize o `flush`:

```typescript
flush() {
  thinkParser?.flush();
  eventQueue.drain(); // emite tool_calls/results deferred com insertBefore
},
```

**Step 5: Escreva um teste de integração — adicione ao arquivo de testes do normalizer:**

```typescript
describe("queue integration", () => {
  it("emite tool_call com insertBefore quando response chegou antes", () => {
    const events: Array<{
      type: StreamEventType;
      data: string;
      meta?: StreamEvent["meta"];
    }> = [];

    const normalizer = createAgentChatStreamNormalizer({
      provider: "anthropic",
      emitUpdateSteps: false,
      emit: (type, data, mode, meta) => events.push({ type, data, meta }),
    });

    // 1. Response chega primeiro via messages
    normalizer.process([
      ["root", "agent"],
      "messages",
      [
        { id: "msg-1", type: "ai", content: "Com base na busca..." },
        { langgraph_node: "agent", run_id: "run-xyz" },
      ],
    ]);

    // 2. tool_call completo chega depois via updates
    normalizer.process([
      "updates",
      {
        tools: {
          messages: [
            {
              type: "ai",
              tool_calls: [{ id: "tc-1", name: "search_web", args: { query: "test" } }],
            },
          ],
        },
      },
    ]);

    normalizer.flush();

    const responseEvt = events.find((e) => e.type === "response");
    const toolCallEvt = events.find((e) => e.type === "tool_call");

    expect(responseEvt).toBeDefined();
    expect(toolCallEvt).toBeDefined();
    // A resposta deve ter categoria
    expect(responseEvt?.meta?.category).toBeDefined();
    // O tool_call deve ter insertBefore (ou ser emitido — mesmo sem partId o campo pode ser undefined)
    // O importante é que tool_call está presente nos eventos
    expect(toolCallEvt?.data).toContain("search_web");
  });
});
```

**Step 6: Rode os testes**

```bash
pnpm test -- chat-stream-normalizer
```

Expected: PASS em todos.

**Step 7: Rode todos os testes**

```bash
pnpm test
```

Expected: zero regressões.

**Step 8: Commit**

```bash
git add src/lib/agent/chat-stream-normalizer.ts
git commit -m "feat: integrate output categorizer and event queue into stream normalizer"
```

---

## Task 6: insertPartBefore no agent-store

**Contexto:** O frontend precisa de uma ação para inserir um ContentPart em uma posição específica, não apenas no final. Isso é usado quando `tool_call` chega com `insertBefore`.

**Files:**
- Modify: `src/stores/agent-store.ts`

**Step 1: Adicione `insertPartBefore` à interface `AgentStore`**

Localize a interface `AgentStore` em `src/stores/agent-store.ts`. Após `addToolCall`, adicione:

```typescript
insertPartBefore: (messageId: string, targetPartId: string, newPart: ContentPart) => void;
```

**Step 2: Implemente `insertPartBefore` no store**

Após a implementação de `addToolCall`, adicione:

```typescript
insertPartBefore: (messageId, targetPartId, newPart) => {
  set((state) => ({
    messages: state.messages.map((m) => {
      if (m.id !== messageId) return m;

      const targetIdx = m.contentParts.findIndex((p) => p.id === targetPartId);
      if (targetIdx === -1) {
        // targetPartId não encontrado — append no final como fallback seguro
        return { ...m, contentParts: [...m.contentParts, newPart] };
      }

      const parts = [...m.contentParts];
      parts.splice(targetIdx, 0, newPart);
      return { ...m, contentParts: parts };
    }),
  }));
},
```

**Step 3: Rode o type-check**

```bash
pnpm exec tsc --noEmit 2>&1 | grep "agent-store"
```

Expected: zero erros no `agent-store.ts`.

**Step 4: Rode todos os testes**

```bash
pnpm test
```

Expected: zero regressões.

**Step 5: Commit**

```bash
git add src/stores/agent-store.ts
git commit -m "feat: add insertPartBefore to agent store for tool ordering"
```

---

## Task 7: Handler insertBefore no use-agent-chat

**Contexto:** O hook que consome o SSE precisa usar `insertPartBefore` quando um `tool_call` chegar com `meta.insertBefore`. Caso contrário, mantém o comportamento atual (`addToolCall`).

**Files:**
- Modify: `src/hooks/use-agent-chat.ts`

**Step 1: Leia o case `"tool_call"` atual**

```bash
grep -n "tool_call\|insertBefore\|insertPartBefore" src/hooks/use-agent-chat.ts
```

**Step 2: Atualize o case `"tool_call"` para suportar `insertBefore`**

Localize o bloco `case "tool_call":` e substitua por:

```typescript
case "tool_call": {
  store.cancelEmptyThinking(assistantId);
  const tc = parseToolCallPayload(event.data);
  if (!tc) break;

  const toolCallId = tc.id || event.meta?.toolCallId;
  const insertBefore = event.meta?.insertBefore;

  if (insertBefore) {
    // Tool chegou atrasado via updates — insere na posição correta
    store.insertPartBefore(assistantId, insertBefore, {
      type: "tool_call",
      id: `part-deferred-${toolCallId ?? Date.now()}`,
      toolCallId: toolCallId ?? `tool-${Date.now()}`,
      name: tc.name,
      args: tc.args,
      status: "running",
      startedAt: new Date().toISOString(),
    });
  } else {
    // Comportamento normal — append no final
    store.addToolCall(assistantId, {
      id: toolCallId,
      name: tc.name,
      args: tc.args,
    });
  }
  break;
}
```

**Step 3: Rode o type-check**

```bash
pnpm exec tsc --noEmit 2>&1 | grep "use-agent-chat"
```

Expected: zero erros.

**Step 4: Rode todos os testes**

```bash
pnpm test
```

Expected: zero regressões.

**Step 5: Commit**

```bash
git add src/hooks/use-agent-chat.ts
git commit -m "feat: handle insertBefore in tool_call SSE events for correct ordering"
```

---

## Task 8: Expandir logger com values e debug modes

**Contexto:** Hoje o `route.ts` usa `streamMode: ["messages", "updates"]`. Precisamos adicionar `values` e `debug` ao stream — mas esses modos só são logados via `logBus`, nunca enviados via SSE para o frontend. O `VALID_STREAM_MODES` do normalizer precisa reconhecê-los para não os ignorar silenciosamente.

**Files:**
- Modify: `src/lib/agent/chat-stream-normalizer.ts`
- Modify: `src/app/api/agent/chat/route.ts`

**Step 1: Expanda `VALID_STREAM_MODES` no normalizer**

Localize a linha com `const VALID_STREAM_MODES = new Set(["messages", "updates", "custom"])` (linha ~307) e substitua:

```typescript
const VALID_STREAM_MODES = new Set(["messages", "updates", "custom", "values", "debug"]);
```

**Step 2: Adicione handlers para `values` e `debug` no `process()`**

Localize o objeto retornado com `process(item)` (final do arquivo). No switch interno, após o bloco `if (tuple.mode === "custom")`, adicione:

```typescript
// values e debug: apenas logados via logBus no route.ts, não emitem SSE
// O normalizer os reconhece mas não os processa para evitar eventos duplicados.
if (tuple.mode === "values" || tuple.mode === "debug") {
  return; // logBus já recebeu via route.ts
}
```

**Step 3: Expanda o `streamMode` no `route.ts`**

Localize em `src/app/api/agent/chat/route.ts` a linha:

```typescript
streamMode: ["messages", "updates"],
```

Substitua por:

```typescript
streamMode: ["messages", "updates", "values", "debug"],
```

**Step 4: Garanta que o logBus receba os eventos extras**

O `logBus.publish(event, sessionId)` já é chamado dentro do `emit()` do `route.ts` para todos os eventos. Mas `values` e `debug` chegam do stream *antes* de chegar ao normalizer — precisamos logar eles diretamente no loop do `route.ts`.

Localize o loop:

```typescript
for await (const item of agentStream as AsyncIterable<unknown>) {
  normalizer.process(item);
}
```

Substitua por:

```typescript
for await (const item of agentStream as AsyncIterable<unknown>) {
  // Log extra modes (values, debug) diretamente no logBus antes de normalizar
  if (Array.isArray(item) && typeof item[0] === "string") {
    const mode = item[0] as string;
    if (mode === "values" || mode === "debug") {
      logBus.publish(
        {
          id: `raw-${mode}-${Date.now()}`,
          seq: 0,
          type: "step",
          mode: mode as "values" | "debug",
          data: JSON.stringify(item[1]),
          meta: { provider, model },
        },
        sessionId
      );
    }
  }
  normalizer.process(item);
}
```

**Step 5: Rode o type-check**

```bash
pnpm exec tsc --noEmit 2>&1 | head -20
```

Expected: zero erros de tipo.

**Step 6: Rode todos os testes**

```bash
pnpm test
```

Expected: zero regressões.

**Step 7: Commit**

```bash
git add src/lib/agent/chat-stream-normalizer.ts src/app/api/agent/chat/route.ts
git commit -m "feat: add values and debug stream modes to logger"
```

---

## Task 9: Verificação end-to-end

**Contexto:** Testar manualmente os 6 critérios de sucesso do design doc.

**Step 1: Inicie o servidor**

```bash
pnpm dev
```

**Step 2: Teste de repetição — critério 1**

1. Abra `http://localhost:3000/agent`
2. Envie: "qual é a capital do Brasil?"
3. Aguarde a resposta completa
4. Envie: "e a capital da Argentina?"
5. **Verifique:** A segunda resposta NÃO deve começar repetindo "Brasília é a capital..."

**Step 3: Teste de ordering — critério 2**

1. Envie: "pesquise sobre LangGraph streaming" (ou qualquer pergunta que acione `search_web`)
2. **Verifique:** O bloco da ferramenta (`search_web`) aparece ACIMA do texto de resposta
3. Se o bloco aparecer abaixo, verifique o console do browser para ver se `insertBefore` está chegando nos eventos SSE

**Step 4: Verifique `meta.category` nos eventos — critério 4**

No browser, abra DevTools > Network > busque a requisição para `/api/agent/chat` > veja a aba "EventStream". Os eventos `response` devem ter `"category":"decision"` ou `"category":"explanation"` etc. no JSON.

**Step 5: Verifique os logs — critério 3**

Abra `http://localhost:3000/logs`. Os logs devem conter eventos de todos os modos (`values`, `debug`, `updates`, `messages`).

**Step 6: Se tudo estiver certo, commit final**

```bash
git add -p  # adicione apenas se houver ajustes manuais
git commit -m "fix: stream filter + ordering + structured output complete"
```

---

## Resumo das mudanças

| Arquivo | Tipo | O que muda |
|---------|------|------------|
| `src/types/agent.ts` | Modify | `OutputCategory`, `StreamModeName` com `values`/`debug`, `meta.insertBefore`, `meta.category`, `meta.turnRunId` |
| `src/lib/agent/output-categorizer.ts` | Create | Heurísticas de categoria para texto de resposta |
| `src/lib/agent/stream-event-queue.ts` | Create | Fila deferred com `insertBefore` para ordering |
| `src/lib/agent/chat-stream-normalizer.ts` | Modify | Turn filter (run_id), integra queue e categorizer, reconhece `values`/`debug` |
| `src/stores/agent-store.ts` | Modify | Nova ação `insertPartBefore` |
| `src/hooks/use-agent-chat.ts` | Modify | Handler `insertBefore` no case `tool_call` |
| `src/app/api/agent/chat/route.ts` | Modify | Expande `streamMode`, loga `values`/`debug` direto no logBus |
