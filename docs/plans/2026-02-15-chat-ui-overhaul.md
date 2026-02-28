# Chat UI Overhaul - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix message splitting bugs, redesign all chat output components with dark/minimal aesthetic, add compact inline indicators, and expose agent delegation steps as visible output.

**Architecture:** Three-layer approach: (1) Fix the store's content-part merging logic so thoughts/text never split across multiple parts unnecessarily; (2) Redesign every output component (ThinkingBlock, ToolCallBlock, ResponseBlock, notifiers) to be compact, dark-themed, inline indicators instead of full-width panels; (3) Add a new `AgentStepsBlock` component that renders task delegation steps inline as expandable output.

**Tech Stack:** React 19, Next.js 16, Tailwind CSS v4, Zustand, Lucide icons, react-markdown

---

### Task 1: Fix Message Splitting - Consolidate Consecutive Thinking Parts in Store

**Files:**
- Modify: `src/stores/agent-store.ts:162-190` (appendThought method)
- Modify: `src/stores/agent-store.ts:136-160` (appendToAssistant method)

**Problem:** When a tool_call or notifier is inserted between two thinking chunks, `appendThought` creates a NEW thinking part instead of appending to the existing one. Same issue with `appendToAssistant` creating multiple text parts. This causes message "splitting" visually.

**Step 1: Fix `appendThought` to find the last thinking part (not just the last part)**

Open `src/stores/agent-store.ts` and replace the `appendThought` method:

```typescript
appendThought: (id, thought) => {
  set((state) => ({
    messages: state.messages.map((m) => {
      if (m.id !== id) return m;

      const parts = [...m.contentParts];

      // Find the last thinking part anywhere in the array (not just the very last part)
      let lastThinkingIdx = -1;
      for (let i = parts.length - 1; i >= 0; i--) {
        if (parts[i].type === "thinking" && parts[i].isStreaming) {
          lastThinkingIdx = i;
          break;
        }
      }

      if (lastThinkingIdx >= 0) {
        // Append to the existing streaming thinking part
        const existing = parts[lastThinkingIdx];
        parts[lastThinkingIdx] = {
          ...existing,
          content: existing.content + thought,
        };
      } else {
        // Check if the last part is a finished thinking block — start a new one
        parts.push({
          type: "thinking",
          id: nextPartId(),
          content: thought,
          isStreaming: true,
        });
      }

      return {
        ...m,
        thoughts: m.thoughts + thought,
        contentParts: parts,
      };
    }),
  }));
},
```

**Step 2: Fix `appendToAssistant` to find the last text part (not just the last part)**

Replace the `appendToAssistant` method:

```typescript
appendToAssistant: (id, text) => {
  set((state) => ({
    messages: state.messages.map((m) => {
      if (m.id !== id) return m;

      const parts = [...m.contentParts];

      // Find the last text part anywhere in the array
      let lastTextIdx = -1;
      for (let i = parts.length - 1; i >= 0; i--) {
        if (parts[i].type === "text") {
          lastTextIdx = i;
          break;
        }
      }

      if (lastTextIdx >= 0) {
        // Append to the existing text part
        const existing = parts[lastTextIdx];
        parts[lastTextIdx] = {
          ...existing,
          content: existing.content + text,
        };
      } else {
        parts.push({ type: "text", id: nextPartId(), content: text });
      }

      return {
        ...m,
        content: m.content + text,
        contentParts: parts,
      };
    }),
  }));
},
```

**Step 3: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 4: Commit**

```bash
git add src/stores/agent-store.ts
git commit -m "fix: consolidate thinking and text parts to prevent message splitting"
```

---

### Task 2: Redesign ThinkingBlock - Compact Inline "Thinking" Indicator

**Files:**
- Modify: `src/components/agent/thinking-block.tsx` (full rewrite)

**Goal:** Replace the full-width glass panel with a compact, dark inline indicator. When streaming: show a small "Thinking..." label with subtle animation. When done: show a compact expandable "Thought for X tokens" chip. Never full-width.

**Step 1: Rewrite thinking-block.tsx**

Replace the entire content of `src/components/agent/thinking-block.tsx`:

```tsx
"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThinkingBlockProps {
  id: string;
  content: string;
  isStreaming: boolean;
  agentId?: string;
  agentColor?: string;
}

function estimateTokenCount(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

function formatTokenCount(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return String(count);
}

function parseReasoningContent(text: string): React.ReactNode[] {
  if (!text) return [];
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-zinc-300">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

function ThinkingBlockInner({
  content,
  isStreaming,
  agentId,
}: ThinkingBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isStreaming && expanded && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [content, isStreaming, expanded]);

  if (!content && !isStreaming) return null;

  const tokenCount = estimateTokenCount(content);

  // Streaming state: compact inline indicator
  if (isStreaming && !expanded) {
    return (
      <div className="flex items-center gap-2 py-1.5 animate-fade-in-up">
        <button
          onClick={() => setExpanded(true)}
          className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-zinc-500/40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-zinc-500" />
          </span>
          <span className="font-medium">
            {agentId ? `${agentId} thinking` : "Thinking"}
          </span>
          <span className="text-zinc-600 font-mono text-[10px]">
            ~{formatTokenCount(tokenCount)}t
          </span>
          <ChevronRight className="h-3 w-3 text-zinc-600" />
        </button>
      </div>
    );
  }

  // Completed or expanded state: compact expandable
  return (
    <div className="py-1 animate-fade-in-up">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 text-zinc-600 transition-transform duration-200",
            expanded && "rotate-90"
          )}
        />
        <span className="font-medium">
          {agentId ? `${agentId} thought` : "Thought"}
        </span>
        <span className="text-zinc-600 font-mono text-[10px]">
          {formatTokenCount(tokenCount)} tokens
        </span>
      </button>

      {expanded && (
        <div className="mt-1.5 ml-4 pl-3 border-l border-zinc-800">
          <div
            ref={scrollRef}
            className="max-h-72 overflow-y-auto whitespace-pre-wrap text-xs text-zinc-500 leading-relaxed font-mono scrollbar-thin"
          >
            {parseReasoningContent(content)}
            {isStreaming && (
              <span className="ml-0.5 inline-block w-1 h-3 bg-zinc-500 animate-typewriter-blink rounded-sm" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export const ThinkingBlock = React.memo(ThinkingBlockInner);
```

**Step 2: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add src/components/agent/thinking-block.tsx
git commit -m "feat: redesign ThinkingBlock as compact inline indicator"
```

---

### Task 3: Redesign ToolCallBlock - Compact Inline Tool Indicator

**Files:**
- Modify: `src/components/agent/tool-call-block.tsx` (full rewrite)

**Goal:** Replace full-width colored panels with compact inline rows. Running tools show a subtle spinner + name. Completed tools show a checkmark + name + duration. Expandable for input/output details. Dark muted colors only.

**Step 1: Rewrite tool-call-block.tsx**

Replace the entire content of `src/components/agent/tool-call-block.tsx`:

```tsx
"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronRight, Loader2, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { getToolConfig } from "./tool-icon-map";

interface ToolCallBlockProps {
  id: string;
  toolName: string;
  toolInput: Record<string, unknown>;
  toolOutput: string | null | undefined;
  status: "pending" | "running" | "success" | "error";
  startedAt: string;
  completedAt?: string;
  agentId?: string;
  agentColor?: string;
}

function argsSummary(toolName: string, args: Record<string, unknown>): string {
  for (const key of ["path", "filePath", "file_path", "noteId", "query", "command", "pattern", "url", "glob"]) {
    if (key in args && args[key] != null) {
      const val = String(args[key]);
      return val.length > 50 ? val.slice(0, 47) + "..." : val;
    }
  }
  const keys = Object.keys(args);
  if (keys.length === 0) return "";
  const first = String(args[keys[0]] ?? "");
  return first.length > 50 ? first.slice(0, 47) + "..." : first;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}

function ElapsedTimer({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(new Date(startedAt).getTime());

  useEffect(() => {
    startRef.current = new Date(startedAt).getTime();
    const interval = setInterval(() => {
      setElapsed(Date.now() - startRef.current);
    }, 100);
    return () => clearInterval(interval);
  }, [startedAt]);

  return (
    <span className="text-[10px] font-mono text-zinc-600 tabular-nums">
      {formatDuration(elapsed)}
    </span>
  );
}

function StatusDot({ status }: { status: ToolCallBlockProps["status"] }) {
  switch (status) {
    case "pending":
      return <span className="h-1.5 w-1.5 rounded-full bg-zinc-600" />;
    case "running":
      return <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />;
    case "success":
      return <Check className="h-3 w-3 text-emerald-500/70" />;
    case "error":
      return <X className="h-3 w-3 text-red-400/70" />;
  }
}

function ToolCallBlockInner({
  toolName,
  toolInput,
  toolOutput,
  status,
  startedAt,
  completedAt,
  agentId,
}: ToolCallBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const config = getToolConfig(toolName);
  const Icon = config.icon;
  const summary = argsSummary(toolName, toolInput);

  const completedMs = completedAt
    ? new Date(completedAt).getTime() - new Date(startedAt).getTime()
    : null;

  return (
    <div className="py-0.5 animate-fade-in-up">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors w-full text-left"
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 text-zinc-600 shrink-0 transition-transform duration-200",
            expanded && "rotate-90"
          )}
        />

        <StatusDot status={status} />

        <Icon className="h-3 w-3 shrink-0 text-zinc-500" />

        <span className="font-medium text-zinc-400">{config.label}</span>

        {agentId && (
          <span className="text-[10px] text-zinc-600 font-mono">
            [{agentId}]
          </span>
        )}

        {summary && (
          <span className="min-w-0 flex-1 truncate text-zinc-600 font-mono text-[11px]">
            {summary}
          </span>
        )}

        <span className="ml-auto flex items-center gap-1.5 shrink-0">
          {status === "running" && <ElapsedTimer startedAt={startedAt} />}
          {completedMs != null && (
            <span className="text-[10px] font-mono text-zinc-600 tabular-nums">
              {formatDuration(completedMs)}
            </span>
          )}
        </span>
      </button>

      {expanded && (
        <div className="ml-4 mt-1 pl-3 border-l border-zinc-800 space-y-2 pb-1">
          {Object.keys(toolInput).length > 0 && (
            <div>
              <span className="text-[10px] font-medium text-zinc-600 uppercase tracking-wider">
                Input
              </span>
              <pre className="mt-0.5 max-h-32 overflow-auto whitespace-pre-wrap rounded-lg bg-zinc-900/50 border border-zinc-800 p-2 text-[11px] font-mono text-zinc-500">
                {JSON.stringify(toolInput, null, 2)}
              </pre>
            </div>
          )}

          {toolOutput != null && (
            <div>
              <span className="text-[10px] font-medium text-zinc-600 uppercase tracking-wider">
                Output
              </span>
              <pre className="mt-0.5 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-zinc-900/50 border border-zinc-800 p-2 text-[11px] font-mono text-zinc-500">
                {toolOutput}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export const ToolCallBlock = React.memo(ToolCallBlockInner);
```

**Step 2: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add src/components/agent/tool-call-block.tsx
git commit -m "feat: redesign ToolCallBlock as compact inline indicator"
```

---

### Task 4: Redesign ResponseBlock - Clean Borderless Text

**Files:**
- Modify: `src/components/agent/response-block.tsx` (rewrite)

**Goal:** Remove the glass card wrapper from response text. Markdown text should flow naturally without borders or backgrounds. Just clean text against the dark background.

**Step 1: Rewrite response-block.tsx**

Replace the entire content of `src/components/agent/response-block.tsx`:

```tsx
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { cn } from "@/lib/utils";

interface ResponseBlockProps {
  content: string;
  isStreaming: boolean;
}

function ResponseBlockInner({ content, isStreaming }: ResponseBlockProps) {
  if (!content && !isStreaming) return null;

  return (
    <div className="py-1 animate-fade-in-up">
      <div
        className={cn(
          "prose prose-sm dark:prose-invert max-w-none",
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

export const ResponseBlock = React.memo(ResponseBlockInner);
```

**Step 2: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add src/components/agent/response-block.tsx
git commit -m "feat: redesign ResponseBlock as clean borderless text"
```

---

### Task 5: Redesign Notifiers - Minimal Inline Labels

**Files:**
- Modify: `src/components/agent/chat-interface.tsx:78-92` (notifier rendering)

**Goal:** Replace full-width pill badges with ultra-compact inline text labels. Just a dimmed label, no backgrounds, no borders, no icons.

**Step 1: Replace the notifier rendering in ContentPartRenderer**

In `src/components/agent/chat-interface.tsx`, replace the `case "notifier":` block (lines 78-92):

```tsx
    case "notifier":
      return (
        <div className="py-0.5 animate-fade-in-up">
          <span className="text-[10px] text-zinc-700 font-mono">
            {part.label}
          </span>
        </div>
      );
```

**Step 2: Remove unused notifier imports**

In `src/components/agent/chat-interface.tsx`, remove these unused imports from the lucide-react import:
- `Zap`
- `GitBranch`
- `AlertTriangle`
- `Play`
- `Square`
- `AlertCircle`

And remove the entire `notifierIcon` function (lines 20-37).

The import line should become:
```tsx
import { Trash2, Bot } from "lucide-react";
```

**Step 3: Remove the NotifierType import if no longer needed**

Update the type import:
```tsx
import type { ContentPart } from "@/types/agent";
```

**Step 4: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 5: Commit**

```bash
git add src/components/agent/chat-interface.tsx
git commit -m "feat: simplify notifiers to minimal inline labels"
```

---

### Task 6: Add Agent Steps Block - Expose Task Delegation Steps

**Files:**
- Create: `src/components/agent/agent-steps-block.tsx`
- Modify: `src/types/agent.ts` (add AgentStepPart type)
- Modify: `src/stores/agent-store.ts` (add agent_step support)
- Modify: `src/hooks/use-agent-chat.ts` (handle agent_step events)
- Modify: `src/components/agent/chat-interface.tsx` (render agent steps)

**Goal:** When the agent delegates a task, show the delegation steps (sub-agent activity) as expandable inline output, similar to how tool calls work but for agent reasoning steps.

**Step 1: Add `AgentStepPart` type to `src/types/agent.ts`**

Add this interface after the `NotifierPart` interface (after line 53):

```typescript
export interface AgentStepPart {
  type: "agent_step";
  id: string;
  stepName: string;
  detail: string;
  status: "running" | "completed";
  startedAt: string;
  completedAt?: string;
  subSteps: string[];
}
```

Update the `ContentPart` union type:
```typescript
export type ContentPart = ThinkingPart | TextPart | ToolCallPart | NotifierPart | AgentStepPart;
```

Add to the `StreamEventType`:
```typescript
export type StreamEventType =
  | "thought"
  | "tool_call"
  | "tool_result"
  | "response"
  | "step"
  | "agent_step"
  | "done"
  | "error"
  | "notifier";
```

**Step 2: Create `src/components/agent/agent-steps-block.tsx`**

```tsx
"use client";

import React, { useState } from "react";
import { ChevronRight, GitBranch, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface AgentStepsBlockProps {
  id: string;
  stepName: string;
  detail: string;
  status: "running" | "completed";
  subSteps: string[];
  startedAt: string;
  completedAt?: string;
}

function AgentStepsBlockInner({
  stepName,
  detail,
  status,
  subSteps,
  startedAt,
  completedAt,
}: AgentStepsBlockProps) {
  const [expanded, setExpanded] = useState(status === "running");

  const duration = completedAt
    ? new Date(completedAt).getTime() - new Date(startedAt).getTime()
    : null;

  return (
    <div className="py-0.5 animate-fade-in-up">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors w-full text-left"
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 text-zinc-600 shrink-0 transition-transform duration-200",
            expanded && "rotate-90"
          )}
        />

        {status === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />
        ) : (
          <Check className="h-3 w-3 text-emerald-500/70" />
        )}

        <GitBranch className="h-3 w-3 shrink-0 text-zinc-500" />

        <span className="font-medium text-zinc-400">{stepName}</span>

        {detail && (
          <span className="min-w-0 flex-1 truncate text-zinc-600 text-[11px]">
            {detail}
          </span>
        )}

        {duration != null && (
          <span className="ml-auto text-[10px] font-mono text-zinc-600 tabular-nums">
            {duration < 1000
              ? `${duration}ms`
              : `${(duration / 1000).toFixed(1)}s`}
          </span>
        )}
      </button>

      {expanded && subSteps.length > 0 && (
        <div className="ml-4 mt-1 pl-3 border-l border-zinc-800 space-y-0.5 pb-1">
          {subSteps.map((step, i) => (
            <div
              key={i}
              className="flex items-center gap-1.5 text-[11px] text-zinc-600 font-mono"
            >
              <span className="h-1 w-1 rounded-full bg-zinc-700 shrink-0" />
              {step}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const AgentStepsBlock = React.memo(AgentStepsBlockInner);
```

**Step 3: Add store methods for agent steps**

In `src/stores/agent-store.ts`, add to the `AgentStore` interface (after `addNotifier`):

```typescript
addAgentStep: (messageId: string, stepName: string, detail: string) => void;
updateAgentStep: (messageId: string, stepId: string, subStep: string) => void;
completeAgentStep: (messageId: string, stepId: string) => void;
```

Add the implementations (after the `cancelEmptyThinking` method):

```typescript
addAgentStep: (messageId, stepName, detail) => {
  set((state) => ({
    messages: state.messages.map((m) => {
      if (m.id !== messageId) return m;

      const parts = [...m.contentParts];
      parts.push({
        type: "agent_step",
        id: nextPartId(),
        stepName,
        detail,
        status: "running",
        startedAt: new Date().toISOString(),
        subSteps: [],
      });

      return { ...m, contentParts: parts };
    }),
  }));
},

updateAgentStep: (messageId, stepId, subStep) => {
  set((state) => ({
    messages: state.messages.map((m) => {
      if (m.id !== messageId) return m;

      const parts = m.contentParts.map((part) => {
        if (part.type === "agent_step" && part.id === stepId) {
          return { ...part, subSteps: [...part.subSteps, subStep] };
        }
        return part;
      });

      return { ...m, contentParts: parts };
    }),
  }));
},

completeAgentStep: (messageId, stepId) => {
  set((state) => ({
    messages: state.messages.map((m) => {
      if (m.id !== messageId) return m;

      const parts = m.contentParts.map((part) => {
        if (part.type === "agent_step" && part.id === stepId) {
          return {
            ...part,
            status: "completed" as const,
            completedAt: new Date().toISOString(),
          };
        }
        return part;
      });

      return { ...m, contentParts: parts };
    }),
  }));
},
```

**Step 4: Handle agent_step events in `src/hooks/use-agent-chat.ts`**

Add a new case in the switch statement (after the `case "step":` block, around line 127):

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
    if (stepData.action === "update" && stepData.stepId && stepData.subStep) {
      store.updateAgentStep(assistantId, stepData.stepId, stepData.subStep);
    } else if (stepData.action === "complete" && stepData.stepId) {
      store.completeAgentStep(assistantId, stepData.stepId);
    } else {
      store.addAgentStep(assistantId, stepData.stepName, stepData.detail);
    }
  } catch {
    // ignore malformed agent_step events
  }
  break;
}
```

**Step 5: Render AgentStepsBlock in chat-interface.tsx**

Add import at top:
```tsx
import { AgentStepsBlock } from "./agent-steps-block";
```

Add case in `ContentPartRenderer` switch (before `default:`):
```tsx
    case "agent_step":
      return (
        <AgentStepsBlock
          id={part.id}
          stepName={part.stepName}
          detail={part.detail}
          status={part.status}
          subSteps={part.subSteps}
          startedAt={part.startedAt}
          completedAt={part.completedAt}
        />
      );
```

**Step 6: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 7: Commit**

```bash
git add src/types/agent.ts src/components/agent/agent-steps-block.tsx src/stores/agent-store.ts src/hooks/use-agent-chat.ts src/components/agent/chat-interface.tsx
git commit -m "feat: add AgentStepsBlock for task delegation visibility"
```

---

### Task 7: Emit Agent Steps from Normalizer for "step" Events

**Files:**
- Modify: `src/lib/agent/chat-stream-normalizer.ts` (enrich step events)
- Modify: `src/app/api/agent/chat/route.ts` (always emit steps)

**Goal:** Convert the existing "step" events into richer "agent_step" events so they appear in the new AgentStepsBlock instead of as notifier labels.

**Step 1: Enable update steps by default in route.ts**

In `src/app/api/agent/chat/route.ts`, change line 57:

```typescript
emitUpdateSteps: true,
```

(Remove the `debugStepsRequested` condition - always emit steps.)

**Step 2: Modify normalizer to emit `agent_step` instead of `step` for visible update nodes**

In `src/lib/agent/chat-stream-normalizer.ts`, in the `processUpdatesMode` function (around line 725), replace:

```typescript
if (emitUpdateSteps && isUserVisibleUpdateNode(nodeName)) {
  emitEvent("step", userVisibleUpdateLabel(nodeName), "updates", {
    node: nodeName,
    path,
  });
}
```

With:

```typescript
if (emitUpdateSteps && isUserVisibleUpdateNode(nodeName)) {
  const stepPayload = JSON.stringify({
    stepName: userVisibleUpdateLabel(nodeName),
    detail: `Node: ${nodeName}`,
    action: "start",
  });
  emitEvent("agent_step" as StreamEventType, stepPayload, "updates", {
    node: nodeName,
    path,
  });
}
```

**Step 3: Update the `StreamEventType` in the normalizer imports**

Ensure `agent_step` is already added in the types (done in Task 6).

**Step 4: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 5: Commit**

```bash
git add src/lib/agent/chat-stream-normalizer.ts src/app/api/agent/chat/route.ts
git commit -m "feat: emit agent_step events from normalizer for visible update nodes"
```

---

### Task 8: Reduce Message Spacing and Polish Chat Layout

**Files:**
- Modify: `src/components/agent/chat-interface.tsx` (layout spacing)
- Modify: `src/components/agent/message-bubble.tsx` (user message style)

**Goal:** Tighten vertical spacing between content parts. Make user messages consistent with the dark minimal theme. Reduce overall padding for a more dense, modern feel.

**Step 1: Update chat-interface.tsx message area spacing**

In `src/components/agent/chat-interface.tsx`, change the messages wrapper div from:
```tsx
<div className="py-4 space-y-1">
```
to:
```tsx
<div className="py-3 space-y-0.5">
```

**Step 2: Update the empty state to match new dark theme**

In `src/components/agent/chat-interface.tsx`, update the empty state (the Bot icon area):
```tsx
<div className="flex items-center justify-center h-full text-muted-foreground text-center py-20">
  <div className="space-y-2">
    <div className="flex items-center justify-center">
      <div className="h-10 w-10 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center">
        <Bot className="h-5 w-5 text-zinc-500" />
      </div>
    </div>
    <p className="text-sm font-medium text-zinc-400">OmniMind Agent</p>
    <p className="text-xs text-zinc-600">Ask me anything</p>
  </div>
</div>
```

**Step 3: Update message-bubble.tsx user message style**

Replace the content of `src/components/agent/message-bubble.tsx`:

```tsx
"use client";

import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  if (role !== "user") return null;

  return (
    <div className="flex justify-end py-2 animate-fade-in-up">
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm",
          "bg-zinc-800 border border-zinc-700/50",
          "text-zinc-200"
        )}
      >
        <div className="whitespace-pre-wrap break-words">{content}</div>
      </div>
    </div>
  );
}
```

**Step 4: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 5: Commit**

```bash
git add src/components/agent/chat-interface.tsx src/components/agent/message-bubble.tsx
git commit -m "feat: tighten layout spacing and polish user message style"
```

---

### Task 9: Clean Up Unused Notifier Filter System

**Files:**
- Modify: `src/stores/agent-store.ts` (remove notifier filter state if no UI uses it)

**Goal:** Since notifiers are now minimal inline labels, the notifier filter system (`notifierFilters`, `setNotifierFilter`) is unused UI state. Keep the store lean.

**Step 1: Verify no other component uses notifierFilters**

Run: `grep -r "notifierFilter" src/ --include="*.tsx" --include="*.ts"`
Expected: Only hits in `agent-store.ts`

**Step 2: Remove notifier filter state from store**

In `src/stores/agent-store.ts`:
- Remove the `NotifierFilters` interface
- Remove `notifierFilters` from `AgentStore` interface
- Remove `setNotifierFilter` from `AgentStore` interface
- Remove `notifierFilters` initial state
- Remove `setNotifierFilter` implementation
- Remove the `NotifierFilters` related import if any

**Step 3: Verify build compiles**

Run: `cd /home/levybonito/OmniMind && npx next build --no-lint 2>&1 | head -30`
Expected: No TypeScript errors

**Step 4: Commit**

```bash
git add src/stores/agent-store.ts
git commit -m "chore: remove unused notifier filter system from store"
```

---

### Task 10: Final Visual Verification

**Files:**
- No file changes - visual verification only

**Goal:** Run the dev server, open the chat, send a test message, and verify all visual changes are working as expected.

**Step 1: Start dev server**

Run: `cd /home/levybonito/OmniMind && npm run dev`

**Step 2: Open browser and verify**

Navigate to `http://localhost:3000/agent` and verify:

1. Thinking indicator is a compact inline "Thinking..." with dot animation (not full-width panel)
2. Tool calls show as compact inline rows with spinner/check (not colored full-width cards)
3. Response text flows naturally without glass borders
4. Notifiers are minimal dimmed text labels
5. User messages are clean dark bubbles
6. Messages are NOT splitting into multiple parts
7. All components use dark zinc colors (no bright colors)
8. Spacing is tight and modern

**Step 3: Test expanding/collapsing**

- Click on "Thought" label to expand reasoning content
- Click on tool call to expand input/output
- Verify expand/collapse animations work smoothly

**Step 4: Final commit if any adjustments needed**

```bash
git add -A
git commit -m "feat: complete chat UI overhaul - dark minimal design"
```
