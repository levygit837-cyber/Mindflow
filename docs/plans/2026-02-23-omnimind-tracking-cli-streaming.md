# OmniMind Tracking, CLI e Streaming Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar sistema de tracking de agente com aba `/logs` em tempo real, comando `omni` CLI, e corrigir 3 bugs no streaming (thinking tokens, quebras de linha, "Model Request" pós-output).

**Architecture:** Um `LogBus` singleton em memória faz pub/sub de `StreamEvent`s — o `chat/route.ts` já existente publica nele a cada emit, e uma nova rota SSE `/api/agent/logs/stream` distribui para todos os clientes conectados. A aba `/logs` consome via hook SSE com filtros e export JSON. O `omni` CLI é um script Node.js binário no `package.json`. Os bugs de streaming são 3 mudanças cirúrgicas em arquivos existentes.

**Tech Stack:** Next.js 16 App Router, TypeScript, Zustand, SSE (ReadableStream), Node.js child_process, React 19.

---

## Task 1: LogBus — pub/sub singleton em memória

**Files:**
- Create: `src/lib/agent/log-bus.ts`

### Step 1: Criar o LogBus com tipos e lógica de pub/sub

```typescript
// src/lib/agent/log-bus.ts

import type { StreamEvent } from "@/types/agent";

export interface LogEntry extends StreamEvent {
  sessionId: string;
  wallTime: string; // ISO timestamp no momento da emissão
}

type LogSubscriber = (entry: LogEntry) => void;

class LogBus {
  private subscribers = new Set<LogSubscriber>();
  // Mantém os últimos 500 entries para novos conectados
  private history: LogEntry[] = [];
  private readonly MAX_HISTORY = 500;

  publish(event: StreamEvent, sessionId: string): void {
    const entry: LogEntry = {
      ...event,
      sessionId,
      wallTime: new Date().toISOString(),
    };
    this.history.push(entry);
    if (this.history.length > this.MAX_HISTORY) {
      this.history.shift();
    }
    for (const sub of this.subscribers) {
      sub(entry);
    }
  }

  subscribe(callback: LogSubscriber): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  getHistory(): LogEntry[] {
    return [...this.history];
  }

  clear(): void {
    this.history = [];
  }
}

// Singleton: garantido pelo module cache do Node.js
export const logBus = new LogBus();
```

### Step 2: Commit

```bash
git add src/lib/agent/log-bus.ts
git commit -m "feat(logs): add LogBus singleton for agent event pub/sub"
```

---

## Task 2: Integrar LogBus no chat/route.ts

**Files:**
- Modify: `src/app/api/agent/chat/route.ts`

### Step 1: Verificar o estado atual do arquivo

Ler `src/app/api/agent/chat/route.ts` para confirmar a estrutura da função `emit`.

### Step 2: Adicionar a publicação no LogBus

Localizar o bloco `const emit = (...)` dentro do `POST` handler e adicionar `logBus.publish(event, sessionId)` logo após `send(event)`.

O diff a aplicar:

```typescript
// No topo do arquivo, adicionar import:
import { logBus } from "@/lib/agent/log-bus";

// Dentro de POST(), gerar sessionId antes do emit:
const sessionId = conversationId || `session-${Date.now()}`;

// Dentro da função emit, após send(event):
send(event);
logBus.publish(event, sessionId);
```

O bloco completo do `emit` ficará assim:

```typescript
const sessionId = conversationId || `session-${Date.now()}`;

const emit = (
  type: StreamEventType,
  data: string,
  mode: StreamModeName,
  meta: StreamEvent["meta"] = {}
) => {
  const event: StreamEvent = {
    id: `evt-${Date.now()}-${seq + 1}`,
    seq: ++seq,
    type,
    mode,
    data,
    meta: {
      provider,
      model,
      ...meta,
    },
  };
  send(event);
  logBus.publish(event, sessionId);
};
```

### Step 3: Commit

```bash
git add src/app/api/agent/chat/route.ts
git commit -m "feat(logs): publish agent events to LogBus in chat route"
```

---

## Task 3: Rota SSE `/api/agent/logs/stream`

**Files:**
- Create: `src/app/api/agent/logs/stream/route.ts`

### Step 1: Criar a rota SSE que escuta o LogBus

```typescript
// src/app/api/agent/logs/stream/route.ts

import { logBus } from "@/lib/agent/log-bus";
import type { LogEntry } from "@/lib/agent/log-bus";

export const dynamic = "force-dynamic";

export async function GET() {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      // Enviar histórico imediatamente ao conectar
      const history = logBus.getHistory();
      for (const entry of history) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(entry)}\n\n`)
        );
      }

      // Enviar evento de conexão
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ type: "connected" })}\n\n`)
      );

      // Assinar novos eventos
      const unsubscribe = logBus.subscribe((entry: LogEntry) => {
        try {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(entry)}\n\n`)
          );
        } catch {
          // Stream fechado pelo cliente
          unsubscribe();
        }
      });

      // Cleanup quando o cliente desconecta
      // Next.js fecha o stream automaticamente quando a conexão cai
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
```

### Step 2: Testar manualmente (após iniciar o servidor)

```bash
curl -N http://localhost:3000/api/agent/logs/stream
```

Deve ficar aberto aguardando eventos. Ao enviar uma mensagem no chat, devem aparecer linhas `data: {...}` no terminal.

### Step 3: Commit

```bash
git add src/app/api/agent/logs/stream/route.ts
git commit -m "feat(logs): add SSE endpoint /api/agent/logs/stream"
```

---

## Task 4: Hook `use-log-stream` no frontend

**Files:**
- Create: `src/hooks/use-log-stream.ts`

### Step 1: Criar o hook com filtros e estado

```typescript
// src/hooks/use-log-stream.ts
"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { LogEntry } from "@/lib/agent/log-bus";

export type LogFilter =
  | "all"
  | "thought"
  | "tool_call"
  | "tool_result"
  | "response"
  | "agent_step"
  | "done"
  | "error";

export function useLogStream() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState<LogFilter>("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const seenIds = useRef(new Set<string>());

  useEffect(() => {
    const es = new EventSource("/api/agent/logs/stream");
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (e) => {
      try {
        const entry = JSON.parse(e.data as string) as LogEntry & { type?: string };
        if (entry.type === "connected") return;
        if (!entry.id || seenIds.current.has(entry.id)) return;
        seenIds.current.add(entry.id);

        setEntries((prev) => [...prev, entry as LogEntry]);
        setUnreadCount((n) => n + 1);
      } catch {
        // ignorar eventos malformados
      }
    };

    es.onerror = () => setConnected(false);

    return () => {
      es.close();
      setConnected(false);
    };
  }, []);

  const clearEntries = useCallback(() => {
    setEntries([]);
    seenIds.current.clear();
    setUnreadCount(0);
  }, []);

  const resetUnread = useCallback(() => setUnreadCount(0), []);

  const filteredEntries =
    filter === "all"
      ? entries
      : entries.filter((e) => e.type === filter);

  const exportJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(filteredEntries, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `omnimind-logs-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filteredEntries]);

  return {
    entries: filteredEntries,
    allEntries: entries,
    connected,
    filter,
    setFilter,
    autoScroll,
    setAutoScroll,
    unreadCount,
    resetUnread,
    clearEntries,
    exportJson,
  };
}
```

### Step 2: Commit

```bash
git add src/hooks/use-log-stream.ts
git commit -m "feat(logs): add useLogStream hook with filter and export"
```

---

## Task 5: Componente `LogViewer`

**Files:**
- Create: `src/components/logs/log-viewer.tsx`

### Step 1: Criar o componente

```typescript
// src/components/logs/log-viewer.tsx
"use client";

import React, { useEffect, useRef, useState } from "react";
import { Download, Trash2, ChevronDown, ChevronUp, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useLogStream, type LogFilter } from "@/hooks/use-log-stream";
import type { LogEntry } from "@/lib/agent/log-bus";

const FILTER_OPTIONS: { value: LogFilter; label: string }[] = [
  { value: "all", label: "ALL" },
  { value: "thought", label: "THOUGHT" },
  { value: "tool_call", label: "TOOL" },
  { value: "tool_result", label: "RESULT" },
  { value: "response", label: "RESP" },
  { value: "agent_step", label: "STEP" },
  { value: "error", label: "ERROR" },
];

const TYPE_COLORS: Record<string, string> = {
  thought: "text-violet-400",
  tool_call: "text-yellow-400",
  tool_result: "text-green-400",
  response: "text-zinc-300",
  agent_step: "text-blue-400",
  done: "text-emerald-400",
  error: "text-red-400",
  step: "text-zinc-500",
  notifier: "text-zinc-500",
};

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toTimeString().slice(0, 8) + "." + String(d.getMilliseconds()).padStart(3, "0");
  } catch {
    return iso.slice(11, 23);
  }
}

function summarizeData(type: string, data: string): string {
  if (!data) return "";
  if (type === "tool_call" || type === "tool_result") {
    try {
      const parsed = JSON.parse(data) as { name?: string; result?: string; args?: unknown };
      if (parsed.name) {
        const extra = parsed.result
          ? ` → ${parsed.result.slice(0, 60)}`
          : parsed.args
          ? `(${JSON.stringify(parsed.args).slice(0, 60)})`
          : "";
        return `${parsed.name}${extra}`;
      }
    } catch {
      // fall through
    }
  }
  return data.length > 120 ? data.slice(0, 120) + "…" : data;
}

function LogRow({ entry }: { entry: LogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const color = TYPE_COLORS[entry.type] ?? "text-zinc-400";

  return (
    <div className="border-b border-zinc-800/50 hover:bg-white/[0.02] transition-colors">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-2 px-3 py-1.5 text-left"
      >
        <span className="text-zinc-600 font-mono text-[10px] shrink-0 pt-0.5 tabular-nums">
          {formatTime(entry.wallTime)}
        </span>
        <span className={cn("font-mono text-[10px] font-bold shrink-0 pt-0.5 w-16", color)}>
          [{entry.type.toUpperCase().slice(0, 8)}]
        </span>
        <span className="text-zinc-400 text-[11px] font-mono truncate flex-1 min-w-0">
          {summarizeData(entry.type, entry.data)}
        </span>
        {expanded ? (
          <ChevronUp className="h-3 w-3 text-zinc-600 shrink-0 mt-0.5" />
        ) : (
          <ChevronDown className="h-3 w-3 text-zinc-600 shrink-0 mt-0.5" />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-2">
          <pre className="text-[10px] font-mono text-zinc-500 bg-zinc-900/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all border border-zinc-800">
            {JSON.stringify(entry, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export function LogViewer() {
  const {
    entries,
    connected,
    filter,
    setFilter,
    autoScroll,
    setAutoScroll,
    clearEntries,
    exportJson,
    resetUnread,
  } = useLogStream();

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    resetUnread();
  }, [resetUnread]);

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [entries, autoScroll]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] backdrop-blur-sm bg-white/[0.02]">
        <div className="flex items-center gap-2">
          {connected ? (
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-red-400" />
          )}
          <span className="text-xs text-zinc-400 font-medium">
            Agent Logs
          </span>
          <span className="text-xs text-zinc-600 font-mono">
            ({entries.length})
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setAutoScroll((v) => !v)}
            className={cn(
              "text-xs h-7 px-2",
              autoScroll
                ? "text-zinc-300"
                : "text-zinc-600"
            )}
          >
            Auto-scroll
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={exportJson}
            className="text-muted-foreground/60 hover:text-foreground/80 hover:bg-white/[0.05] h-7 px-2"
          >
            <Download className="h-3.5 w-3.5 mr-1" />
            Export
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearEntries}
            className="text-muted-foreground/60 hover:text-foreground/80 hover:bg-white/[0.05] h-7 px-2"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            Clear
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-1 px-3 py-1.5 border-b border-white/[0.04] overflow-x-auto">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFilter(opt.value)}
            className={cn(
              "text-[10px] font-mono font-bold px-2 py-0.5 rounded shrink-0 transition-colors",
              filter === opt.value
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-600 hover:text-zinc-400"
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Log entries */}
      <ScrollArea className="flex-1">
        {entries.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-zinc-600 text-xs font-mono">
            {connected ? "Aguardando eventos do agente..." : "Desconectado"}
          </div>
        ) : (
          <div>
            {entries.map((entry) => (
              <LogRow key={entry.id} entry={entry} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
```

### Step 2: Commit

```bash
git add src/components/logs/log-viewer.tsx
git commit -m "feat(logs): add LogViewer component with filters and expandable rows"
```

---

## Task 6: Página `/logs` e entrada na sidebar

**Files:**
- Create: `src/app/logs/page.tsx`
- Modify: `src/components/layout/sidebar.tsx`

### Step 1: Criar a página

```typescript
// src/app/logs/page.tsx
import { LogViewer } from "@/components/logs/log-viewer";

export default function LogsPage() {
  return (
    <div className="h-full flex flex-col">
      <LogViewer />
    </div>
  );
}
```

### Step 2: Adicionar item na sidebar

Em `src/components/layout/sidebar.tsx`, localizar o array `navItems` e adicionar o item de Logs:

```typescript
// Adicionar import no topo:
import { Brain, Bot, Settings, Users, ScrollText } from "lucide-react";

// Adicionar ao array navItems:
{ href: "/logs", label: "Logs", icon: ScrollText },
```

O array final ficará:

```typescript
const navItems = [
  { href: "/", label: "Dashboard", icon: Brain },
  { href: "/agent", label: "Deep Agent", icon: Bot },
  { href: "/swarm", label: "Swarm", icon: Users },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];
```

### Step 3: Commit

```bash
git add src/app/logs/page.tsx src/components/layout/sidebar.tsx
git commit -m "feat(logs): add /logs page and sidebar navigation item"
```

---

## Task 7: Corrigir "Model Request" aparecendo após output

**Files:**
- Modify: `src/lib/agent/chat-stream-normalizer.ts`

**Contexto:** A função `isUserVisibleUpdateNode` retorna `true` para `"model_request"`. O nó `model_request` do LangGraph é emitido no final do ciclo (após o output do agente), causando o bloco "Model Request" aparecer depois da resposta. Basta removê-lo da lista de nós visíveis.

### Step 1: Localizar e corrigir

Encontrar a linha:

```typescript
return nodeName === "tools" || nodeName === "model_request" || nodeName === "agent";
```

Substituir por:

```typescript
return nodeName === "tools" || nodeName === "agent";
```

Encontrar também:

```typescript
if (nodeName === "model_request") return "Model request";
```

E remover essa linha (o `userVisibleUpdateLabel` nunca mais será chamado com `"model_request"`).

### Step 2: Verificar o teste existente

```bash
pnpm test -- --reporter=verbose 2>&1 | grep -i "model_request\|normalizer"
```

O teste em `src/lib/agent/__tests__/chat-stream-normalizer.test.ts` linha 372 espera `"Model request"` — precisará ser atualizado.

Localizar no teste:

```typescript
expect(steps).toContain("Model request");
```

E remover ou alterar para verificar que `"Model request"` **não** está nos steps:

```typescript
expect(steps).not.toContain("Model request");
```

### Step 3: Rodar os testes

```bash
pnpm test
```

Expected: PASS

### Step 4: Commit

```bash
git add src/lib/agent/chat-stream-normalizer.ts src/lib/agent/__tests__/chat-stream-normalizer.test.ts
git commit -m "fix(streaming): remove model_request from visible agent steps"
```

---

## Task 8: Corrigir thinking tokens streamando em tempo real

**Files:**
- Modify: `src/components/agent/thinking-block.tsx`

**Contexto:** O `ThinkingBlock` quando `isStreaming && !expanded` mostra apenas um indicador de "Thinking" sem conteúdo. O usuário clica para expandir e vê tudo de uma vez (sem streaming progressivo visível). O fix: mostrar os últimos ~120 caracteres do `content` inline mesmo antes de expandir, dando feedback visual do que está sendo processado.

### Step 1: Localizar o bloco de streaming state

Em `thinking-block.tsx`, localizar:

```typescript
// Streaming state: compact inline indicator
if (isStreaming && !expanded) {
  return (
    <div className="flex items-center gap-2 py-1">
      <button
        onClick={() => setExpanded(true)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-pulse" />
        <span className="font-medium">
          {agentId ? `${agentId} thinking` : "Thinking"}
        </span>
        {tokenCount > 0 && (
          <span className="text-zinc-600 font-mono text-[10px]">
            ~{formatTokenCount(tokenCount)}t
          </span>
        )}
        <ChevronRight className="h-3 w-3 text-zinc-600" />
      </button>
    </div>
  );
}
```

Substituir por:

```typescript
// Streaming state: indicador compacto com preview dos últimos tokens
if (isStreaming && !expanded) {
  const previewText = content.length > 0
    ? content.slice(-120).replace(/\n+/g, " ").trim()
    : "";

  return (
    <div className="flex flex-col gap-0.5 py-1">
      <button
        onClick={() => setExpanded(true)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-pulse" />
        <span className="font-medium">
          {agentId ? `${agentId} thinking` : "Thinking"}
        </span>
        {tokenCount > 0 && (
          <span className="text-zinc-600 font-mono text-[10px]">
            ~{formatTokenCount(tokenCount)}t
          </span>
        )}
        <ChevronRight className="h-3 w-3 text-zinc-600" />
      </button>
      {previewText && (
        <div className="ml-4 pl-3 border-l border-zinc-800">
          <span className="text-[10px] font-mono text-zinc-600 italic line-clamp-2">
            {previewText}
            <span className="ml-0.5 inline-block w-1 h-2.5 bg-zinc-600 animate-typewriter-blink rounded-sm align-middle" />
          </span>
        </div>
      )}
    </div>
  );
}
```

### Step 2: Verificar o teste existente

```bash
pnpm test -- src/components/agent/__tests__/thinking-block.test.tsx --reporter=verbose
```

### Step 3: Commit

```bash
git add src/components/agent/thinking-block.tsx
git commit -m "fix(streaming): show live token preview in thinking block during streaming"
```

---

## Task 9: Corrigir quebras de linha inacabadas no ResponseBlock

**Files:**
- Modify: `src/components/agent/response-block.tsx`

**Contexto:** Durante o streaming, o `ReactMarkdown` tenta parsear markdown parcial a cada token. Um `\n\n` incompleto ou um bloco de código não fechado criam parágrafos quebrados ou elementos flutuantes. O fix: enquanto `isStreaming: true`, renderizar como texto plano em `<pre>`; quando completo (`isStreaming: false`), renderizar com `ReactMarkdown`.

### Step 1: Modificar o ResponseBlock

Localizar:

```typescript
function ResponseBlockInner({ content, isStreaming }: ResponseBlockProps) {
  if (!content && !isStreaming) return null;

  return (
    <div className="py-1">
      <div
        className={cn(
          "prose prose-sm dark:prose-invert",
          // ... classes
        )}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {content}
        </ReactMarkdown>
        {isStreaming && (
          <span
            className={cn(
              "ml-0.5 inline-block w-1 h-4 rounded-sm",
              "bg-zinc-400 animate-typewriter-blink"
            )}
          />
        )}
      </div>
    </div>
  );
}
```

Substituir por:

```typescript
function ResponseBlockInner({ content, isStreaming }: ResponseBlockProps) {
  if (!content && !isStreaming) return null;

  // Durante o streaming, usar texto plano para evitar markdown parcial quebrado
  if (isStreaming) {
    return (
      <div className="py-1">
        <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap font-sans">
          {content}
          <span
            className={cn(
              "ml-0.5 inline-block w-1 h-4 rounded-sm align-middle",
              "bg-zinc-400 animate-typewriter-blink"
            )}
          />
        </div>
      </div>
    );
  }

  // Quando completo, renderizar markdown completo
  return (
    <div className="py-1">
      <div
        className={cn(
          "prose prose-sm dark:prose-invert",
          "prose-p:my-1.5 prose-headings:my-2 prose-pre:my-2",
          "prose-code:before:content-none prose-code:after:content-none",
          "prose-code:rounded-md prose-code:bg-zinc-800/60 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[13px] prose-code:font-mono prose-code:text-zinc-300",
          "prose-pre:rounded-lg prose-pre:bg-zinc-900/60 prose-pre:border prose-pre:border-zinc-800 prose-pre:text-zinc-300",
          "prose-a:text-zinc-400 prose-a:underline prose-a:decoration-zinc-700 hover:prose-a:text-zinc-300",
          "prose-table:text-xs prose-th:text-left",
          "prose-li:my-0.5",
          "prose-strong:text-zinc-200",
          "prose-headings:text-zinc-200",
          "text-zinc-300"
        )}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
```

### Step 2: Rodar os testes

```bash
pnpm test
```

Expected: PASS

### Step 3: Commit

```bash
git add src/components/agent/response-block.tsx
git commit -m "fix(streaming): render plain text during streaming to avoid broken markdown"
```

---

## Task 10: CLI `omni`

**Files:**
- Create: `omni.js`
- Modify: `package.json`

**Contexto:** O `start.sh` e `start.js` já existem mas não são instaláveis como CLI. Criar um `omni.js` que suporte `omni` (inicia o servidor) e `omni --logs` (inicia o servidor + stream de logs no terminal formatado por tipo).

### Step 1: Criar `omni.js`

```javascript
#!/usr/bin/env node
// omni.js — CLI do OmniMind
// Uso: node omni.js [--logs]

const { spawn } = require("child_process");
const http = require("http");

const args = process.argv.slice(2);
const showLogs = args.includes("--logs");

// Cores ANSI
const C = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  bold: "\x1b[1m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
  magenta: "\x1b[35m",
  red: "\x1b[31m",
  white: "\x1b[37m",
  gray: "\x1b[90m",
};

const TYPE_COLOR = {
  thought: C.magenta,
  tool_call: C.yellow,
  tool_result: C.green,
  response: C.white,
  agent_step: C.blue,
  done: C.cyan,
  error: C.red,
  step: C.gray,
  notifier: C.gray,
};

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toTimeString().slice(0, 8) + "." + String(d.getMilliseconds()).padStart(3, "0");
  } catch {
    return "";
  }
}

function summarize(type, data) {
  if (!data) return "";
  if (type === "tool_call" || type === "tool_result") {
    try {
      const p = JSON.parse(data);
      if (p.name) {
        const extra = p.result
          ? ` → ${p.result.slice(0, 80)}`
          : p.args
          ? `(${JSON.stringify(p.args).slice(0, 80)})`
          : "";
        return `${p.name}${extra}`;
      }
    } catch {}
  }
  const str = typeof data === "string" ? data : JSON.stringify(data);
  return str.replace(/\n/g, " ").slice(0, 100);
}

function printLog(entry) {
  const color = TYPE_COLOR[entry.type] || C.gray;
  const time = C.gray + formatTime(entry.wallTime || entry.meta?.timestamp || new Date().toISOString()) + C.reset;
  const tag = color + C.bold + `[${(entry.type || "?").toUpperCase().slice(0, 8).padEnd(8)}]` + C.reset;
  const content = C.dim + summarize(entry.type, entry.data) + C.reset;
  const session = entry.sessionId ? C.gray + ` (${entry.sessionId.slice(0, 12)})` + C.reset : "";
  process.stdout.write(`${time} ${tag} ${content}${session}\n`);
}

function connectLogs(retries = 0) {
  const MAX_RETRIES = 30;
  const req = http.get("http://localhost:3000/api/agent/logs/stream", (res) => {
    process.stdout.write(`${C.green}${C.bold}● Logs conectados${C.reset}\n`);
    let buffer = "";
    res.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const entry = JSON.parse(line.slice(6));
          if (entry.type === "connected") continue;
          printLog(entry);
        } catch {}
      }
    });
    res.on("end", () => {
      process.stdout.write(`${C.yellow}Logs desconectados. Reconectando...${C.reset}\n`);
      setTimeout(() => connectLogs(0), 2000);
    });
  });

  req.on("error", () => {
    if (retries < MAX_RETRIES) {
      setTimeout(() => connectLogs(retries + 1), 1000);
    } else {
      process.stdout.write(`${C.red}Não foi possível conectar ao stream de logs.${C.reset}\n`);
    }
  });
}

// Iniciar o servidor Next.js
process.stdout.write(`${C.bold}${C.cyan}🧠 OmniMind${C.reset}\n`);
if (showLogs) {
  process.stdout.write(`${C.gray}Modo: servidor + logs em tempo real${C.reset}\n\n`);
} else {
  process.stdout.write(`${C.gray}Modo: servidor${C.reset}\n\n`);
}

const server = spawn("pnpm", ["dev"], {
  cwd: __dirname,
  stdio: "inherit",
  shell: true,
});

if (showLogs) {
  // Aguardar o servidor subir antes de conectar aos logs
  process.stdout.write(`${C.gray}Aguardando servidor iniciar...${C.reset}\n`);
  setTimeout(() => connectLogs(), 4000);
}

server.on("close", (code) => {
  process.exit(code ?? 0);
});

process.on("SIGINT", () => {
  server.kill("SIGINT");
  process.exit(0);
});

process.on("SIGTERM", () => {
  server.kill("SIGTERM");
  process.exit(0);
});
```

### Step 2: Tornar executável

```bash
chmod +x omni.js
```

### Step 3: Adicionar entrada `bin` no package.json

Localizar em `package.json` o campo `"scripts"` e adicionar `"bin"` antes ou depois:

```json
"bin": {
  "omni": "./omni.js"
},
```

O `package.json` ficará:

```json
{
  "name": "omnimind",
  "version": "2.0.0",
  "private": true,
  "bin": {
    "omni": "./omni.js"
  },
  "scripts": {
    ...
  }
}
```

### Step 4: Testar sem instalar globalmente

```bash
node omni.js
# Deve iniciar o servidor normalmente

# Em outro terminal:
node omni.js --logs
# Deve iniciar o servidor e após ~4s mostrar logs formatados
```

### Step 5: Commit

```bash
git add omni.js package.json
git commit -m "feat(cli): add omni CLI with --logs flag for real-time agent monitoring"
```

---

## Task 11: Salvar onboarding no Serena

**Files:**
- (memória do Serena, não é um arquivo do projeto)

### Step 1: Escrever memória do projeto

Registrar no Serena os comandos sugeridos e overview do projeto OmniMind para futuros agentes.

```
Comandos:
- pnpm dev           → inicia o servidor (http://localhost:3000)
- node omni.js       → idem via CLI
- node omni.js --logs → servidor + stream de logs no terminal
- pnpm test          → Vitest
- pnpm build         → build de produção
```

---

## Ordem de Execução Recomendada

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6
(infraestrutura de logs, de baixo para cima)

Task 7 (fix rápido, independente)
Task 8 (fix rápido, independente)
Task 9 (fix rápido, independente)
Task 10 (CLI, independente)
Task 11 (onboarding, por último)
```

Tasks 7, 8, 9 e 10 são **completamente independentes** e podem ser feitas em qualquer ordem (ou em paralelo se usando agentes paralelos).
