# Chat Agent Fix + Architecture Map Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all chat UI rendering bugs (overlapping text, oversized components, edge-to-edge layout), simplify tool-call component visuals, remove success icons, and constrain message widths — all validated against real LLM tool-call data.

**Architecture:** Frontend-only changes to 6 React components + 1 CSS file + 1 Zustand store method. No backend changes needed — the streaming pipeline and normalizer are correct. The rendering bugs stem from: (1) `max-w-none` on ResponseBlock removing width constraints, (2) no max-width on assistant message container, (3) `animate-fade-in-up` on every single content part causing visual stacking during rapid streaming, (4) pre-output ThinkingBlock placeholder visible during fast tool-call sequences.

**Tech Stack:** React 19, Tailwind CSS v4, Zustand, Lucide React, react-markdown

---

## Architecture Mapping (Reference Document)

> This section documents the complete OmniMind agent architecture as requested. It is NOT an implementation task — it is reference material for the team.

### Model Initialization

| Setting | Value |
|---------|-------|
| Default Provider | `vertexai` |
| Default Model | `gemini-3-flash-preview` |
| Factory | `getModelForProvider()` in `src/lib/agent/providers.ts` |
| Supported | Vertex AI, Google GenAI, Anthropic, OpenAI, Ollama |
| Vertex Location | `global` (gemini-3*), `us-central1` (otherwise) |
| Reasoning | Vertex: `reasoningEffort: "high"`, Google: `thinkingLevel: "HIGH"`, Anthropic: `thinking: { type: "adaptive" }` |

### Agent Creation Flow
```
POST /api/agent/chat → route.ts
  └─ createOmniMindAgent(provider, model) → src/lib/agent/index.ts
       └─ getModelForProvider(provider, model) → BaseChatModel
       └─ createOmniMindDeepAgent({ model, systemPrompt }) → src/lib/agent/deep-agent-config.ts
            └─ deepagents.createDeepAgent({
                 model,
                 systemPrompt: "You are OmniMind...",
                 name: "omnimind-agent",
                 checkpointer: PostgresSaver,
                 tools: [searchWebTool],
                 backend: CompositeBackend(
                   FilesystemBackend({ rootDir: cwd }),
                   { "/memories/": StateBackend({}) }
                 )
               })
```

### Tools Available to Chat Agent

| Tool | Source | Description |
|------|--------|-------------|
| `search_web` | Custom (`src/lib/agent/tools/search-web.ts`) | SearXNG web search |
| `read_file` | deepagents built-in | Read file contents |
| `write_file` | deepagents built-in | Write file |
| `edit_file` | deepagents built-in | String replacement editing |
| `glob` | deepagents built-in | File pattern matching |
| `grep` | deepagents built-in | Content search |
| `ls` | deepagents built-in | Directory listing |
| `execute` | deepagents built-in | Shell execution |
| `TodoWrite` | deepagents built-in | Task management |

### Memory & State

| Layer | Mechanism | Persistence |
|-------|-----------|-------------|
| Graph Checkpointer | `PostgresSaver` (`@langchain/langgraph-checkpoint-postgres`) | PostgreSQL (durable) |
| Thread Isolation | `configurable: { thread_id: conversationId }` | Per-conversation |
| File Backend | `FilesystemBackend({ rootDir: cwd })` | Filesystem |
| Memory Backend | `StateBackend({ state: {}, store: undefined })` | In-memory (ephemeral) |

### Agent Decision Flow
```
User message → DeepAgent.stream()
  └─ LLM decides: respond directly OR call tool(s)
       └─ Tool results fed back to LLM (ReAct loop)
       └─ LLM decides again (loop until final response)
  └─ Tokens stream via normalizer → SSE → client
```

### Streaming Pipeline
```
agent.stream(HumanMessage, { streamMode: ["messages", "updates"] })
  → for await (item) → normalizer.process(item)
    → emit(type, data, mode, meta)
      → SSE "data: {JSON}\n\n"
        → fetch().body.getReader()
          → JSON.parse → switch(event.type) → Zustand store
            → React re-render → ContentPartRenderer
```

### Event Types

| Event | Source | Frontend Handler |
|-------|--------|-----------------|
| `thought` | AI reasoning/thinking blocks | `store.appendThought()` |
| `response` | AI visible text | `store.appendToAssistant()` |
| `tool_call` | AI tool invocations | `store.addToolCall()` |
| `tool_result` | Tool completion data | `store.updateToolResult()` |
| `agent_step` | Graph node transitions | `store.addAgentStep()` |
| `step` | Custom mode events | `store.addNotifier()` |
| `notifier` | Structured notifications | `store.addNotifier()` |
| `done` | Stream completion | (no-op) |
| `error` | Error messages | `store.appendToAssistant()` |

### Security Concerns (Documented)

1. **CRITICAL:** `run_command` tool in swarm coder executes arbitrary shell commands without sandboxing
2. **CRITICAL:** Hardcoded service account path in `providers.ts`
3. **MODERATE:** No authentication on `/api/agent/chat` endpoint
4. **MODERATE:** In-memory swarm registry not persisted across restarts
5. **MINOR:** `StateBackend({ store: undefined })` — no persistent memory store configured

---

## Bug Root Cause Analysis

### Bug 1: "Letters on top of letters" (overlapping text)

**Root Cause:** `animate-fade-in-up` (300ms fade+translate animation) applied to EVERY content part (`<div className="py-0.5 animate-fade-in-up">` in ToolCallBlock, ResponseBlock, ThinkingBlock, AgentStepsBlock). During rapid streaming, dozens of parts animate simultaneously, each shifting 12px upward — creating visual overlap as elements settle.

**Fix:** Remove `animate-fade-in-up` from all content parts. These are inline timeline elements, not cards — they shouldn't animate individually.

### Bug 2: "Components are too big / cover the entire chat"

**Root Cause:** Assistant messages have NO max-width constraint. The `<ScrollArea className="flex-1 px-4">` has only 16px padding. `ResponseBlock` uses `max-w-none` which explicitly removes prose's default `65ch` max-width. Tool call blocks use `w-full`.

**Fix:** Wrap assistant message content in a container with `max-w-3xl` (48rem = 768px) and remove `max-w-none` from ResponseBlock.

### Bug 3: "Success check icons on tool components"

**Root Cause:** `StatusDot` in `tool-call-block.tsx` renders `<Check className="h-3 w-3 text-emerald-500/70" />` when status is `"success"`. Same pattern in `AgentStepsBlock`.

**Fix:** Replace success icon with a subtle dot indicator (same as pending state but in a muted color).

### Bug 4: "Components are too colorful / bright"

**Root Cause:** The components are actually already quite subdued (zinc grays). However, the `accentColor` field in `tool-icon-map.ts` defines colors per tool type that are NOT currently used — this is a non-issue. The main visual noise comes from: (1) emerald success checks, (2) the animated ping dot on thinking, (3) too much vertical spacing.

**Fix:** Tighten spacing, remove success checks, simplify thinking indicator.

### Bug 5: Pre-output rendering issue

**Root Cause:** `startAssistantMessage()` immediately creates a `ThinkingPart` with `content: ""` and `isStreaming: true`. This renders the animated "Thinking" indicator. If the first SSE event is a `tool_call`, `cancelEmptyThinking()` closes it — but there's a brief visible flash. If the first event is `thought` data, it works correctly.

**Fix:** Don't render the ThinkingBlock at all when it has empty content and streaming just started. The `cancelEmptyThinking` mechanism is correct — the visual flash is acceptable and brief enough. No code change needed here.

---

## Implementation Tasks

### Task 1: Add test for chat message width constraints

**Files:**
- Create: `src/components/agent/__tests__/chat-interface.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

// Mock the useAgentChat hook
vi.mock("@/hooks/use-agent-chat", () => ({
  useAgentChat: () => ({
    messages: [
      {
        id: "msg-1",
        role: "assistant",
        content: "Hello world",
        thoughts: "",
        toolCalls: [],
        isStreaming: false,
        contentParts: [
          { type: "text", id: "part-1", content: "Hello world" },
        ],
      },
    ],
    isLoading: false,
    provider: "vertexai",
    model: "gemini-3-flash-preview",
    sendMessage: vi.fn(),
    setProvider: vi.fn(),
    setModel: vi.fn(),
    setNoteContext: vi.fn(),
    clearMessages: vi.fn(),
  }),
}));

describe("ChatInterface", () => {
  it("assistant messages have max-width constraint", async () => {
    const { ChatInterface } = await import("../chat-interface");
    const { container } = render(<ChatInterface />);

    // Find the assistant message wrapper
    const assistantWrapper = container.querySelector("[data-testid='assistant-message']");
    expect(assistantWrapper).toBeTruthy();
    expect(assistantWrapper?.className).toContain("max-w-3xl");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/chat-interface.test.tsx --reporter=verbose`
Expected: FAIL — no `data-testid='assistant-message'` attribute exists yet

**Step 3: Write minimal implementation**

Edit `src/components/agent/chat-interface.tsx` — wrap assistant message content parts in a constrained container:

In the messages map, change the assistant message rendering from:
```tsx
) : msg.contentParts.length > 0 ? (
  <>
    {msg.contentParts.map((part, idx) => {
```
to:
```tsx
) : msg.contentParts.length > 0 ? (
  <div data-testid="assistant-message" className="max-w-3xl">
    {msg.contentParts.map((part, idx) => {
```

And close the `<div>` where the `<>` was closing:
```tsx
    // Change </> to </div>
```

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/chat-interface.test.tsx --reporter=verbose`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/__tests__/chat-interface.test.tsx src/components/agent/chat-interface.tsx && git commit -m "feat(chat): add max-width constraint to assistant messages"
```

---

### Task 2: Remove animations from content parts to fix overlapping text

**Files:**
- Modify: `src/components/agent/tool-call-block.tsx:92`
- Modify: `src/components/agent/thinking-block.tsx:61,84`
- Modify: `src/components/agent/response-block.tsx:18`
- Modify: `src/components/agent/agent-steps-block.tsx:32`

**Step 1: Write the failing test**

Add to `src/components/agent/__tests__/chat-interface.test.tsx`:

```tsx
it("content parts do not have fade-in-up animation class", async () => {
  const { ChatInterface } = await import("../chat-interface");
  const { container } = render(<ChatInterface />);

  // No element within the message area should have animate-fade-in-up
  const animatedElements = container.querySelectorAll(".animate-fade-in-up");
  expect(animatedElements.length).toBe(0);
});
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/chat-interface.test.tsx --reporter=verbose`
Expected: FAIL — ResponseBlock has `animate-fade-in-up`

**Step 3: Remove animations from all content part components**

In `src/components/agent/tool-call-block.tsx` line 92, change:
```tsx
<div className="py-0.5 animate-fade-in-up">
```
to:
```tsx
<div className="py-0.5">
```

In `src/components/agent/thinking-block.tsx` line 61, change:
```tsx
<div className="flex items-center gap-2 py-1.5 animate-fade-in-up">
```
to:
```tsx
<div className="flex items-center gap-2 py-1.5">
```

In `src/components/agent/thinking-block.tsx` line 84, change:
```tsx
<div className="py-1 animate-fade-in-up">
```
to:
```tsx
<div className="py-1">
```

In `src/components/agent/response-block.tsx` line 18, change:
```tsx
<div className="py-1 animate-fade-in-up">
```
to:
```tsx
<div className="py-1">
```

In `src/components/agent/agent-steps-block.tsx` line 32, change:
```tsx
<div className="py-0.5 animate-fade-in-up">
```
to:
```tsx
<div className="py-0.5">
```

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/chat-interface.test.tsx --reporter=verbose`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/tool-call-block.tsx src/components/agent/thinking-block.tsx src/components/agent/response-block.tsx src/components/agent/agent-steps-block.tsx && git commit -m "fix(chat): remove fade-in-up animations from content parts to fix overlapping text"
```

---

### Task 3: Remove max-w-none from ResponseBlock

**Files:**
- Modify: `src/components/agent/response-block.tsx:21`

**Step 1: Write the failing test**

Add to `src/components/agent/__tests__/chat-interface.test.tsx`:

```tsx
it("response block does not use max-w-none", async () => {
  // Read the source file and verify max-w-none is not present
  const { ResponseBlock } = await import("../response-block");
  const { container } = render(
    <ResponseBlock content="Hello" isStreaming={false} />
  );

  const proseEl = container.querySelector(".prose");
  expect(proseEl).toBeTruthy();
  expect(proseEl?.className).not.toContain("max-w-none");
});
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/chat-interface.test.tsx --reporter=verbose`
Expected: FAIL — prose div contains `max-w-none`

**Step 3: Remove max-w-none**

In `src/components/agent/response-block.tsx` line 21, change:
```tsx
"prose prose-sm dark:prose-invert max-w-none",
```
to:
```tsx
"prose prose-sm dark:prose-invert",
```

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/chat-interface.test.tsx --reporter=verbose`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/response-block.tsx && git commit -m "fix(chat): remove max-w-none from ResponseBlock to constrain text width"
```

---

### Task 4: Remove success check icons from ToolCallBlock and AgentStepsBlock

**Files:**
- Modify: `src/components/agent/tool-call-block.tsx:60-71`
- Modify: `src/components/agent/agent-steps-block.tsx:44-48`

**Step 1: Write the failing test**

Create `src/components/agent/__tests__/tool-call-block.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ToolCallBlock } from "../tool-call-block";

describe("ToolCallBlock", () => {
  it("does not render Check icon for success status", () => {
    const { container } = render(
      <ToolCallBlock
        id="tc-1"
        toolName="read_file"
        toolInput={{ path: "/test.ts" }}
        toolOutput="file contents"
        status="success"
        startedAt={new Date().toISOString()}
        completedAt={new Date().toISOString()}
      />
    );

    // Should NOT have a Check (checkmark) SVG — should use a dot instead
    const checkSvgs = container.querySelectorAll("svg");
    const checkPaths = Array.from(checkSvgs).filter(
      (svg) => svg.querySelector("polyline[points='20 6 9 17 4 12']") !== null
    );
    expect(checkPaths.length).toBe(0);
  });

  it("renders a subtle dot for success status", () => {
    const { container } = render(
      <ToolCallBlock
        id="tc-1"
        toolName="read_file"
        toolInput={{ path: "/test.ts" }}
        toolOutput="file contents"
        status="success"
        startedAt={new Date().toISOString()}
        completedAt={new Date().toISOString()}
      />
    );

    // Should have a dot span element for success
    const dots = container.querySelectorAll("span.rounded-full");
    expect(dots.length).toBeGreaterThan(0);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/tool-call-block.test.tsx --reporter=verbose`
Expected: FAIL — success still renders Check icon

**Step 3: Replace success Check icon with subtle dot**

In `src/components/agent/tool-call-block.tsx`, replace the `StatusDot` function (lines 60-71):

```tsx
function StatusDot({ status }: { status: ToolCallBlockProps["status"] }) {
  switch (status) {
    case "pending":
      return <span className="h-1.5 w-1.5 rounded-full bg-zinc-600" />;
    case "running":
      return <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />;
    case "success":
      return <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />;
    case "error":
      return <X className="h-3 w-3 text-red-400/70" />;
  }
}
```

Remove `Check` from the import line (line 4):
```tsx
import { ChevronRight, Loader2, X } from "lucide-react";
```

In `src/components/agent/agent-steps-block.tsx`, replace the status icon rendering (lines 44-48):

```tsx
{status === "running" ? (
  <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />
) : (
  <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
)}
```

Remove `Check` from the import line (line 4):
```tsx
import { ChevronRight, GitBranch, Loader2 } from "lucide-react";
```

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/tool-call-block.test.tsx --reporter=verbose`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/tool-call-block.tsx src/components/agent/agent-steps-block.tsx src/components/agent/__tests__/tool-call-block.test.tsx && git commit -m "fix(chat): replace success check icons with subtle dots in tool and step blocks"
```

---

### Task 5: Simplify ThinkingBlock — remove animated ping, tighten spacing

**Files:**
- Modify: `src/components/agent/thinking-block.tsx:59-79`

**Step 1: Write the failing test**

Create `src/components/agent/__tests__/thinking-block.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ThinkingBlock } from "../thinking-block";

describe("ThinkingBlock", () => {
  it("does not render animate-ping elements when streaming", () => {
    const { container } = render(
      <ThinkingBlock
        id="t-1"
        content=""
        isStreaming={true}
      />
    );

    const pingElements = container.querySelectorAll(".animate-ping");
    expect(pingElements.length).toBe(0);
  });

  it("renders a simple pulsing dot instead of ping animation", () => {
    const { container } = render(
      <ThinkingBlock
        id="t-1"
        content=""
        isStreaming={true}
      />
    );

    const pulseDot = container.querySelector(".animate-pulse");
    expect(pulseDot).toBeTruthy();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/thinking-block.test.tsx --reporter=verbose`
Expected: FAIL — still has `animate-ping`

**Step 3: Simplify the streaming indicator**

In `src/components/agent/thinking-block.tsx`, replace the streaming state block (lines 59-79) with:

```tsx
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

Key changes:
- Removed the double-span ping animation (`animate-ping` + inner dot) — replaced with single dot + `animate-pulse`
- Reduced `py-1.5` to `py-1`
- Only show token count when > 0 (hides the `~0t` on initial empty state)

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/thinking-block.test.tsx --reporter=verbose`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/thinking-block.tsx src/components/agent/__tests__/thinking-block.test.tsx && git commit -m "fix(chat): simplify ThinkingBlock indicator — remove ping animation, tighten spacing"
```

---

### Task 6: Remove w-full from ToolCallBlock and AgentStepsBlock buttons

**Files:**
- Modify: `src/components/agent/tool-call-block.tsx:95`
- Modify: `src/components/agent/agent-steps-block.tsx:35`

**Step 1: Write the failing test**

Add to `src/components/agent/__tests__/tool-call-block.test.tsx`:

```tsx
it("tool call button does not use w-full", () => {
  const { container } = render(
    <ToolCallBlock
      id="tc-1"
      toolName="read_file"
      toolInput={{ path: "/test.ts" }}
      toolOutput={null}
      status="running"
      startedAt={new Date().toISOString()}
    />
  );

  const button = container.querySelector("button");
  expect(button).toBeTruthy();
  expect(button?.className).not.toContain("w-full");
});
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/tool-call-block.test.tsx --reporter=verbose`
Expected: FAIL — button has `w-full`

**Step 3: Remove w-full from buttons**

In `src/components/agent/tool-call-block.tsx` line 95, change:
```tsx
className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors w-full text-left"
```
to:
```tsx
className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors text-left"
```

In `src/components/agent/agent-steps-block.tsx` line 35, change:
```tsx
className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors w-full text-left"
```
to:
```tsx
className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors text-left"
```

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/tool-call-block.test.tsx --reporter=verbose`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/tool-call-block.tsx src/components/agent/agent-steps-block.tsx && git commit -m "fix(chat): remove w-full from tool call and agent step buttons"
```

---

### Task 7: Remove unused accentColor and CheckIcon exports from tool-icon-map

**Files:**
- Modify: `src/components/agent/tool-icon-map.ts`

**Step 1: Write the failing test**

Create `src/components/agent/__tests__/tool-icon-map.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { getToolConfig } from "../tool-icon-map";

describe("getToolConfig", () => {
  it("returns config without accentColor field", () => {
    const config = getToolConfig("read_file");
    expect(config).toHaveProperty("icon");
    expect(config).toHaveProperty("label");
    expect(config).not.toHaveProperty("accentColor");
  });

  it("returns correct label for known tools", () => {
    expect(getToolConfig("read_file").label).toBe("Read File");
    expect(getToolConfig("write_file").label).toBe("Write File");
    expect(getToolConfig("search_web").label).toBe("Web Search");
    expect(getToolConfig("execute").label).toBe("Execute Code");
  });

  it("prettifies unknown tool names", () => {
    expect(getToolConfig("my_custom_tool").label).toBe("My Custom Tool");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/tool-icon-map.test.ts --reporter=verbose`
Expected: FAIL — config still has `accentColor`

**Step 3: Remove accentColor from ToolVisualConfig interface and all entries**

Replace the entire `src/components/agent/tool-icon-map.ts` file with:

```ts
import type { LucideIcon } from "lucide-react";
import {
  Globe,
  Terminal,
  FileText,
  FilePen,
  FolderTree,
  Code,
  Search,
  FileSearch,
  FolderOpen,
  BookOpen,
  StickyNote,
  Link2,
  ListChecks,
  ClipboardList,
  Network,
  FileEdit,
  Settings,
  Loader2,
  AlertCircle,
} from "lucide-react";

export interface ToolVisualConfig {
  icon: LucideIcon;
  label: string;
}

const MAP: Record<string, ToolVisualConfig> = {
  // Web / search
  web_search: { icon: Globe, label: "Web Search" },
  search_web: { icon: Globe, label: "Web Search" },

  // Terminal / shell
  bash: { icon: Terminal, label: "Terminal" },
  run_command: { icon: Terminal, label: "Run Command" },
  execute: { icon: Code, label: "Execute Code" },

  // File operations
  read_file: { icon: FileText, label: "Read File" },
  write_file: { icon: FilePen, label: "Write File" },
  edit_file: { icon: FileEdit, label: "Edit File" },
  list_files: { icon: FolderTree, label: "List Files" },

  // Search / grep
  search_files: { icon: FileSearch, label: "Search Files" },
  search_content: { icon: Search, label: "Search Content" },
  glob: { icon: FileSearch, label: "Glob Search" },
  grep: { icon: Search, label: "Grep" },
  ls: { icon: FolderOpen, label: "List Directory" },

  // Note operations
  read_note: { icon: BookOpen, label: "Read Note" },
  search_notes: { icon: Search, label: "Search Notes" },
  get_notes_context: { icon: StickyNote, label: "Notes Context" },
  list_notes: { icon: ListChecks, label: "List Notes" },
  link_notes: { icon: Link2, label: "Link Notes" },

  // Task / report
  write_todos: { icon: ClipboardList, label: "Write Todos" },
  write_report: { icon: FilePen, label: "Write Report" },
  task: { icon: Network, label: "Task" },
};

const DEFAULT_CONFIG: ToolVisualConfig = {
  icon: Settings,
  label: "Tool",
};

function prettifyToolName(toolName: string): string {
  const raw = String(toolName || "").trim();
  if (!raw || raw.toLowerCase() === "unknown") return "Tool";

  return raw
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getToolConfig(toolName: string): ToolVisualConfig {
  const config = MAP[toolName];
  if (config) return config;
  return { ...DEFAULT_CONFIG, label: prettifyToolName(toolName) };
}

/** Status-related icons re-exported for convenience */
export { Loader2 as SpinnerIcon, AlertCircle as ErrorIcon };
```

Key changes:
- Removed `accentColor` from `ToolVisualConfig` interface
- Removed `accentColor` from every MAP entry
- Removed `Check as CheckIcon` export (no longer used anywhere)

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/tool-icon-map.test.ts --reporter=verbose`
Expected: PASS

**Step 5: Verify no broken imports**

Run: `cd /home/levybonito/OmniMind && npx tsc --noEmit 2>&1 | head -30`
Expected: No errors related to `accentColor` or `CheckIcon`

**Step 6: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/tool-icon-map.ts src/components/agent/__tests__/tool-icon-map.test.ts && git commit -m "refactor(chat): remove unused accentColor and CheckIcon from tool-icon-map"
```

---

### Task 8: Tighten vertical spacing in message list

**Files:**
- Modify: `src/components/agent/chat-interface.tsx:138`

**Step 1: Change message list spacing**

In `src/components/agent/chat-interface.tsx` line 138, change:
```tsx
<div className="py-3 space-y-0.5">
```
to:
```tsx
<div className="py-2 space-y-0">
```

This removes the 2px gap between content parts (they already have their own `py-0.5` or `py-1` padding).

**Step 2: Also tighten the notifier part spacing**

In `src/components/agent/chat-interface.tsx`, the notifier part rendering (around line 58-63) — change:
```tsx
<div className="py-0.5 animate-fade-in-up">
```
to:
```tsx
<div className="py-0.5">
```

(This also removes the animation from the inline notifier element.)

**Step 3: Run the full test suite**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/ --reporter=verbose`
Expected: All tests PASS

**Step 4: Commit**

```bash
cd /home/levybonito/OmniMind && git add src/components/agent/chat-interface.tsx && git commit -m "fix(chat): tighten vertical spacing in message list"
```

---

### Task 9: Run full type check and all tests

**Files:** None (verification only)

**Step 1: Run TypeScript type check**

Run: `cd /home/levybonito/OmniMind && npx tsc --noEmit`
Expected: No errors

**Step 2: Run all component tests**

Run: `cd /home/levybonito/OmniMind && npx vitest run src/components/agent/__tests__/ --reporter=verbose`
Expected: All tests PASS

**Step 3: Run all existing tests**

Run: `cd /home/levybonito/OmniMind && npx vitest run --reporter=verbose`
Expected: All tests PASS (existing normalizer tests, store tests, route tests should not be affected)

**Step 4: Visual verification**

Start the dev server and test in browser:
Run: `cd /home/levybonito/OmniMind && npm run dev`
- Navigate to `http://localhost:3000/agent`
- Send a message to the agent
- Verify:
  - [ ] Messages don't extend edge-to-edge (max-width ~768px)
  - [ ] No overlapping text during streaming
  - [ ] No success check icons on completed tool calls
  - [ ] No animated ping on thinking indicator (just a subtle pulse dot)
  - [ ] Tool call blocks don't span full width
  - [ ] Response text has natural prose width (not max-w-none)
  - [ ] Vertical spacing is tight but readable

**Step 5: Final commit (if any adjustments needed)**

```bash
cd /home/levybonito/OmniMind && git add -A && git commit -m "fix(chat): final adjustments after visual verification"
```

---

## Summary of All Changes

| File | Change | Fixes |
|------|--------|-------|
| `chat-interface.tsx` | Add `max-w-3xl` wrapper on assistant messages, remove animation from notifier, tighten spacing | Messages too wide, edge-to-edge layout |
| `response-block.tsx` | Remove `max-w-none`, remove `animate-fade-in-up` | Text spanning full width, overlapping |
| `tool-call-block.tsx` | Replace Check icon with dot, remove `w-full`, remove animation | Success icon, buttons too wide, overlapping |
| `thinking-block.tsx` | Replace ping animation with pulse dot, remove animation, tighten spacing | Bright/flashy indicator, overlapping |
| `agent-steps-block.tsx` | Replace Check icon with dot, remove `w-full`, remove animation | Success icon, buttons too wide, overlapping |
| `tool-icon-map.ts` | Remove `accentColor` field, remove `CheckIcon` export | Dead code cleanup |

**Total files modified:** 6 source files + 3 new test files
**No backend changes.**
**No streaming pipeline changes.**
**No Zustand store logic changes.**
