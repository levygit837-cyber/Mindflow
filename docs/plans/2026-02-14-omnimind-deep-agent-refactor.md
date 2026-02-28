# OmniMind Deep Agent Refactor - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform OmniMind into a pure DeepAgent-powered AI assistant with proper streaming (thinking/reasoning/tools/output), PostgreSQL persistence, Vertex AI (gemini-3-flash-preview), clean architecture, and zero notes/Express legacy.

**Architecture:** Single Next.js 16 app (no Express backend). DeepAgent with CompositeBackend routing memories to PostgresStore, workspace to StateBackend. SSE streaming pipeline: DeepAgent -> chat-stream-normalizer -> SSE -> React components (ThinkingBlock, ToolCallBlock, ResponseBlock). PostgresSaver for checkpointing, PostgresStore for long-term memory.

**Tech Stack:** Next.js 16, deepagentsjs ^1.7.0, @langchain/langgraph ^1.1.3, @langchain/langgraph-checkpoint-postgres, @langchain/google-vertexai ^2.1.15, PostgreSQL 16, Zustand, Tailwind CSS, TypeScript 5.9

---

## Phase 1: Cleanup - Remove Notes & Express Backend

### Task 1: Remove Express Backend Entirely

**Files:**
- Delete: `backend/server.ts`
- Delete: `backend/api/routes/agentRoutes.ts`
- Delete: `backend/agents/graphs/exampleAgentGraph.ts`
- Delete: `backend/agents/nodes/simpleChatNode.ts`
- Delete: `backend/config/config.ts`
- Delete: `backend/config/index.ts`
- Delete: `backend/utils/logger.ts`
- Delete: `backend/package.json`
- Delete: `backend/package-lock.json`
- Modify: `package.json` (remove backend scripts)
- Modify: `start.js` (remove backend startup)
- Modify: `start.sh` (remove backend startup)

**Step 1: Delete backend server files**

```bash
rm -rf backend/server.ts backend/api/ backend/agents/ backend/config/ backend/utils/
rm backend/package.json backend/package-lock.json
```

**Step 2: Clean backend directory - keep only lib/swarm (will be moved later)**

Verify swarm files exist that we want to keep:
```bash
ls backend/lib/swarm/
```

**Step 3: Update root package.json - remove Express scripts**

Remove `"dev:backend"` script and update `"dev"` to only start frontend:
```json
{
  "scripts": {
    "dev": "cd frontend && next dev --turbopack",
    "dev:frontend": "cd frontend && next dev --turbopack",
    "build": "cd frontend && next build",
    "start": "cd frontend && next start",
    "lint": "cd frontend && next lint",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

**Step 4: Simplify start.js to only launch Next.js**

```javascript
const { spawn } = require('child_process');
const path = require('path');

const frontend = spawn('npx', ['next', 'dev', '--turbopack'], {
  cwd: path.join(__dirname, 'frontend'),
  stdio: 'inherit',
  shell: true,
});

frontend.on('close', (code) => {
  process.exit(code);
});
```

**Step 5: Commit**
```bash
git add -A && git commit -m "chore: remove Express backend - consolidate to Next.js API routes"
```

---

### Task 2: Remove All Notes-Related Code

**Files:**
- Delete: `frontend/app/notes/` (entire directory)
- Delete: `frontend/app/api/notes/` (entire directory)
- Delete: `frontend/app/graph/page.tsx`
- Delete: `frontend/app/api/graph/route.ts`
- Delete: `frontend/components/notes/` (entire directory)
- Delete: `frontend/components/graph/` (entire directory)
- Delete: `frontend/hooks/use-notes.ts`
- Delete: `frontend/hooks/use-graph-data.ts`
- Delete: `frontend/stores/graph-store.ts`
- Delete: `frontend/types/note.ts`
- Delete: `frontend/types/graph.ts`
- Delete: `frontend/lib/notes/` (entire directory)
- Delete: `frontend/lib/graph/` (entire directory)
- Delete: `frontend/lib/db/` (entire directory - SQLite)
- Delete: `frontend/lib/agent/tools/note-tools.ts`
- Delete: `frontend/lib/polymarket/` (entire directory)
- Delete: `backend/lib/notes/` (entire directory)
- Delete: `backend/lib/db/` (entire directory)
- Delete: `backend/lib/agent/tools/note-tools.ts`
- Delete: `backend/lib/polymarket/` (entire directory)
- Delete: `backend/data/` (entire directory - SQLite data)
- Delete: `drizzle.config.ts`
- Delete: `frontend/examples/` (entire directory)
- Modify: `frontend/app/page.tsx` (remove notes references)
- Modify: `frontend/app/layout.tsx` (no changes needed)
- Modify: `frontend/components/layout/sidebar.tsx` (remove notes/graph links)
- Modify: `package.json` (remove drizzle, blocknote, better-sqlite3, three.js deps)

**Step 1: Delete all notes directories and files**

```bash
# Frontend notes
rm -rf frontend/app/notes/ frontend/app/api/notes/ frontend/app/api/graph/
rm -rf frontend/app/graph/
rm -rf frontend/components/notes/ frontend/components/graph/
rm -rf frontend/hooks/use-notes.ts frontend/hooks/use-graph-data.ts
rm -rf frontend/stores/graph-store.ts
rm -rf frontend/types/note.ts frontend/types/graph.ts
rm -rf frontend/lib/notes/ frontend/lib/graph/ frontend/lib/db/
rm -rf frontend/lib/agent/tools/note-tools.ts
rm -rf frontend/lib/polymarket/
rm -rf frontend/examples/

# Backend notes
rm -rf backend/lib/notes/ backend/lib/db/
rm -rf backend/lib/agent/tools/note-tools.ts
rm -rf backend/lib/polymarket/
rm -rf backend/data/

# Root
rm -f drizzle.config.ts
```

**Step 2: Remove unused dependencies from root package.json**

Remove these from `dependencies`:
- `@blocknote/core`, `@blocknote/mantine`, `@blocknote/react`, `@blocknote/shadcn`
- `@mantine/core`
- `@react-three/drei`, `@react-three/fiber`, `three`
- `better-sqlite3`
- `drizzle-orm`

Remove from `devDependencies`:
- `@types/better-sqlite3`
- `@types/three`
- `drizzle-kit`

Remove from `pnpm.onlyBuiltDependencies`:
- `better-sqlite3`

Remove scripts: `db:generate`, `db:migrate`

**Step 3: Update frontend/app/page.tsx - Agent-only dashboard**

```tsx
"use client";

import Link from "next/link";
import { Bot, Settings } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">OmniMind</h2>
        <p className="text-muted-foreground mt-1">
          Your personal Deep Agent powered by Vertex AI
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link href="/agent">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10 text-green-500">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Deep Agent</CardTitle>
                  <CardDescription>Chat with OmniMind</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/settings">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                  <Settings className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Settings</CardTitle>
                  <CardDescription>Configure provider & model</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}
```

**Step 4: Update sidebar to remove notes/graph links**

Update `frontend/components/layout/sidebar.tsx` - remove `Notes`, `Graph` nav items. Keep only `Home`, `Agent`, `Settings`.

**Step 5: Run build to verify no broken imports**

```bash
cd frontend && npx next build 2>&1 | head -50
```
Expected: Compilation should succeed (or only have minor import issues to fix).

**Step 6: Commit**
```bash
git add -A && git commit -m "chore: remove all notes, graph, SQLite, BlockNote, Three.js code"
```

---

## Phase 2: Reorganize Project Structure (Clean Architecture)

### Task 3: Move Backend Lib into Frontend and Establish Clean Hierarchy

**Target structure:**
```
frontend/
  app/
    (dashboard)/
      page.tsx                    # Home/dashboard
    agent/
      page.tsx                    # Agent chat page
    settings/
      page.tsx                    # Settings page
    api/
      agent/
        chat/
          route.ts                # SSE streaming endpoint
        conversations/
          route.ts
          [id]/
            messages/
              route.ts
      settings/
        route.ts
    layout.tsx
    globals.css
  components/
    agent/
      chat-interface.tsx
      chat-input.tsx
      message-bubble.tsx
      thinking-block.tsx
      tool-call-block.tsx
      tool-icon-map.ts
      provider-selector.tsx
      activity-stream.tsx
      conversation-sidebar.tsx
    layout/
      app-shell.tsx
      header.tsx
      sidebar.tsx
    ui/
      (shadcn components)
  hooks/
    use-agent-chat.ts
    use-swarm-stream.ts
  stores/
    agent-store.ts
    swarm-store.ts
  lib/
    agent/
      index.ts                    # createOmniMindAgent factory
      providers.ts                # LLM provider factory (Vertex AI focus)
      deep-agent-config.ts        # DeepAgent + CompositeBackend config
      stream.ts                   # SSE stream utilities
      chat-stream-normalizer.ts   # Stream event normalizer
    db/
      postgres.ts                 # PostgreSQL connection pool + setup
    swarm/                        # (existing swarm code, cleaned up)
      graph.ts
      state.ts
      coder.ts
      orchestrator.ts
      reviewer.ts
      live-analyst.ts
      notifier.ts
      sandbox-renderer.ts
      registry.ts
      prompts/
      tools/
      templates/
      utils/
  types/
    agent.ts
    swarm.ts
    settings.ts
    index.ts
  utils/
    logger.ts
  config/
    index.ts
```

**Step 1: Move backend/lib/swarm files to frontend/lib/swarm**

The frontend already has copies. Verify they are identical or use the latest version:
```bash
diff -r backend/lib/swarm frontend/lib/swarm
```

If identical, just delete backend/lib/swarm. If different, keep frontend versions (they're more recent per modification dates).

**Step 2: Move remaining backend files**

```bash
# Move agent lib files (backend versions) if they differ
# backend/lib/agent/* -> frontend/lib/agent/* (use frontend versions, they're newer)
rm -rf backend/lib/
```

**Step 3: Delete entire backend directory**

```bash
rm -rf backend/
```

**Step 4: Remove backend/lib/utils.ts references**

Verify frontend/lib/utils.ts exists and is the canonical version.

**Step 5: Verify the project builds**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

**Step 6: Commit**
```bash
git add -A && git commit -m "refactor: consolidate to single Next.js project, remove backend/"
```

---

## Phase 3: PostgreSQL Setup & LangGraph Store

### Task 4: Install PostgreSQL Dependencies and Configure Connection

**Files:**
- Modify: `package.json` (add postgres dependencies)
- Create: `frontend/lib/db/postgres.ts`
- Modify: `.env.local` (add DATABASE_URL)

**Step 1: Install PostgreSQL packages**

```bash
cd /home/levybonito/OmniMind && pnpm add @langchain/langgraph-checkpoint-postgres pg
cd /home/levybonito/OmniMind && pnpm add -D @types/pg
```

**Step 2: Create .env.local entry**

Add to `.env.local`:
```
DATABASE_URL=postgresql://omnimind:omnimind@localhost:5432/omnimind
```

**Step 3: Create PostgreSQL connection module**

Create `frontend/lib/db/postgres.ts`:
```typescript
import pg from "pg";
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";

const { Pool } = pg;

let pool: pg.Pool | null = null;
let checkpointer: PostgresSaver | null = null;
let initialized = false;

function getPool(): pg.Pool {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) {
      throw new Error("DATABASE_URL environment variable is required");
    }
    pool = new Pool({
      connectionString,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
  }
  return pool;
}

export function getCheckpointer(): PostgresSaver {
  if (!checkpointer) {
    checkpointer = new PostgresSaver(getPool());
  }
  return checkpointer;
}

export async function ensureDbInitialized(): Promise<void> {
  if (initialized) return;
  const cp = getCheckpointer();
  await cp.setup();
  initialized = true;
}

export { getPool };
```

**Step 4: Create PostgreSQL database locally**

```bash
sudo -u postgres psql -c "CREATE USER omnimind WITH PASSWORD 'omnimind';"
sudo -u postgres psql -c "CREATE DATABASE omnimind OWNER omnimind;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE omnimind TO omnimind;"
```

**Step 5: Write a basic test to verify connection**

```bash
cd frontend && npx tsx -e "
  const pg = require('pg');
  const pool = new pg.Pool({ connectionString: 'postgresql://omnimind:omnimind@localhost:5432/omnimind' });
  pool.query('SELECT NOW()').then(r => { console.log('Connected:', r.rows[0]); pool.end(); });
"
```

**Step 6: Commit**
```bash
git add -A && git commit -m "feat: add PostgreSQL connection pool and LangGraph checkpointer"
```

---

## Phase 4: DeepAgent with CompositeBackend & Vertex AI

### Task 5: Reconfigure Agent Factory with DeepAgent + CompositeBackend

**Files:**
- Modify: `frontend/lib/agent/index.ts` (rewrite agent factory)
- Create: `frontend/lib/agent/deep-agent-config.ts` (DeepAgent config)
- Modify: `frontend/lib/agent/providers.ts` (simplify to Vertex AI focus)

**Step 1: Create DeepAgent configuration module**

Create `frontend/lib/agent/deep-agent-config.ts`:
```typescript
import {
  createDeepAgent,
  CompositeBackend,
  StateBackend,
  StoreBackend,
} from "deepagents";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import { getCheckpointer } from "@/lib/db/postgres";

export interface DeepAgentOptions {
  model: BaseChatModel;
  systemPrompt: string;
  tools?: any[];
  subagents?: any[];
}

export function createOmniMindDeepAgent(options: DeepAgentOptions) {
  const checkpointer = getCheckpointer();

  const agent = createDeepAgent({
    model: options.model,
    tools: options.tools ?? [],
    subagents: options.subagents ?? [],
    systemPrompt: options.systemPrompt,
    name: "omnimind-agent",
    backend: (config: any) =>
      new CompositeBackend({
        state: new StateBackend(config),
        store: config.store ? new StoreBackend(config) : undefined,
      }),
    checkpointer,
  });

  return agent;
}
```

**Step 2: Simplify providers.ts to focus on Vertex AI**

Rewrite `frontend/lib/agent/providers.ts`:
```typescript
import { ChatVertexAI } from "@langchain/google-vertexai";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { ChatAnthropic } from "@langchain/anthropic";
import { ChatOpenAI } from "@langchain/openai";
import { ChatOllama } from "@langchain/ollama";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import type { LLMProvider } from "@/types/agent";
import fs from "fs";

const DEFAULT_VERTEX_CREDENTIALS_PATH =
  "/home/levybonito/Downloads/serviceAccount/serviceAccountVertex.json";

function getVertexProjectId(): string | undefined {
  const credentialsPath =
    process.env.VERTEXAI_CREDENTIALS_PATH ||
    process.env.GOOGLE_APPLICATION_CREDENTIALS ||
    DEFAULT_VERTEX_CREDENTIALS_PATH;

  try {
    const raw = fs.readFileSync(credentialsPath, "utf8");
    const parsed = JSON.parse(raw) as { project_id?: string };
    return parsed.project_id;
  } catch {
    return undefined;
  }
}

function getVertexLocation(model: string): string {
  // All gemini-3.x models use global location
  if (model.startsWith("gemini-3")) return "global";
  // Default to us-central1 for older models
  return "us-central1";
}

function ensureVertexEnv() {
  const credentialsPath =
    process.env.VERTEXAI_CREDENTIALS_PATH ||
    process.env.GOOGLE_APPLICATION_CREDENTIALS ||
    DEFAULT_VERTEX_CREDENTIALS_PATH;

  if (!process.env.GOOGLE_APPLICATION_CREDENTIALS && fs.existsSync(credentialsPath)) {
    process.env.GOOGLE_APPLICATION_CREDENTIALS = credentialsPath;
  }

  const projectId = getVertexProjectId();
  if (projectId) {
    process.env.GOOGLE_CLOUD_PROJECT ||= projectId;
    process.env.GCLOUD_PROJECT ||= projectId;
  }
}

export function getModelForProvider(
  provider: LLMProvider,
  model: string,
  options: { apiKey?: string; baseUrl?: string } = {}
): BaseChatModel {
  switch (provider) {
    case "vertexai": {
      ensureVertexEnv();
      return new ChatVertexAI({
        model,
        location: getVertexLocation(model),
        apiKey: options.apiKey || process.env.API_KEY || process.env.GOOGLE_API_KEY,
      });
    }

    case "google":
      return new ChatGoogleGenerativeAI({
        model,
        apiKey: options.apiKey || process.env.GOOGLE_API_KEY,
      });

    case "anthropic": {
      const config: ConstructorParameters<typeof ChatAnthropic>[0] = {
        model,
        anthropicApiKey: options.apiKey || process.env.ANTHROPIC_API_KEY,
      };
      const m = model.toLowerCase();
      if (m.includes("claude-sonnet-4") || m.includes("claude-opus-4")) {
        config.thinking = { type: "adaptive" };
      }
      return new ChatAnthropic(config);
    }

    case "openai":
      return new ChatOpenAI({
        model,
        openAIApiKey: options.apiKey || process.env.OPENAI_API_KEY,
      });

    case "ollama":
      return new ChatOllama({
        model,
        baseUrl: options.baseUrl || process.env.OLLAMA_BASE_URL || "http://localhost:11434",
      });

    default:
      throw new Error(`Unknown provider: ${provider}`);
  }
}

export const DEFAULT_PROVIDER: LLMProvider = "vertexai";
export const DEFAULT_MODEL = "gemini-3-flash-preview";
```

**Step 3: Rewrite agent index.ts to use DeepAgent factory**

Rewrite `frontend/lib/agent/index.ts`:
```typescript
import { createOmniMindDeepAgent } from "./deep-agent-config";
import { getModelForProvider, DEFAULT_PROVIDER, DEFAULT_MODEL } from "./providers";
import type { LLMProvider } from "@/types/agent";

const SYSTEM_PROMPT = `You are OmniMind, a powerful Deep Agent with planning, sub-agent delegation, filesystem access, and long-term memory capabilities.

You can:
- Plan complex tasks step-by-step using your todo list
- Delegate subtasks to specialized sub-agents
- Read, write, and search files in your workspace
- Remember important information across conversations
- Execute shell commands when needed

When reasoning through complex problems, think step by step. Your thinking process will be shown to the user in a collapsible section.

Be concise, helpful, and thorough.`;

export function createOmniMindAgent(
  provider: LLMProvider = DEFAULT_PROVIDER,
  model: string = DEFAULT_MODEL,
  options: { apiKey?: string; baseUrl?: string } = {}
) {
  const llm = getModelForProvider(provider, model, options);

  return createOmniMindDeepAgent({
    model: llm,
    systemPrompt: SYSTEM_PROMPT,
  });
}

export { DEFAULT_PROVIDER, DEFAULT_MODEL };
```

**Step 4: Update the chat route to use PostgreSQL checkpointer**

Modify `frontend/app/api/agent/chat/route.ts`:
- Replace `import { ensureDbInitialized } from "@/lib/db/init"` with `import { ensureDbInitialized } from "@/lib/db/postgres"`
- Update default provider/model imports
- Keep rest of streaming logic intact

**Step 5: Update agent-store default values**

Modify `frontend/stores/agent-store.ts`:
- Change default `provider` to `"vertexai"`
- Change default `model` to `"gemini-3-flash-preview"`

**Step 6: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

**Step 7: Commit**
```bash
git add -A && git commit -m "feat: reconfigure agent with DeepAgent + CompositeBackend + Vertex AI default"
```

---

## Phase 5: Fix Streaming Pipeline for Thinking/Reasoning

### Task 6: Update Stream Normalizer for Native Vertex AI Thinking

**Files:**
- Modify: `frontend/lib/agent/chat-stream-normalizer.ts`
- Modify: `frontend/app/api/agent/chat/route.ts`

The current normalizer uses `<think>` tags for Gemini reasoning (a workaround). With Vertex AI's native `thinkingConfig`, reasoning tokens come through the `additional_kwargs.thinking` or as content blocks with `type: "thinking"`. The normalizer already handles these patterns but we need to ensure the Vertex AI model is configured with `thinkingConfig`.

**Step 1: Update providers.ts to add thinkingConfig for Vertex AI**

In `frontend/lib/agent/providers.ts`, update the `vertexai` case:
```typescript
case "vertexai": {
  ensureVertexEnv();
  return new ChatVertexAI({
    model,
    location: getVertexLocation(model),
    apiKey: options.apiKey || process.env.API_KEY || process.env.GOOGLE_API_KEY,
    // Enable native thinking for models that support it
    ...(model.includes("flash") || model.includes("pro") ? {
      thinking: {
        includeThoughts: true,
        thinkingBudget: 8192,
      }
    } : {}),
  });
}
```

**Step 2: Remove the `<think>` tag workaround from agent index.ts**

The `GEMINI_THINKING_INSTRUCTION` constant and `isGeminiProvider` check that appends it to system prompt should be removed since we're using native thinking config now.

In `frontend/lib/agent/index.ts`, the system prompt should NOT include the `<think>` tag instruction.

**Step 3: Update normalizer to prioritize native thinking blocks**

The normalizer already handles `content.type === "thinking"` and `additional_kwargs.thinking`. Verify the `contentBlockText` function correctly extracts thinking from Vertex AI's native format.

No code changes needed here if the normalizer's `extractTextAndThought` already handles:
- `content[].type === "thinking"` -> thought
- `content[].type === "text"` -> text
- `additional_kwargs.thinking` -> thought

The existing normalizer code is comprehensive. The key fix is in Step 1 (enabling native thinking) and Step 2 (removing the `<think>` tag hack).

**Step 4: Update chat route to pass streamMode correctly**

In `frontend/app/api/agent/chat/route.ts`, ensure stream modes include `"messages"` and `"updates"`:
```typescript
const stream = await agent.stream(
  { messages: [new HumanMessage(fullMessage)] },
  {
    ...config,
    streamMode: ["messages", "updates"],
  }
);
```
(This is already correct in the current code.)

**Step 5: Verify streaming works end-to-end**

```bash
# Start the dev server
cd /home/levybonito/OmniMind && pnpm dev
```

Then test with curl:
```bash
curl -X POST http://localhost:3000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is 2+2? Think step by step.","provider":"vertexai","model":"gemini-3-flash-preview"}'
```

Expected: SSE events with `type: "thought"` and `type: "response"`.

**Step 6: Commit**
```bash
git add -A && git commit -m "feat: enable native Vertex AI thinking, remove <think> tag workaround"
```

---

### Task 7: Improve ThinkingBlock Component (Auto-Collapse + Live Streaming)

**Files:**
- Modify: `frontend/components/agent/thinking-block.tsx`

**Step 1: Rewrite ThinkingBlock with auto-collapse behavior**

The thinking block should:
- Start collapsed by default
- Show a preview of the first ~80 chars
- While streaming: show pulsing "Thinking..." with expanding content
- After streaming: show "Thought" with preview, click to expand
- Smooth expand/collapse animation

```tsx
"use client";

import React, { useState, useEffect, useRef } from "react";
import { Brain, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThinkingBlockProps {
  id: string;
  content: string;
  isStreaming: boolean;
  agentId?: string;
  agentColor?: string;
}

function ThinkingBlockInner({
  content,
  isStreaming,
  agentId,
}: ThinkingBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // Auto-expand briefly when streaming starts, then collapse
  useEffect(() => {
    if (isStreaming && content.length < 10) {
      // Don't auto-expand, keep collapsed while streaming
    }
  }, [isStreaming, content]);

  if (!content && !isStreaming) return null;

  const preview =
    content.length > 80 ? content.slice(0, 80).trimEnd() + "..." : content;

  const tokenCount = content.split(/\s+/).filter(Boolean).length;

  return (
    <div
      className={cn(
        "animate-fade-slide-up mb-2 rounded-md border-l-2 border-l-purple-500 bg-purple-500/5 dark:bg-purple-400/10",
        "transition-all duration-200"
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <Brain
          className={cn("h-3.5 w-3.5 shrink-0 text-purple-500", {
            "animate-pulse": isStreaming,
          })}
        />
        <span className="font-medium">
          {agentId ? `${agentId} ` : ""}
          {isStreaming ? "Thinking..." : "Thought"}
        </span>
        {!isStreaming && tokenCount > 0 && (
          <span className="text-[10px] opacity-40">{tokenCount} tokens</span>
        )}
        {!expanded && (
          <span className="min-w-0 flex-1 truncate opacity-60 italic">
            {preview}
          </span>
        )}
        {expanded ? (
          <ChevronDown className="ml-auto h-3 w-3 shrink-0" />
        ) : (
          <ChevronRight className="ml-auto h-3 w-3 shrink-0" />
        )}
      </button>

      <div
        ref={contentRef}
        className={cn(
          "overflow-hidden transition-all duration-200 ease-in-out",
          expanded ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
        )}
      >
        <div className="whitespace-pre-wrap px-3 pb-2 text-xs text-muted-foreground italic leading-relaxed">
          {content}
          {isStreaming && (
            <span className="ml-0.5 inline-block animate-pulse text-purple-400">|</span>
          )}
        </div>
      </div>
    </div>
  );
}

export const ThinkingBlock = React.memo(ThinkingBlockInner);
```

**Step 2: Verify visually in browser**

Navigate to `/agent`, send a message, verify:
- Thinking block appears collapsed with preview
- Click expands with animation
- Streaming shows pulsing cursor
- After completion, shows token count

**Step 3: Commit**
```bash
git add -A && git commit -m "feat: improve ThinkingBlock with auto-collapse and token count"
```

---

### Task 8: Improve ToolCallBlock Component

**Files:**
- Modify: `frontend/components/agent/tool-call-block.tsx`

**Step 1: Update ToolCallBlock with better UX**

The existing component is already well-structured. Enhance it with:
- Better loading animation
- Elapsed time counter while running
- Truncated output preview when collapsed

No major rewrite needed - the current implementation is solid. Minor polish:

```tsx
// Add elapsed time display for running tools
// In the ToolCallBlock component, add a useEffect that ticks every second when status === "running"
```

**Step 2: Commit**
```bash
git add -A && git commit -m "feat: polish ToolCallBlock with elapsed time and output preview"
```

---

### Task 9: Create ResponseBlock Component

**Files:**
- Create: `frontend/components/agent/response-block.tsx`
- Modify: `frontend/components/agent/chat-interface.tsx`

Currently, text responses use the generic `MessageBubble` component. Create a dedicated `ResponseBlock` that renders markdown properly.

**Step 1: Create ResponseBlock component**

Create `frontend/components/agent/response-block.tsx`:
```tsx
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";

interface ResponseBlockProps {
  content: string;
  isStreaming: boolean;
  agentId?: string;
}

function ResponseBlockInner({ content, isStreaming, agentId }: ResponseBlockProps) {
  if (!content && !isStreaming) return null;

  return (
    <div className="flex gap-3 py-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        {agentId && (
          <span className="mb-1 inline-block rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
            {agentId}
          </span>
        )}
        <div className={cn(
          "prose prose-sm dark:prose-invert max-w-none",
          "prose-p:my-1 prose-pre:my-2 prose-code:text-xs",
          "prose-headings:mt-3 prose-headings:mb-1"
        )}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
          >
            {content}
          </ReactMarkdown>
          {isStreaming && (
            <span className="ml-0.5 inline-block animate-pulse text-primary">|</span>
          )}
        </div>
      </div>
    </div>
  );
}

export const ResponseBlock = React.memo(ResponseBlockInner);
```

**Step 2: Update ChatInterface to use ResponseBlock for assistant text**

In `frontend/components/agent/chat-interface.tsx`, replace the `case "text"` rendering:
```tsx
case "text":
  if (!part.content) return null;
  return (
    <ResponseBlock
      content={part.content}
      isStreaming={isLastTextPart && messageIsStreaming}
      agentId={msg.agentId}
    />
  );
```

Import: `import { ResponseBlock } from "./response-block";`

**Step 3: Commit**
```bash
git add -A && git commit -m "feat: add ResponseBlock with markdown rendering"
```

---

## Phase 6: Provider Selector & Settings Updates

### Task 10: Update Provider Selector for Vertex AI Default

**Files:**
- Modify: `frontend/components/agent/provider-selector.tsx`
- Modify: `frontend/app/settings/page.tsx`

**Step 1: Update ProviderSelector with Vertex AI models**

Update the provider/model options to include:
- **Vertex AI** (default): gemini-3-flash-preview, gemini-2.5-flash, gemini-2.5-pro
- **Google AI**: gemini-2.5-flash, gemini-2.5-pro
- **Anthropic**: claude-sonnet-4, claude-opus-4
- **OpenAI**: gpt-4o, gpt-4o-mini
- **Ollama**: (user configurable)

**Step 2: Commit**
```bash
git add -A && git commit -m "feat: update provider selector with Vertex AI models as default"
```

---

## Phase 7: Swarm Integration Cleanup

### Task 11: Update Swarm Graph to Use PostgreSQL Checkpointer

**Files:**
- Modify: `frontend/lib/swarm/graph.ts`
- Modify: `frontend/lib/swarm/coder.ts`

**Step 1: Update swarm graph to compile with PostgreSQL checkpointer**

In `frontend/lib/swarm/graph.ts`, add checkpointer to graph compilation:
```typescript
import { getCheckpointer } from "@/lib/db/postgres";

// In createSwarmGraph():
const checkpointer = getCheckpointer();
const graph = new StateGraph(SwarmStateAnnotation)
  // ... nodes and edges ...
  .compile({ checkpointer });
```

**Step 2: Update coder node default provider and model**

In `frontend/lib/swarm/coder.ts`, update imports to use `DEFAULT_PROVIDER` and `DEFAULT_MODEL`.

**Step 3: Commit**
```bash
git add -A && git commit -m "feat: add PostgreSQL checkpointer to swarm graph"
```

---

## Phase 8: Final Cleanup & Verification

### Task 12: Remove Unused Dependencies and Final Cleanup

**Files:**
- Modify: `package.json` (final dependency audit)
- Delete: `frontend/lib/agent/conversations.ts` (if SQLite-dependent)
- Delete: `frontend/app/api/agent/conversations/` (if SQLite-dependent)

**Step 1: Audit all imports for dangling references**

```bash
cd frontend && grep -r "better-sqlite3\|drizzle\|@blocknote\|@react-three\|three\|note-tools" --include="*.ts" --include="*.tsx" -l
```

Fix any remaining imports.

**Step 2: Run pnpm install to clean lockfile**

```bash
cd /home/levybonito/OmniMind && pnpm install
```

**Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

**Step 4: Run build**

```bash
cd frontend && npx next build
```

**Step 5: Commit**
```bash
git add -A && git commit -m "chore: final cleanup - remove dangling imports and unused deps"
```

---

### Task 13: End-to-End Verification

**Step 1: Start PostgreSQL**

```bash
sudo systemctl start postgresql
```

**Step 2: Start the app**

```bash
cd /home/levybonito/OmniMind && pnpm dev
```

**Step 3: Test agent chat**

1. Open http://localhost:3000
2. Navigate to Agent page
3. Select Vertex AI / gemini-3-flash-preview
4. Send: "What is quantum computing? Think step by step."
5. Verify:
   - ThinkingBlock appears collapsed with preview
   - Click to expand shows reasoning tokens
   - ToolCallBlock appears if tools are used
   - ResponseBlock shows markdown-rendered response
   - No errors in console

**Step 4: Test conversation persistence**

1. Send a message: "My name is Levy"
2. Refresh the page
3. Send: "What's my name?"
4. Verify the agent remembers (PostgreSQL checkpointing)

**Step 5: Final commit**

```bash
git add -A && git commit -m "feat: OmniMind v2 - DeepAgent + Vertex AI + PostgreSQL"
```

---

## Latency Optimization Notes

1. **Vertex AI Location**: Using `"global"` for gemini-3-flash-preview routes to nearest region
2. **Connection Pooling**: PostgreSQL pool with `max: 10` connections, reused across requests
3. **Stream Mode**: Using `["messages", "updates"]` instead of `streamEvents` (v2) - fewer intermediate events
4. **Normalizer Efficiency**: The existing normalizer is highly optimized with deduplication sets and pending tool tracking
5. **React.memo**: All heavy components (ThinkingBlock, ToolCallBlock, ResponseBlock) are memoized
6. **SSE over WebSocket**: Lower overhead for one-directional streaming

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Eliminate Express | Reduces infra complexity, Next.js API routes handle everything |
| PostgreSQL over SQLite | Production-ready, supports LangGraph checkpointer natively |
| CompositeBackend | Separates ephemeral state from persistent memory |
| Native thinkingConfig | Vertex AI's built-in reasoning is more reliable than `<think>` tags |
| deepagentsjs | Already installed, TypeScript-native, includes all middleware |
| SSE streaming | Simpler than WebSockets for one-directional token streaming |
