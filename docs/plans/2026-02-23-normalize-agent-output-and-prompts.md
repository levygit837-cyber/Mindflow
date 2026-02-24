# Normalize Agent Output, Stream Nodes & Dynamic System Prompts

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir o streaming token-a-token do thinking, normalizar todos os tipos de nodes do LangGraph para evitar exibição incorreta no frontend, e substituir as instruções de tools hardcoded no systemPrompt por um sistema de prompts dinâmicos e modulares.

**Architecture:** O normalizer (`chat-stream-normalizer.ts`) já suporta messages/updates/custom mas não trata todos os node types que o LangGraph pode emitir. O agente usa um único systemPrompt monolítico em `index.ts`; vamos migrar para um sistema de prompts por arquivo com função dinâmica que muda o systemPrompt baseado no estado do grafo (quais tools foram invocadas, contexto atual). O streaming do thinking usa thinkTagParser que acumula buffer — corrigiremos para emitir token-a-token imediatamente.

**Tech Stack:** TypeScript 5.9, LangGraph JS (createReactAgent com `prompt` fn dinâmica), LangChain Core, Vitest, Next.js SSE, Zustand v5.

---

## Pré-requisito: rodar os testes atuais para baseline

```bash
pnpm test
```

Anote quais testes passam antes de começar.

---

## PARTE 1 — Corrigir streaming token-a-token do thinking

### Task 1: Corrigir o ThinkTag parser para emitir tokens imediatamente

**Problema atual:** O `createThinkTagParser` em `chat-stream-normalizer.ts` acumula no buffer e só emite quando `buffer.length > 8` (safe window de 8 chars para o tag `</think>`). Isso cria chunks de mensagens ao invés de tokens individuais.

**Arquivos:**
- Modify: `src/lib/agent/chat-stream-normalizer.ts` (função `createThinkTagParser`)
- Test: `src/lib/agent/__tests__/chat-stream-normalizer.test.ts`

**Step 1: Escreva o teste que falha**

Em `src/lib/agent/__tests__/chat-stream-normalizer.test.ts`, adicione no final do `describe`:

```typescript
it("emite thought tokens individualmente (token-a-token) sem acumular buffer", () => {
  const emitted: Array<{ type: StreamEventType; data: string }> = [];

  const normalizer = createAgentChatStreamNormalizer({
    provider: "vertexai",
    emit: (type, data) => emitted.push({ type, data }),
  });

  // Simula chegada de tokens individuais (1 char por vez)
  const tokens = ["<", "t", "h", "i", "n", "k", ">", "p", "e", "n", "s", "a", "<", "/", "t", "h", "i", "n", "k", ">", "o", "k"];
  for (const token of tokens) {
    normalizer.process([token, { langgraph_node: "agent" }]);
  }
  normalizer.flush();

  // Deve emitir "thought" com "pensa" progressivamente (não acumular tudo)
  const thoughtEvents = emitted.filter(e => e.type === "thought");
  const responseEvents = emitted.filter(e => e.type === "response");

  // Deve ter pelo menos 1 evento thought com conteúdo partial
  expect(thoughtEvents.length).toBeGreaterThan(0);
  // Conteúdo total pensado deve ser "pensa"
  const totalThought = thoughtEvents.map(e => e.data).join("");
  expect(totalThought).toBe("pensa");
  // Response deve ser "ok"
  const totalResponse = responseEvents.map(e => e.data).join("");
  expect(totalResponse).toBe("ok");
});
```

**Step 2: Rode para ver falhar**

```bash
pnpm test -- chat-stream-normalizer
```

Expected: FAIL — o teste atual vai falhar porque tokens individuais `["<","t","h"...]` chegam como `[string, metadata]` mas o parser não processa esse shape (trata como messages mode com `payload = [string, meta]`).

**Step 3: Corrija o `processMessageMode` para aceitar content string direta**

No `chat-stream-normalizer.ts`, localize `processMessageMode`. A função rejeita se `payload[0]` não é um record (`asRecord`). Corrija para aceitar string direta:

```typescript
const processMessageMode = (payload: unknown, path?: string[]) => {
  if (!Array.isArray(payload) || payload.length !== 2) return;
  const rawMessage = payload[0];
  const metadata = asRecord(payload[1]);

  // Handle raw string tokens directly (Gemini token-by-token)
  if (typeof rawMessage === "string") {
    const node = safeString(metadata?.langgraph_node);
    const meta = { node, runId: safeString(metadata?.run_id), path };
    emitText(rawMessage, "messages", meta);
    return;
  }

  const messageRecord = asRecord(rawMessage);
  if (!messageRecord) return;
  const message = unwrapMessageLike(messageRecord);
  // ... resto igual
```

**Step 4: Corrija o `createThinkTagParser` para emitir imediatamente**

Substitua a função `createThinkTagParser` inteira (linhas com `let buffer = ""`):

```typescript
function createThinkTagParser(send: (type: StreamEventType, data: string, mode: StreamModeName) => void) {
  let insideThink = false;
  // Acumula apenas o mínimo necessário para detectar os tags (7 chars para "<think>" ou 8 para "</think>")
  let tagBuffer = "";

  return {
    push(text: string) {
      // Processa char por char para emitir o mais cedo possível
      for (const ch of text) {
        tagBuffer += ch;

        if (insideThink) {
          // Procura por "</think>" no buffer
          const closeTag = "</think>";
          if (tagBuffer.endsWith(closeTag)) {
            // Emite o conteúdo antes do close tag
            const content = tagBuffer.slice(0, -closeTag.length);
            if (content) send("thought", content, "messages");
            tagBuffer = "";
            insideThink = false;
          } else if (tagBuffer.length > closeTag.length) {
            // Pode emitir os chars que com certeza não fazem parte do tag
            const safe = tagBuffer.slice(0, tagBuffer.length - closeTag.length + 1);
            send("thought", safe, "messages");
            tagBuffer = tagBuffer.slice(safe.length);
          }
        } else {
          // Procura por "<think>" no buffer
          const openTag = "<think>";
          if (tagBuffer.endsWith(openTag)) {
            // Emite o que vem antes do tag como response
            const before = tagBuffer.slice(0, -openTag.length);
            if (before) send("response", before, "messages");
            tagBuffer = "";
            insideThink = true;
          } else if (tagBuffer.length > openTag.length) {
            // Emite chars que com certeza não fazem parte do tag
            const safe = tagBuffer.slice(0, tagBuffer.length - openTag.length + 1);
            send("response", safe, "messages");
            tagBuffer = tagBuffer.slice(safe.length);
          }
        }
      }
    },

    flush() {
      if (!tagBuffer) return;
      send(insideThink ? "thought" : "response", tagBuffer, "messages");
      tagBuffer = "";
    },
  };
}
```

**Step 5: Rode os testes para verificar que passam**

```bash
pnpm test -- chat-stream-normalizer
```

Expected: PASS em todos.

**Step 6: Commit**

```bash
git add src/lib/agent/chat-stream-normalizer.ts src/lib/agent/__tests__/chat-stream-normalizer.test.ts
git commit -m "fix: emit thinking tokens immediately without buffer accumulation"
```

---

## PARTE 2 — Normalizar todos os tipos de Nodes do LangGraph

### Task 2: Mapear e tipar todos os node types que o LangGraph pode emitir

**Contexto:** O LangGraph emite vários tipos de nodes no modo `updates`. O frontend só conhece `"agent"` e `"tools"` mas o deepagents pode emitir middleware nodes, subgraph nodes, custom nodes. Precisamos de um mapeamento central.

**Arquivos:**
- Create: `src/lib/agent/node-registry.ts`
- Modify: `src/lib/agent/chat-stream-normalizer.ts`
- Modify: `src/types/agent.ts`

**Step 1: Escreva testes para o node-registry**

Crie `src/lib/agent/__tests__/node-registry.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import {
  classifyNode,
  getNodeLabel,
  isStreamableNode,
  NodeCategory,
} from "@/lib/agent/node-registry";

describe("node-registry", () => {
  it("classifica 'agent' como LLM_INVOKE", () => {
    expect(classifyNode("agent")).toBe(NodeCategory.LLM_INVOKE);
  });

  it("classifica 'tools' como TOOL_EXECUTION", () => {
    expect(classifyNode("tools")).toBe(NodeCategory.TOOL_EXECUTION);
  });

  it("classifica nodes de middleware como INTERNAL", () => {
    expect(classifyNode("patchToolCallsMiddleware.before_agent")).toBe(NodeCategory.INTERNAL);
    expect(classifyNode("SummarizationMiddleware.after_agent")).toBe(NodeCategory.INTERNAL);
    expect(classifyNode("__start__")).toBe(NodeCategory.INTERNAL);
    expect(classifyNode("__end__")).toBe(NodeCategory.INTERNAL);
  });

  it("classifica subgraph nodes como SUBGRAPH", () => {
    expect(classifyNode("coder:agent")).toBe(NodeCategory.SUBGRAPH);
    expect(classifyNode("analyst:tools")).toBe(NodeCategory.SUBGRAPH);
  });

  it("classifica nodes desconhecidos como UNKNOWN", () => {
    expect(classifyNode("my_custom_node")).toBe(NodeCategory.UNKNOWN);
  });

  it("retorna label amigável para nodes conhecidos", () => {
    expect(getNodeLabel("agent")).toBe("Agent");
    expect(getNodeLabel("tools")).toBe("Tools");
  });

  it("retorna label descritivo para subgraph nodes", () => {
    expect(getNodeLabel("coder:agent")).toBe("Coder › Agent");
  });

  it("isStreamableNode retorna false para INTERNAL", () => {
    expect(isStreamableNode("__start__")).toBe(false);
    expect(isStreamableNode("patchToolCallsMiddleware.before_agent")).toBe(false);
  });

  it("isStreamableNode retorna true para agent e tools", () => {
    expect(isStreamableNode("agent")).toBe(true);
    expect(isStreamableNode("tools")).toBe(true);
  });
});
```

**Step 2: Rode para ver falhar**

```bash
pnpm test -- node-registry
```

Expected: FAIL (arquivo não existe).

**Step 3: Crie `src/lib/agent/node-registry.ts`**

```typescript
/**
 * Node Registry — classifica e rotula todos os tipos de nodes que o LangGraph pode emitir.
 *
 * O LangGraph emite updates para vários tipos de nodes. Este módulo centraliza
 * a lógica de categorização para que o normalizer e o frontend saibam o que exibir.
 */

export enum NodeCategory {
  /** Invocação direta do LLM (agent, model) */
  LLM_INVOKE = "LLM_INVOKE",
  /** Execução de tools (tools, tool_executor) */
  TOOL_EXECUTION = "TOOL_EXECUTION",
  /** Subgraph de outro agente (formato "agentName:nodeName") */
  SUBGRAPH = "SUBGRAPH",
  /** Nó interno/middleware — não deve aparecer no frontend */
  INTERNAL = "INTERNAL",
  /** Nó customizado desconhecido */
  UNKNOWN = "UNKNOWN",
}

/** Nomes de nós internos que nunca devem ser exibidos */
const INTERNAL_NODE_PATTERNS: RegExp[] = [
  /^__/,                          // __start__, __end__, __interrupt__
  /Middleware/i,                  // patchToolCallsMiddleware, SummarizationMiddleware
  /\.before_/,                    // .before_agent
  /\.after_/,                     // .after_agent
  /^model_request$/,
  /^model_response$/,
  /^patchToolCalls/,
];

/** Nomes canônicos de nodes LLM */
const LLM_NODES = new Set(["agent", "model", "llm", "generate", "chat"]);

/** Nomes canônicos de nodes de tools */
const TOOL_NODES = new Set(["tools", "tool_executor", "tool_node", "action"]);

export function classifyNode(nodeName: string): NodeCategory {
  if (!nodeName) return NodeCategory.INTERNAL;

  // Subgraph: contém ":" separando agente:nó
  if (nodeName.includes(":")) return NodeCategory.SUBGRAPH;

  // Interno
  for (const pattern of INTERNAL_NODE_PATTERNS) {
    if (pattern.test(nodeName)) return NodeCategory.INTERNAL;
  }

  if (LLM_NODES.has(nodeName)) return NodeCategory.LLM_INVOKE;
  if (TOOL_NODES.has(nodeName)) return NodeCategory.TOOL_EXECUTION;

  return NodeCategory.UNKNOWN;
}

export function getNodeLabel(nodeName: string): string {
  if (!nodeName) return "Node";

  // Subgraph: "coder:agent" → "Coder › Agent"
  if (nodeName.includes(":")) {
    const [parent, child] = nodeName.split(":", 2);
    return `${titleCase(parent)} › ${titleCase(child)}`;
  }

  const canonical: Record<string, string> = {
    agent: "Agent",
    tools: "Tools",
    model: "Model",
    llm: "LLM",
    generate: "Generate",
    chat: "Chat",
    tool_executor: "Tools",
    tool_node: "Tools",
    action: "Action",
  };

  return canonical[nodeName] ?? titleCase(nodeName);
}

/** Retorna true se este node deve ter seus eventos expostos ao frontend */
export function isStreamableNode(nodeName: string): boolean {
  const category = classifyNode(nodeName);
  return (
    category === NodeCategory.LLM_INVOKE ||
    category === NodeCategory.TOOL_EXECUTION ||
    category === NodeCategory.SUBGRAPH ||
    category === NodeCategory.UNKNOWN
  );
}

function titleCase(value: string): string {
  if (!value) return "";
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
```

**Step 4: Rode os testes**

```bash
pnpm test -- node-registry
```

Expected: PASS.

**Step 5: Atualize `src/types/agent.ts` para incluir NodeCategory**

Adicione após a linha `export type StreamModeName = ...`:

```typescript
export type { NodeCategory } from "@/lib/agent/node-registry";

/** Metadados de um node do LangGraph */
export interface NodeMeta {
  name: string;
  category: import("@/lib/agent/node-registry").NodeCategory;
  label: string;
  isStreamable: boolean;
  subgraphPath?: string[];
}
```

**Step 6: Atualize o `chat-stream-normalizer.ts` para usar o node-registry**

Localize as funções `isUserVisibleUpdateNode` e `userVisibleUpdateLabel`. Substitua-as pelo uso do registry:

```typescript
// No topo do arquivo, adicione:
import { classifyNode, getNodeLabel, isStreamableNode, NodeCategory } from "./node-registry";

// Remova as funções isUserVisibleUpdateNode e userVisibleUpdateLabel
// e substitua seus usos por:
//   isUserVisibleUpdateNode(x) → isStreamableNode(x)
//   userVisibleUpdateLabel(x) → getNodeLabel(x)
```

No `processUpdatesMode`, mude:

```typescript
if (emitUpdateSteps && isStreamableNode(nodeName)) {
  const label = getNodeLabel(nodeName);
  const category = classifyNode(nodeName);
  const stepPayload = JSON.stringify({
    stepName: label,
    detail: `Node: ${nodeName} [${category}]`,
    action: "start",
  });
  emitEvent("agent_step" as StreamEventType, stepPayload, "updates", {
    node: nodeName,
    path,
  });
}
```

**Step 7: Rode todos os testes**

```bash
pnpm test
```

Expected: PASS em todos (os testes existentes que verificam "Tools" e "Agent" ainda devem passar).

**Step 8: Commit**

```bash
git add src/lib/agent/node-registry.ts src/lib/agent/__tests__/node-registry.test.ts src/lib/agent/chat-stream-normalizer.ts src/types/agent.ts
git commit -m "feat: add node-registry to classify all LangGraph node types"
```

---

### Task 3: Adicionar `NodeCategory` ao `StreamEvent.meta` e exibir no frontend

**Problema:** O frontend recebe `agent_step` mas não sabe de qual categoria de node veio. Às vezes aparecem nodes que o frontend não esperava e exibe igual.

**Arquivos:**
- Modify: `src/types/agent.ts`
- Modify: `src/components/agent/agent-steps-block.tsx`

**Step 1: Adicione `nodeCategory` ao `StreamEvent.meta`**

Em `src/types/agent.ts`, localize a interface `StreamEvent.meta` e adicione:

```typescript
meta?: {
  runId?: string;
  parentRunId?: string;
  node?: string;
  nodeCategory?: string;   // ← adicionar
  toolCallId?: string;
  provider?: LLMProvider;
  model?: string;
  status?: "start" | "update" | "end";
  path?: string[];
};
```

**Step 2: Leia o `agent-steps-block.tsx`**

```bash
# No editor, abra:
# src/components/agent/agent-steps-block.tsx
```

**Step 3: Escreva um teste de renderização para `AgentStepBlock`**

Verifique se existe `src/components/agent/__tests__/`. Se não existir, crie. Adicione `agent-steps-block.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AgentStepsBlock } from "@/components/agent/agent-steps-block";

describe("AgentStepsBlock", () => {
  it("exibe label do step corretamente", () => {
    render(
      <AgentStepsBlock
        id="step-1"
        stepName="Agent"
        detail="Node: agent [LLM_INVOKE]"
        status="running"
        startedAt={new Date().toISOString()}
        subSteps={[]}
      />
    );
    expect(screen.getByText("Agent")).toBeInTheDocument();
  });

  it("não renderiza nodes INTERNAL", () => {
    const { container } = render(
      <AgentStepsBlock
        id="step-2"
        stepName=""
        detail="Node: __start__ [INTERNAL]"
        status="completed"
        startedAt={new Date().toISOString()}
        subSteps={[]}
        hidden={true}
      />
    );
    expect(container.firstChild).toBeNull();
  });
});
```

> **Nota:** Se a configuração de testes de componente React não estiver pronta (jsdom), pule este teste de componente e foque apenas nos testes unitários do normalizer e registry.

**Step 4: Atualize `agent-steps-block.tsx` para respeitar `hidden` prop**

Leia o arquivo primeiro, depois edite para adicionar:

```typescript
interface AgentStepBlockProps {
  // ... props existentes
  hidden?: boolean;
}

// No início do componente:
if (props.hidden) return null;
```

**Step 5: No `use-agent-chat.ts`, passe `nodeCategory` para `addAgentStep`**

Localize o case `"agent_step"` no switch do SSE consumer. Após o parse do `stepData`, adicione o nodeCategory ao detail se disponível:

```typescript
case "agent_step": {
  try {
    const stepData = JSON.parse(event.data) as {
      stepName: string;
      detail: string;
      action?: "start" | "update" | "complete";
      subStep?: string;
      stepId?: string;
    };
    // Filtra nodes INTERNAL antes de exibir
    if (stepData.detail?.includes("[INTERNAL]")) break;

    if (stepData.action === "update" && stepData.stepId && stepData.subStep) {
      store.updateAgentStep(assistantId, stepData.stepId, stepData.subStep);
    } else if (stepData.action === "complete" && stepData.stepId) {
      store.completeAgentStep(assistantId, stepData.stepId);
    } else {
      store.addAgentStep(assistantId, stepData.stepName, stepData.detail);
    }
  } catch {
    // ignore
  }
  break;
}
```

**Step 6: Rode os testes**

```bash
pnpm test
```

**Step 7: Commit**

```bash
git add src/types/agent.ts src/components/agent/agent-steps-block.tsx src/hooks/use-agent-chat.ts
git commit -m "fix: filter INTERNAL nodes from agent steps display"
```

---

## PARTE 3 — Sistema de SystemPrompts Modulares

### Task 4: Criar estrutura de prompts dinâmicos por ferramenta/contexto

**Contexto:** Atualmente o SYSTEM_PROMPT em `src/lib/agent/index.ts` tem ~120 linhas de instruções de tools hardcoded. A abordagem LangGraph correta é usar a `prompt` function que recebe `state` e `config` e retorna `BaseMessageLike[]` — isso permite mudar o systemPrompt baseado no estado atual.

**Arquivos:**
- Create: `src/lib/agent/prompts/base.ts`
- Create: `src/lib/agent/prompts/tools/filesystem.ts`
- Create: `src/lib/agent/prompts/tools/web-search.ts`
- Create: `src/lib/agent/prompts/tools/task-planning.ts`
- Create: `src/lib/agent/prompts/tools/shell.ts`
- Create: `src/lib/agent/prompts/dynamic-prompt.ts`
- Modify: `src/lib/agent/index.ts`
- Modify: `src/lib/agent/deep-agent-config.ts`

**Step 1: Escreva testes para o sistema de prompts dinâmicos**

Crie `src/lib/agent/__tests__/dynamic-prompt.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { buildDynamicPrompt } from "@/lib/agent/prompts/dynamic-prompt";
import { MessagesAnnotation } from "@langchain/langgraph";
import type { BaseMessageLike } from "@langchain/core/messages";
import { HumanMessage } from "@langchain/core/messages";

describe("buildDynamicPrompt", () => {
  const baseState = {
    messages: [new HumanMessage("Olá")],
  };

  it("retorna SystemMessage + messages no mínimo", () => {
    const result = buildDynamicPrompt(baseState);
    expect(result.length).toBeGreaterThanOrEqual(2);
    const first = result[0] as { role: string; content: string };
    expect(first.role).toBe("system");
    expect(first.content).toContain("OmniMind");
  });

  it("inclui instruções de filesystem quando há tool_calls de filesystem", () => {
    const stateWithFsTool = {
      messages: [
        new HumanMessage("leia o arquivo"),
        // Simula AIMessage com tool_call de filesystem
        {
          type: "ai",
          content: "",
          tool_calls: [{ id: "tc-1", name: "read_file", args: { file_path: "/src/index.ts" } }],
        },
      ],
    };
    const result = buildDynamicPrompt(stateWithFsTool as typeof MessagesAnnotation.State);
    const systemContent = (result[0] as { role: string; content: string }).content;
    expect(systemContent).toContain("read_file");
    expect(systemContent).toContain("edit_file");
  });

  it("inclui instruções de web search quando há tool_calls de search", () => {
    const stateWithSearchTool = {
      messages: [
        new HumanMessage("pesquise"),
        {
          type: "ai",
          content: "",
          tool_calls: [{ id: "tc-2", name: "search_web", args: { query: "langgraph" } }],
        },
      ],
    };
    const result = buildDynamicPrompt(stateWithSearchTool as typeof MessagesAnnotation.State);
    const systemContent = (result[0] as { role: string; content: string }).content;
    expect(systemContent).toContain("search_web");
  });

  it("não duplica seções quando múltiplas tools do mesmo grupo são chamadas", () => {
    const stateWithMultipleFsTools = {
      messages: [
        new HumanMessage("edite e leia"),
        {
          type: "ai",
          content: "",
          tool_calls: [
            { id: "tc-3", name: "read_file", args: {} },
            { id: "tc-4", name: "edit_file", args: {} },
          ],
        },
      ],
    };
    const result = buildDynamicPrompt(stateWithMultipleFsTools as typeof MessagesAnnotation.State);
    const systemContent = (result[0] as { role: string; content: string }).content;
    // "read_file" deve aparecer apenas UMA vez no prompt
    const occurrences = (systemContent.match(/read_file/g) ?? []).length;
    expect(occurrences).toBe(1);
  });
});
```

**Step 2: Rode para ver falhar**

```bash
pnpm test -- dynamic-prompt
```

Expected: FAIL (arquivos não existem).

**Step 3: Crie `src/lib/agent/prompts/base.ts`**

```typescript
/**
 * Base system prompt — identidade e comportamento geral do OmniMind.
 * NÃO contém instruções específicas de tools (isso fica nos módulos tool-specific).
 */
export const BASE_PROMPT = `You are OmniMind, a powerful AI agent with deep task resolution capabilities.

## Core Behavior

1. **Think step by step** — your reasoning will be shown to the user in a collapsible section.
2. **Be concise, helpful, and thorough** — avoid unnecessary verbosity.
3. **Always verify before acting** — check file existence before reading, read before editing.
4. **Use the right tool for the job** — never use execute when a dedicated tool exists.
5. **Report errors clearly** — if a tool fails, explain what happened and suggest alternatives.
6. **Respect the workspace** — you operate on real files. Be careful with writes and edits.

## General Tool Rules

- Never delete files or directories without explicit user permission.
- Never perform destructive operations (rm, DROP TABLE, git reset --hard) autonomously.
- If you need to delete or permanently modify something — ASK THE USER first.`;
```

**Step 4: Crie `src/lib/agent/prompts/tools/filesystem.ts`**

```typescript
/**
 * System prompt module — Filesystem tools.
 * Incluído quando o agente usa: ls, read_file, write_file, edit_file, glob, grep
 */
export const FILESYSTEM_PROMPT = `## Filesystem Tools

### ls (List Directory)
- **ALWAYS call ls BEFORE read_file or edit_file** to verify the file exists.
- Use ls on the parent directory to discover file names before operating on them.
- Default path is "/". Always pass the specific directory: ls(path="/src/components").
- **DO NOT** use execute(command="ls ...") — use this tool instead.

### read_file (Read File)
- Use pagination for large files: read_file(file_path="/path", offset=0, limit=100).
- Always read a file BEFORE editing it with edit_file.
- Lines are numbered in output (cat -n format) — use these for exact content matching.
- **DO NOT** use execute(command="cat ...") — use this tool instead.

### write_file (Write New File)
- ONLY for creating NEW files. If file exists, it returns an error.
- Always provide the COMPLETE file content.
- Verify the parent directory exists with ls before writing.

### edit_file (Edit Existing File)
- Performs exact string replacement: old_string → new_string.
- You MUST read_file first to get the exact content to replace.
- Preserve exact indentation (tabs/spaces) as shown in read_file output.
- **Workflow:** ls → read_file → edit_file (always in this order).

### glob (Find Files by Pattern)
- Use glob patterns: glob(pattern="**/*.ts") finds all TypeScript files recursively.
- Pass a base path to narrow the search: glob(pattern="*.tsx", path="/src/components").
- **DO NOT** use execute(command="find . -name '*.ts'") — use this tool instead.

### grep (Search File Contents)
- Searches for text patterns across files and returns matching lines with line numbers.
- Specify a path to narrow scope: grep(pattern="TODO", path="/src").
- **DO NOT** use execute(command="grep ...") — use this tool instead.`;
```

**Step 5: Crie `src/lib/agent/prompts/tools/web-search.ts`**

```typescript
/**
 * System prompt module — Web search tool.
 * Incluído quando o agente usa: search_web
 */
export const WEB_SEARCH_PROMPT = `## Web Search Tool

### search_web (Web Search)
- Search the web for up-to-date information, documentation, APIs, error solutions.
- Returns top 10 results with title, URL, and snippet.
- Use specific, targeted queries: search_web(query="Next.js 16 app router streaming SSE") not just "nextjs".
- Use when you need: current documentation, error messages you don't recognize, package APIs, best practices.
- This is your ONLY source of external information — use it when your knowledge is uncertain or outdated.`;
```

**Step 6: Crie `src/lib/agent/prompts/tools/task-planning.ts`**

```typescript
/**
 * System prompt module — Task planning tool.
 * Incluído quando o agente usa: write_todos
 */
export const TASK_PLANNING_PROMPT = `## Task Planning Tool

### write_todos (Task Planning)
- Use ONLY for complex tasks that require 3 or more steps.
- Each call REPLACES the entire todo list — always include all items (pending, in_progress, completed).
- Mark items as "in_progress" when you start working on them, "completed" when done.
- NEVER call write_todos multiple times in the same turn — consolidate into one call.
- For simple tasks (1-2 steps), just do them directly without write_todos.`;
```

**Step 7: Crie `src/lib/agent/prompts/tools/shell.ts`**

```typescript
/**
 * System prompt module — Shell execution tool.
 * Incluído quando o agente usa: execute
 */
export const SHELL_PROMPT = `## Shell Execution Tool (RESTRICTED)

### execute (Shell Commands)
- Use ONLY for operations that NO OTHER tool can accomplish.
- Prefer dedicated tools: ls, read_file, glob, grep over their shell equivalents.

**ALLOWED commands:**
- Package managers: npm, npx, yarn, pnpm, pip, cargo, go
- Build/test: make, cmake, tsc, eslint, prettier, vitest, jest, pytest
- Version control: git status, git diff, git log, git add, git commit, git branch
- Runtime: node, python, deno, bun
- Utilities: echo, wc, sort, uniq, diff, date, whoami, pwd, which, env
- Network (read-only): curl (GET only), wget (download only), ping

**ABSOLUTELY FORBIDDEN:**
- rm, rmdir — NEVER delete files
- rm -rf — NEVER recursive delete
- kill, killall, pkill — NEVER terminate processes
- shutdown, reboot, halt, poweroff — NEVER system control
- sudo, su — NEVER privilege escalation
- git push --force, git reset --hard — NEVER destructive git
- DROP TABLE, DELETE FROM, TRUNCATE — NEVER destructive SQL
- Any curl -X POST/PUT/DELETE — NEVER mutating HTTP requests

**If you need to delete, move, or change permissions — ASK THE USER first.**`;
```

**Step 8: Crie `src/lib/agent/prompts/dynamic-prompt.ts`**

```typescript
/**
 * Dynamic prompt builder para o OmniMind agent.
 *
 * Em vez de um único systemPrompt monolítico, constrói o prompt dinamicamente
 * baseado no estado atual do agente (quais tools foram chamadas recentemente).
 *
 * Compatível com a API de `prompt` function do createReactAgent do LangGraph:
 * (state: State, config?: RunnableConfig) => BaseMessageLike[]
 */

import type { BaseMessageLike } from "@langchain/core/messages";
import type { RunnableConfig } from "@langchain/core/runnables";
import { MessagesAnnotation } from "@langchain/langgraph";
import { BASE_PROMPT } from "./base";
import { FILESYSTEM_PROMPT } from "./tools/filesystem";
import { WEB_SEARCH_PROMPT } from "./tools/web-search";
import { TASK_PLANNING_PROMPT } from "./tools/task-planning";
import { SHELL_PROMPT } from "./tools/shell";

/** Groups de tools mapeadas para seus prompts */
const TOOL_PROMPT_MODULES: Array<{
  toolNames: string[];
  prompt: string;
}> = [
  {
    toolNames: ["ls", "read_file", "write_file", "edit_file", "glob", "grep"],
    prompt: FILESYSTEM_PROMPT,
  },
  {
    toolNames: ["search_web"],
    prompt: WEB_SEARCH_PROMPT,
  },
  {
    toolNames: ["write_todos"],
    prompt: TASK_PLANNING_PROMPT,
  },
  {
    toolNames: ["execute"],
    prompt: SHELL_PROMPT,
  },
];

/** Extrai os nomes de tools invocadas nas mensagens do estado */
function extractRecentToolNames(
  messages: typeof MessagesAnnotation.State["messages"]
): Set<string> {
  const names = new Set<string>();

  for (const msg of messages) {
    // Suporta AIMessage com tool_calls array
    const toolCalls = (msg as { tool_calls?: Array<{ name: string }> }).tool_calls;
    if (Array.isArray(toolCalls)) {
      for (const tc of toolCalls) {
        if (tc.name) names.add(tc.name);
      }
    }

    // Suporta content blocks com type "tool_use"
    const content = (msg as { content?: unknown }).content;
    if (Array.isArray(content)) {
      for (const block of content) {
        if (
          typeof block === "object" &&
          block !== null &&
          "type" in block &&
          (block as { type: string }).type === "tool_use" &&
          "name" in block
        ) {
          names.add((block as { name: string }).name);
        }
      }
    }
  }

  return names;
}

/**
 * Constrói o prompt dinâmico baseado no estado atual.
 * Sempre inclui o BASE_PROMPT + sections dos tools que já foram usados
 * (ou todos os tools disponíveis na primeira mensagem).
 */
export function buildDynamicPrompt(
  state: typeof MessagesAnnotation.State,
  _config?: RunnableConfig
): BaseMessageLike[] {
  const usedTools = extractRecentToolNames(state.messages);

  // Coleta as seções de prompt dos tools relevantes (sem duplicatas)
  const sections: string[] = [BASE_PROMPT];
  const addedPrompts = new Set<string>();

  // Se nenhuma tool foi usada ainda, inclui TODOS os módulos
  // (contexto completo na primeira interação)
  const includeAll = usedTools.size === 0;

  for (const module of TOOL_PROMPT_MODULES) {
    const isRelevant = includeAll || module.toolNames.some((name) => usedTools.has(name));
    if (isRelevant && !addedPrompts.has(module.prompt)) {
      sections.push(module.prompt);
      addedPrompts.add(module.prompt);
    }
  }

  const systemContent = sections.join("\n\n");

  return [
    { role: "system", content: systemContent },
    ...state.messages,
  ];
}
```

**Step 9: Rode os testes**

```bash
pnpm test -- dynamic-prompt
```

Expected: PASS em todos.

**Step 10: Commit**

```bash
git add src/lib/agent/prompts/
git commit -m "feat: add modular prompt system with per-tool sections"
```

---

### Task 5: Integrar o dynamic prompt no agente e remover SYSTEM_PROMPT hardcoded

**Arquivos:**
- Modify: `src/lib/agent/deep-agent-config.ts`
- Modify: `src/lib/agent/index.ts`

**Step 1: Leia o `deep-agent-config.ts` atual**

```
src/lib/agent/deep-agent-config.ts
```

(já lido — veja o arquivo acima. Ele aceita `systemPrompt: string`.)

**Step 2: Atualize `DeepAgentOptions` em `deep-agent-config.ts` para aceitar `prompt` function**

O `createDeepAgent` do deepagents aceita `systemPrompt: string`. Precisamos verificar se também aceita uma `prompt` function. Como ele usa `createReactAgent` internamente:

- **Se o deepagents aceitar `prompt` function** → passe diretamente.
- **Se não aceitar** → use `systemPrompt` com um fallback estático e aplique o dynamic prompt via pre-processing no route handler.

A abordagem segura (sem depender de tipos internos do deepagents) é manter `systemPrompt` como string e adicionar suporte a `promptFn` no route handler que pré-processa as mensagens:

Atualize `deep-agent-config.ts`:

```typescript
import {
  createDeepAgent,
  CompositeBackend,
  StateBackend,
  FilesystemBackend,
} from "deepagents";
import { SafeBackend } from "./safe-backend";
import type { BaseLanguageModel } from "@langchain/core/language_models/base";
import { getCheckpointer } from "@/lib/db/postgres";
import { searchWebTool } from "./tools/search-web";
import type { BaseMessageLike } from "@langchain/core/messages";

export interface DeepAgentOptions {
  model: BaseLanguageModel;
  /** System prompt estático. Use promptFn para prompts dinâmicos. */
  systemPrompt?: string;
  /**
   * Função de prompt dinâmico. Se fornecida, sobrepõe systemPrompt.
   * Recebe o estado atual e retorna BaseMessageLike[].
   * Compatível com a API de `prompt` function do createReactAgent.
   */
  promptFn?: (state: { messages: BaseMessageLike[] }) => BaseMessageLike[];
}

export function createOmniMindDeepAgent(options: DeepAgentOptions) {
  const checkpointer = getCheckpointer();

  // Usa systemPrompt vazio se promptFn for fornecido (o route handler aplica o promptFn)
  const systemPrompt = options.systemPrompt ?? "";

  const agent = createDeepAgent({
    model: options.model,
    systemPrompt,
    name: "omnimind-agent",
    checkpointer,
    tools: [searchWebTool],
    backend: new SafeBackend(
      new CompositeBackend(
        new FilesystemBackend({ rootDir: process.cwd() }),
        {
          "/memories/": new StateBackend({ state: {}, store: undefined }),
        }
      )
    ) as unknown as CompositeBackend,
  });

  return { agent, promptFn: options.promptFn };
}
```

**Step 3: Atualize `src/lib/agent/index.ts` para usar `buildDynamicPrompt`**

Substitua todo o conteúdo do arquivo:

```typescript
import { createOmniMindDeepAgent } from "./deep-agent-config";
import { getModelForProvider, DEFAULT_PROVIDER, DEFAULT_MODEL } from "./providers";
import { buildDynamicPrompt } from "./prompts/dynamic-prompt";
import type { LLMProvider } from "@/types/agent";

export function createOmniMindAgent(
  provider: LLMProvider = DEFAULT_PROVIDER,
  model: string = DEFAULT_MODEL,
  options: { apiKey?: string; baseUrl?: string } = {}
) {
  const llm = getModelForProvider(provider, model, options);

  return createOmniMindDeepAgent({
    model: llm,
    promptFn: buildDynamicPrompt,
    // systemPrompt omitido — buildDynamicPrompt é a fonte de verdade
  });
}

export { DEFAULT_PROVIDER, DEFAULT_MODEL };
```

**Step 4: Atualize `src/app/api/agent/chat/route.ts` para usar `promptFn`**

Localize a linha:

```typescript
const agent = createOmniMindAgent(provider, model);
```

Mude para:

```typescript
const { agent, promptFn } = createOmniMindAgent(provider, model);
```

E antes de passar as mensagens ao agente, aplique o `promptFn` se disponível:

```typescript
// Monta o input com prompt dinâmico se disponível
const inputMessages = [new HumanMessage(message)];
const agentInput = promptFn
  ? { messages: promptFn({ messages: inputMessages }) }
  : { messages: inputMessages };

const agentStream = await agent.stream(
  agentInput,
  {
    ...config,
    streamMode: ["messages", "updates"],
  }
);
```

> **Nota:** Esta abordagem funciona se `promptFn` recebe apenas o histórico inicial. Para prompts verdadeiramente dinâmicos (baseados no histórico mid-conversation), precisamos integrar com o `createReactAgent` diretamente — o que requer acesso ao tipo interno do deepagents. Se o deepagents exportar `prompt` como opção, use-a diretamente.

**Step 5: Rode type-check**

```bash
pnpm exec tsc --noEmit
```

Corrija todos os erros de tipos.

**Step 6: Rode todos os testes**

```bash
pnpm test
```

Expected: PASS.

**Step 7: Commit**

```bash
git add src/lib/agent/deep-agent-config.ts src/lib/agent/index.ts src/app/api/agent/chat/route.ts
git commit -m "feat: integrate dynamic prompt builder, remove hardcoded SYSTEM_PROMPT"
```

---

### Task 6: Verificar integração completa com servidor de dev

**Step 1: Inicie o servidor de dev**

```bash
pnpm dev
```

**Step 2: Envie uma mensagem de teste**

Abra `http://localhost:3000/agent` e envie:
- "liste os arquivos em /src"
- Verifique que o thinking aparece token-a-token (sem delay de bloco)
- Verifique que os steps mostram "Agent" e "Tools" (não nodes INTERNAL como `__start__`)

**Step 3: Abra `/logs` e verifique os eventos**

Abra `http://localhost:3000/logs` e verifique:
- Eventos `thought` chegam como tokens individuais
- Eventos `agent_step` têm detail com `[LLM_INVOKE]` ou `[TOOL_EXECUTION]`
- Nenhum node `[INTERNAL]` aparece na UI

**Step 4: Commit final se necessário**

```bash
git add -p
git commit -m "fix: agent output normalization complete"
```

---

## Resumo das Mudanças

| Arquivo | Tipo | O que muda |
|---------|------|------------|
| `src/lib/agent/chat-stream-normalizer.ts` | Modify | ThinkTag parser emite token-a-token; aceita raw string tokens; usa node-registry |
| `src/lib/agent/node-registry.ts` | Create | Classifica todos os tipos de nodes do LangGraph |
| `src/lib/agent/prompts/base.ts` | Create | Base prompt (identidade + regras gerais) |
| `src/lib/agent/prompts/tools/filesystem.ts` | Create | Prompt das filesystem tools |
| `src/lib/agent/prompts/tools/web-search.ts` | Create | Prompt da web search tool |
| `src/lib/agent/prompts/tools/task-planning.ts` | Create | Prompt da task planning tool |
| `src/lib/agent/prompts/tools/shell.ts` | Create | Prompt da shell execution tool |
| `src/lib/agent/prompts/dynamic-prompt.ts` | Create | Função que monta systemPrompt dinamicamente baseado no estado |
| `src/lib/agent/deep-agent-config.ts` | Modify | Aceita `promptFn` além de `systemPrompt` |
| `src/lib/agent/index.ts` | Modify | Remove SYSTEM_PROMPT monolítico, usa `buildDynamicPrompt` |
| `src/app/api/agent/chat/route.ts` | Modify | Aplica `promptFn` ao input do agente |
| `src/types/agent.ts` | Modify | Adiciona `nodeCategory` ao `StreamEvent.meta` |
| `src/hooks/use-agent-chat.ts` | Modify | Filtra agent_steps com `[INTERNAL]` antes de exibir |
| Testes novos | Create | `node-registry.test.ts`, `dynamic-prompt.test.ts`, token streaming test |
