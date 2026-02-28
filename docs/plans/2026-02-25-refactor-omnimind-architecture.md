# OmniMind Architecture Refactor — Option B Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refatorar o projeto OmniMind para uma arquitetura com separação física de pastas `frontend/`, `backend/` e `shared/`, mantendo `src/app/` exclusivo para roteamento Next.js, com Zod validations, server-only guards e correção de todos os issues identificados.

**Architecture:** Next.js 16 full-stack com separação explícita: `frontend/` (componentes, hooks, stores Zustand), `backend/` (agentes, swarm, DB, schemas Zod, config, utils) e `shared/` (tipos TypeScript puros). `src/app/` permanece apenas como entry point das rotas Next.js. Path aliases configurados no tsconfig e next.config.

**Tech Stack:** Next.js 16, React 19, TypeScript 5.9, Zod 4, Zustand 5, LangGraph 1.1, LangChain (anthropic/openai/google/vertexai/ollama), deepagents, PostgreSQL (pg), Tailwind 4, Radix UI, Vitest 4.

---

## Estrutura Alvo

```
OmniMind/
│
├── frontend/                          ← código client-only
│   ├── components/
│   │   ├── agent/
│   │   ├── swarm/
│   │   ├── layout/
│   │   ├── logs/
│   │   └── ui/
│   ├── hooks/
│   │   ├── use-agent-chat.ts
│   │   ├── use-log-stream.ts
│   │   └── use-swarm-stream.ts
│   └── stores/
│       ├── agent.store.ts             ← renomeado de agent-store.ts
│       └── swarm.store.ts             ← renomeado de swarm-store.ts
│
├── backend/                           ← código server-only
│   ├── agent/                         ← domínio Agent Chat
│   │   ├── index.ts                   ← import "server-only"
│   │   ├── deep-agent-config.ts
│   │   ├── providers.ts               ← sem hardpath
│   │   ├── safe-backend.ts
│   │   ├── conversations.ts
│   │   ├── log-bus.ts
│   │   ├── node-registry.ts
│   │   ├── output-categorizer.ts
│   │   ├── stream.ts
│   │   ├── stream-event-queue.ts
│   │   ├── chat-stream-normalizer.ts
│   │   ├── tools/
│   │   │   └── search-web.ts
│   │   └── prompts/
│   │       ├── base.ts
│   │       ├── dynamic-prompt.ts
│   │       └── tools/
│   │           ├── filesystem.ts
│   │           ├── shell.ts
│   │           ├── task-planning.ts
│   │           └── web-search.ts
│   ├── swarm/                         ← domínio Swarm
│   │   ├── graph.ts                   ← import "server-only"
│   │   ├── state.ts
│   │   ├── orchestrator.ts
│   │   ├── coder.ts
│   │   ├── live-analyst.ts
│   │   ├── reviewer.ts
│   │   ├── sandbox-renderer.ts
│   │   ├── notifier.ts
│   │   ├── registry.ts
│   │   ├── tools/
│   │   │   ├── analyst-tools.ts
│   │   │   ├── coder-tools.ts
│   │   │   └── reviewer-tools.ts
│   │   ├── prompts/
│   │   │   ├── router.ts
│   │   │   ├── analyst-prompt.ts
│   │   │   ├── coder-prompt.ts
│   │   │   ├── orchestrator-prompt.ts
│   │   │   └── reviewer-prompt.ts
│   │   ├── templates/
│   │   │   ├── index.ts
│   │   │   ├── cli-tool.ts
│   │   │   ├── file-tree.ts
│   │   │   ├── graphql.ts
│   │   │   ├── microservices.ts
│   │   │   └── rest-api.ts
│   │   └── utils/
│   │       └── deduplicate-tools.ts
│   ├── db/
│   │   └── postgres.ts                ← import "server-only"
│   ├── schemas/                       ← Zod schemas centralizados
│   │   ├── agent.schema.ts
│   │   ├── swarm.schema.ts
│   │   └── settings.schema.ts
│   ├── config/
│   │   └── index.ts                   ← Zod-validated, todas as variáveis
│   └── utils/
│       └── logger.ts
│
├── shared/                            ← tipos TypeScript puros (sem Zod, sem server deps)
│   └── types/
│       ├── agent.ts
│       ├── swarm.ts                   ← apenas interfaces, sem schemas Zod
│       ├── settings.ts
│       ├── common.ts                  ← ApiResponse, PaginatedResponse, StreamChunk, etc.
│       └── index.ts                   ← barrel re-export
│
└── src/
    └── app/                           ← Next.js App Router APENAS
        ├── api/
        │   ├── agent/
        │   │   ├── chat/route.ts      ← usa @backend/schemas/agent.schema
        │   │   ├── conversations/route.ts
        │   │   └── conversations/[id]/messages/route.ts
        │   ├── swarm/
        │   │   ├── route.ts
        │   │   ├── [taskId]/route.ts
        │   │   └── [taskId]/stream/route.ts
        │   ├── settings/route.ts
        │   └── logs/stream/route.ts
        ├── agent/page.tsx
        ├── swarm/page.tsx
        ├── logs/page.tsx
        ├── settings/page.tsx
        ├── layout.tsx
        ├── page.tsx
        └── globals.css
```

**Path Aliases (tsconfig.json + next.config.ts):**
```
@/*          → ./src/*
@frontend/*  → ./frontend/*
@backend/*   → ./backend/*
@shared/*    → ./shared/*
```

---

## Task 1: Criar estrutura de diretórios

**Objetivo:** Criar todos os diretórios vazios da nova estrutura. Não mover arquivos ainda.

**Files:**
- Create dirs: `frontend/components/`, `frontend/hooks/`, `frontend/stores/`
- Create dirs: `backend/agent/`, `backend/swarm/`, `backend/db/`, `backend/schemas/`, `backend/config/`, `backend/utils/`
- Create dirs: `shared/types/`

**Step 1: Criar os diretórios**

```bash
cd /home/levybonito/Projetos/OmniMind
mkdir -p frontend/components frontend/hooks frontend/stores
mkdir -p backend/agent/tools backend/agent/prompts/tools
mkdir -p backend/swarm/tools backend/swarm/prompts backend/swarm/templates backend/swarm/utils
mkdir -p backend/db backend/schemas backend/config backend/utils
mkdir -p shared/types
```

**Step 2: Verificar estrutura criada**

```bash
cd /home/levybonito/Projetos/OmniMind
find frontend backend shared -type d | sort
```

Esperado: todas as pastas listadas acima.

**Step 3: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add frontend/ backend/ shared/
git commit -m "chore: scaffold frontend/, backend/, shared/ directory structure"
```

---

## Task 2: Mover componentes, hooks e stores → `frontend/`

**Objetivo:** Mover todo o código client-only de `src/` para `frontend/`.

**Files:**
- Move: `src/components/` → `frontend/components/`
- Move: `src/hooks/` → `frontend/hooks/`
- Move: `src/stores/agent-store.ts` → `frontend/stores/agent.store.ts`
- Move: `src/stores/swarm-store.ts` → `frontend/stores/swarm.store.ts`

**Step 1: Mover components e hooks**

```bash
cd /home/levybonito/Projetos/OmniMind
cp -r src/components/* frontend/components/
cp -r src/hooks/* frontend/hooks/
cp src/stores/agent-store.ts frontend/stores/agent.store.ts
cp src/stores/swarm-store.ts frontend/stores/swarm.store.ts
```

**Step 2: Verificar arquivos copiados**

```bash
find frontend/ -name "*.ts" -o -name "*.tsx" | sort
```

**Step 3: Commit (ainda sem deletar os originais)**

```bash
cd /home/levybonito/Projetos/OmniMind
git add frontend/
git commit -m "chore: copy components, hooks, stores to frontend/ (originals kept temporarily)"
```

---

## Task 3: Mover tipos para `shared/types/`

**Objetivo:** Mover tipos TypeScript puros (sem Zod, sem deps de servidor) para `shared/types/`.

**Files:**
- Move: `src/types/agent.ts` → `shared/types/agent.ts`
- Move: `src/types/settings.ts` → `shared/types/settings.ts`
- Create: `shared/types/swarm.ts` (versão limpa, sem schemas Zod)
- Create: `shared/types/common.ts` (tipos utilitários de `src/types/index.ts`)
- Create: `shared/types/index.ts` (barrel)

**Step 1: Copiar `agent.ts` e `settings.ts`**

```bash
cd /home/levybonito/Projetos/OmniMind
cp src/types/agent.ts shared/types/agent.ts
cp src/types/settings.ts shared/types/settings.ts
```

**Step 2: Criar `shared/types/swarm.ts` — versão limpa sem schemas Zod**

```typescript
// shared/types/swarm.ts
/**
 * Swarm-specific TypeScript interfaces and union types.
 * Pure types only — no Zod schemas. Schemas live in backend/schemas/.
 */

// ============================================================================
// Core Union Types
// ============================================================================

/** All notification event types emitted by swarm agents */
export type SwarmEventType =
  | "AGENT_STATE_CHANGE"
  | "TOKEN_STREAM"
  | "TOOL_CALL"
  | "TOOL_RESULT"
  | "FILE_CHANGE"
  | "PLAN_UPDATE"
  | "ANALYST_FINDING"
  | "ANALYST_STATE_CHANGE"
  | "REVIEW_FINDING"
  | "SANDBOX_UPDATE"
  | "ERROR";

/** Agent identifiers within the swarm */
export type SwarmAgentId =
  | "orchestrator"
  | "coder"
  | "live_analyst"
  | "reviewer"
  | "sandbox_renderer";

/** Live Analyst alert levels */
export type AnalystAlertLevel =
  | "IDLE"
  | "MONITORING"
  | "ALERT_LOW"
  | "ALERT_MODERATE"
  | "ALERT_CRITICAL";

/** Task lifecycle status */
export type TaskStatus =
  | "pending"
  | "planning"
  | "coding"
  | "reviewing"
  | "complete"
  | "error";

/** Reviewer overall assessment */
export type ReviewAssessment =
  | "APPROVED"
  | "APPROVED_WITH_SUGGESTIONS"
  | "CHANGES_REQUESTED";

// ============================================================================
// Entry Interfaces (for state list fields)
// ============================================================================

export interface TokenStreamEntry {
  token: string;
  timestamp: string;
}

export interface ToolCallEntry {
  name: string;
  input: Record<string, unknown>;
  output: unknown;
  timestamp: string;
}

export interface FileChangeEntry {
  filepath: string;
  action: "create" | "modify" | "delete";
  diff_summary: string;
}

export interface InterruptionRequest {
  urgency: "CRITICAL";
  issue: string;
  file: string;
  suggested_action: string;
  evidence: string;
}

export interface ReviewImprovement {
  category: string;
  filepath: string;
  line_range: string;
  description: string;
  improvement: string;
}

// ============================================================================
// Notification Event
// ============================================================================

export interface NotificationEvent {
  event_id: string;
  event_type: SwarmEventType;
  agent_id: SwarmAgentId;
  timestamp: string;
  payload: Record<string, unknown>;
  metadata: {
    task_id: string;
    sequence_number: number;
  };
}

// ============================================================================
// API Interfaces
// ============================================================================

export interface SwarmTaskSubmission {
  description: string;
  provider?: string;
  model?: string;
  workingPath?: string;
}

export interface SwarmTaskStatus {
  task_id: string;
  task_status: TaskStatus;
  coder_plan: string | null;
  analyst_state: AnalystAlertLevel;
  sandbox_display: string;
  notifications_count: number;
}
```

**Step 3: Criar `shared/types/common.ts`**

```typescript
// shared/types/common.ts
/**
 * Common utility types shared across all domains.
 */

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
  timestamp?: string;
}

export interface ResponseMetadata {
  timestamp: string;
  requestId?: string;
  duration?: number;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
  metadata?: ResponseMetadata;
}

export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// ============================================================================
// Streaming Types
// ============================================================================

export interface StreamChunk<T = unknown> {
  type: "data" | "error" | "complete";
  data?: T;
  error?: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Utility Types
// ============================================================================

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type DeepRequired<T> = {
  [P in keyof T]-?: T[P] extends object ? DeepRequired<T[P]> : T[P];
};

export type MaybePromise<T> = T | Promise<T>;

export type AsyncFunction<TArgs extends unknown[] = unknown[], TReturn = unknown> = (
  ...args: TArgs
) => Promise<TReturn>;

export type Environment = "development" | "production" | "test";
```

**Step 4: Criar `shared/types/index.ts`**

```typescript
// shared/types/index.ts
export type * from "./agent";
export type * from "./swarm";
export type * from "./settings";
export type * from "./common";
```

**Step 5: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add shared/
git commit -m "refactor: create shared/types/ with clean TypeScript interfaces (no Zod)"
```

---

## Task 4: Mover módulos backend para `backend/`

**Objetivo:** Mover toda a lógica server-side de `src/lib/`, `src/config/`, `src/utils/` para `backend/`.

**Files:**
- Move: `src/lib/agent/` → `backend/agent/`
- Move: `src/lib/swarm/` → `backend/swarm/`
- Move: `src/lib/db/postgres.ts` → `backend/db/postgres.ts`
- Move: `src/config/index.ts` → `backend/config/index.ts`
- Move: `src/utils/logger.ts` → `backend/utils/logger.ts`

**Step 1: Copiar módulos**

```bash
cd /home/levybonito/Projetos/OmniMind
cp -r src/lib/agent/* backend/agent/
cp -r src/lib/swarm/* backend/swarm/
cp src/lib/db/postgres.ts backend/db/postgres.ts
cp src/config/index.ts backend/config/index.ts
cp src/utils/logger.ts backend/utils/logger.ts
```

**Step 2: Verificar**

```bash
find backend/ -name "*.ts" | sort
```

**Step 3: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add backend/
git commit -m "chore: copy backend modules to backend/ (originals kept temporarily)"
```

---

## Task 5: Criar schemas Zod em `backend/schemas/`

**Objetivo:** Centralizar todas as validações Zod em `backend/schemas/`, separadas das interfaces TypeScript em `shared/types/`.

**Files:**
- Create: `backend/schemas/agent.schema.ts`
- Create: `backend/schemas/swarm.schema.ts`
- Create: `backend/schemas/settings.schema.ts`

**Step 1: Criar `backend/schemas/agent.schema.ts`**

```typescript
// backend/schemas/agent.schema.ts
import "server-only";
import { z } from "zod";

export const llmProviderSchema = z.enum([
  "anthropic",
  "openai",
  "ollama",
  "google",
  "vertexai",
]);

export const agentChatRequestSchema = z.object({
  message: z
    .string()
    .min(1, "Message cannot be empty")
    .max(100_000, "Message too long"),
  provider: llmProviderSchema.optional(),
  model: z.string().optional(),
  conversationId: z.string().optional(),
  debugSteps: z.boolean().optional().default(false),
});

export const conversationCreateSchema = z.object({
  title: z.string().min(1).max(200).optional(),
});

export type AgentChatRequest = z.infer<typeof agentChatRequestSchema>;
export type ConversationCreate = z.infer<typeof conversationCreateSchema>;
```

**Step 2: Criar `backend/schemas/swarm.schema.ts`**

```typescript
// backend/schemas/swarm.schema.ts
import "server-only";
import { z } from "zod";
import { llmProviderSchema } from "./agent.schema";

export const swarmTaskSubmissionSchema = z.object({
  description: z
    .string()
    .min(1, "Task description is required")
    .max(10_000, "Task description must be at most 10000 characters"),
  provider: llmProviderSchema.optional(),
  model: z.string().optional(),
  workingPath: z.string().optional(),
});

export const notificationEventSchema = z.object({
  event_id: z.string().uuid(),
  event_type: z.enum([
    "AGENT_STATE_CHANGE",
    "TOKEN_STREAM",
    "TOOL_CALL",
    "TOOL_RESULT",
    "FILE_CHANGE",
    "PLAN_UPDATE",
    "ANALYST_FINDING",
    "ANALYST_STATE_CHANGE",
    "REVIEW_FINDING",
    "SANDBOX_UPDATE",
    "ERROR",
  ]),
  agent_id: z.enum([
    "orchestrator",
    "coder",
    "live_analyst",
    "reviewer",
    "sandbox_renderer",
  ]),
  timestamp: z.string().datetime(),
  payload: z.record(z.string(), z.unknown()),
  metadata: z.object({
    task_id: z.string(),
    sequence_number: z.number().int().nonnegative(),
  }),
});

export type SwarmTaskSubmissionInput = z.infer<typeof swarmTaskSubmissionSchema>;
export type NotificationEventInput = z.infer<typeof notificationEventSchema>;
```

**Step 3: Criar `backend/schemas/settings.schema.ts`**

```typescript
// backend/schemas/settings.schema.ts
import "server-only";
import { z } from "zod";
import { llmProviderSchema } from "./agent.schema";

export const appSettingsSchema = z.object({
  defaultProvider: llmProviderSchema,
  defaultModel: z.string().min(1),
  anthropicApiKey: z.string().default(""),
  openaiApiKey: z.string().default(""),
  googleApiKey: z.string().default(""),
  ollamaBaseUrl: z
    .string()
    .url("Must be a valid URL")
    .default("http://localhost:11434"),
});

export const settingsUpdateSchema = appSettingsSchema.partial();

export type AppSettingsInput = z.infer<typeof appSettingsSchema>;
export type SettingsUpdate = z.infer<typeof settingsUpdateSchema>;
```

**Step 4: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add backend/schemas/
git commit -m "feat: create backend/schemas/ with Zod validation for agent, swarm, settings"
```

---

## Task 6: Reescrever `backend/config/index.ts` com validação completa

**Objetivo:** O config atual valida apenas 7 variáveis. Expandir para todas as variáveis do projeto, com `server-only` guard.

**Files:**
- Modify: `backend/config/index.ts`

**Step 1: Reescrever `backend/config/index.ts`**

```typescript
// backend/config/index.ts
import "server-only";
import { z } from "zod";

const configSchema = z.object({
  // Server
  nodeEnv: z.enum(["development", "production", "test"]).default("development"),
  port: z.coerce.number().int().min(1).max(65535).default(3000),

  // Database
  databaseUrl: z.string().url().optional(),

  // Default LLM
  defaultProvider: z
    .enum(["anthropic", "openai", "ollama", "google", "vertexai"])
    .default("vertexai"),
  defaultModel: z.string().default("gemini-3-flash-preview"),
  defaultTemperature: z.coerce.number().min(0).max(2).default(0.7),
  maxTokens: z.coerce.number().int().positive().default(8192),
  enableStreaming: z.boolean().default(true),

  // LLM API Keys (optional — user can provide via Settings UI)
  anthropicApiKey: z.string().optional(),
  openaiApiKey: z.string().optional(),
  googleApiKey: z.string().optional(),
  ollamaBaseUrl: z.string().url().default("http://localhost:11434"),

  // Vertex AI
  vertexCredentialsPath: z.string().optional(),
  googleCloudProject: z.string().optional(),

  // Logging
  logLevel: z.enum(["error", "warn", "info", "debug"]).default("info"),

  // Search
  tavilyApiKey: z.string().optional(),
  searxngUrl: z.string().url().optional(),
});

function buildConfig() {
  try {
    return configSchema.parse({
      nodeEnv: process.env.NODE_ENV,
      port: process.env.PORT,
      databaseUrl: process.env.DATABASE_URL,
      defaultProvider: process.env.DEFAULT_PROVIDER,
      defaultModel: process.env.DEFAULT_MODEL,
      defaultTemperature: process.env.DEFAULT_TEMPERATURE,
      maxTokens: process.env.MAX_TOKENS,
      enableStreaming: process.env.ENABLE_STREAMING !== "false",
      anthropicApiKey: process.env.ANTHROPIC_API_KEY,
      openaiApiKey: process.env.OPENAI_API_KEY,
      googleApiKey: process.env.GOOGLE_API_KEY,
      ollamaBaseUrl: process.env.OLLAMA_BASE_URL,
      vertexCredentialsPath:
        process.env.VERTEXAI_CREDENTIALS_PATH ||
        process.env.GOOGLE_APPLICATION_CREDENTIALS,
      googleCloudProject:
        process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT,
      logLevel: process.env.LOG_LEVEL,
      tavilyApiKey: process.env.TAVILY_API_KEY,
      searxngUrl: process.env.SEARXNG_URL,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error("Configuration validation error:", error.issues);
      throw new Error("Invalid configuration. Check environment variables.");
    }
    throw error;
  }
}

export const config = buildConfig();
export type Config = z.infer<typeof configSchema>;

export const isProduction = () => config.nodeEnv === "production";
export const isDevelopment = () => config.nodeEnv === "development";
export const isTest = () => config.nodeEnv === "test";

export default config;
```

**Step 2: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add backend/config/index.ts
git commit -m "feat: expand backend/config with full env var validation and server-only guard"
```

---

## Task 7: Atualizar `tsconfig.json` e `next.config.ts` com os novos path aliases

**Objetivo:** Configurar `@frontend/*`, `@backend/*` e `@shared/*` como path aliases para que imports funcionem com a nova estrutura.

**Files:**
- Modify: `tsconfig.json`
- Modify: `next.config.ts`

**Step 1: Ler o tsconfig atual**

```bash
cat /home/levybonito/Projetos/OmniMind/tsconfig.json
```

**Step 2: Atualizar `tsconfig.json`**

No campo `paths`, adicionar os novos aliases. O arquivo atual tem apenas `"@/*": ["./src/*"]`. Atualizar para:

```jsonc
{
  "compilerOptions": {
    // ... manter todas as outras opções
    "paths": {
      "@/*": ["./src/*"],
      "@frontend/*": ["./frontend/*"],
      "@backend/*": ["./backend/*"],
      "@shared/*": ["./shared/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**IMPORTANTE:** Remover `"backend"` e `"frontend"` do `exclude` (se presentes), pois agora essas pastas devem ser compiladas.

**Step 3: Atualizar `next.config.ts`**

```typescript
import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  experimental: {
    turbo: {
      root: path.resolve(__dirname),
      resolveAlias: {
        "@frontend": path.resolve(__dirname, "frontend"),
        "@backend": path.resolve(__dirname, "backend"),
        "@shared": path.resolve(__dirname, "shared"),
      },
    },
  },
};

export default nextConfig;
```

**Step 4: Verificar build TypeScript**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -30
```

**Step 5: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add tsconfig.json next.config.ts
git commit -m "feat: add @frontend, @backend, @shared path aliases to tsconfig and next.config"
```

---

## Task 8: Atualizar imports em `backend/` para usar novos aliases

**Objetivo:** Todos os arquivos em `backend/` devem usar `@backend/*` e `@shared/*` em vez de `@/lib/*`, `@/types/*`, `@/config/*`.

**Files:**
- Modify: todos os arquivos `.ts` em `backend/`

**Step 1: Verificar quais imports precisam ser atualizados**

```bash
cd /home/levybonito/Projetos/OmniMind
grep -rn "from \"@/lib\|from \"@/types\|from \"@/config\|from \"@/utils\|from \"@/schemas\"" backend/ --include="*.ts"
```

**Step 2: Substituir os padrões de import**

```bash
cd /home/levybonito/Projetos/OmniMind
# @/lib/agent → @backend/agent
find backend/ -name "*.ts" | xargs sed -i 's|from "@/lib/agent|from "@backend/agent|g'
# @/lib/swarm → @backend/swarm
find backend/ -name "*.ts" | xargs sed -i 's|from "@/lib/swarm|from "@backend/swarm|g'
# @/lib/db → @backend/db
find backend/ -name "*.ts" | xargs sed -i 's|from "@/lib/db|from "@backend/db|g'
# @/config → @backend/config
find backend/ -name "*.ts" | xargs sed -i 's|from "@/config|from "@backend/config|g'
# @/utils → @backend/utils
find backend/ -name "*.ts" | xargs sed -i 's|from "@/utils|from "@backend/utils|g'
# @/types → @shared/types
find backend/ -name "*.ts" | xargs sed -i 's|from "@/types|from "@shared/types|g'
# @/schemas → @backend/schemas
find backend/ -name "*.ts" | xargs sed -i 's|from "@/schemas|from "@backend/schemas|g'
```

**Step 3: Verificar TypeScript**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -50
```

Corrigir quaisquer erros restantes de import manualmente.

**Step 4: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add backend/
git commit -m "refactor: update all imports in backend/ to use @backend/* and @shared/* aliases"
```

---

## Task 9: Atualizar imports em `frontend/` para usar novos aliases

**Objetivo:** Todos os arquivos em `frontend/` devem usar `@frontend/*`, `@shared/*`, e manter referências a `@backend/*` apenas para tipos (não módulos server-only).

**Files:**
- Modify: todos os arquivos `.ts` e `.tsx` em `frontend/`

**Step 1: Verificar quais imports precisam ser atualizados**

```bash
cd /home/levybonito/Projetos/OmniMind
grep -rn "from \"@/" frontend/ --include="*.ts" --include="*.tsx"
```

**Step 2: Substituir os padrões de import**

```bash
cd /home/levybonito/Projetos/OmniMind
# @/components → @frontend/components
find frontend/ -name "*.ts" -o -name "*.tsx" | xargs sed -i 's|from "@/components|from "@frontend/components|g'
# @/hooks → @frontend/hooks
find frontend/ -name "*.ts" -o -name "*.tsx" | xargs sed -i 's|from "@/hooks|from "@frontend/hooks|g'
# @/stores → @frontend/stores
find frontend/ -name "*.ts" -o -name "*.tsx" | xargs sed -i 's|from "@/stores|from "@frontend/stores|g'
# @/types → @shared/types
find frontend/ -name "*.ts" -o -name "*.tsx" | xargs sed -i 's|from "@/types|from "@shared/types|g'
# Correção de convenção de nomes de stores
find frontend/ -name "*.ts" -o -name "*.tsx" | xargs sed -i 's|stores/agent-store|stores/agent.store|g'
find frontend/ -name "*.ts" -o -name "*.tsx" | xargs sed -i 's|stores/swarm-store|stores/swarm.store|g'
```

**Step 3: Verificar TypeScript**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -50
```

**Step 4: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add frontend/
git commit -m "refactor: update all imports in frontend/ to use @frontend/* and @shared/* aliases"
```

---

## Task 10: Atualizar rotas API em `src/app/api/` para usar novos aliases + validação Zod

**Objetivo:** As rotas API devem importar de `@backend/` e `@shared/`, e ter validação Zod em todas as rotas que recebem input.

**Files:**
- Modify: `src/app/api/agent/chat/route.ts`
- Modify: `src/app/api/swarm/route.ts`
- Modify: `src/app/api/settings/route.ts`
- Modify: demais rotas em `src/app/api/`

**Step 1: Verificar imports nas rotas atuais**

```bash
grep -rn "from \"@/" src/app/api/ --include="*.ts"
```

**Step 2: Substituir imports em todas as rotas**

```bash
cd /home/levybonito/Projetos/OmniMind
find src/app/api/ -name "*.ts" | xargs sed -i \
  -e 's|from "@/lib/agent|from "@backend/agent|g' \
  -e 's|from "@/lib/swarm|from "@backend/swarm|g' \
  -e 's|from "@/lib/db|from "@backend/db|g' \
  -e 's|from "@/config|from "@backend/config|g' \
  -e 's|from "@/utils|from "@backend/utils|g' \
  -e 's|from "@/types|from "@shared/types|g' \
  -e 's|from "@/schemas|from "@backend/schemas|g'
```

**Step 3: Adicionar validação Zod em `src/app/api/agent/chat/route.ts`**

O arquivo atual usa type assertion `body as {...}`. Substituir pelo padrão safeParse:

```typescript
// Adicionar import:
import { agentChatRequestSchema } from "@backend/schemas/agent.schema";

// No POST handler, substituir destructure sem validação:
// DE:
const {
  message,
  provider = DEFAULT_PROVIDER,
  model = DEFAULT_MODEL,
  conversationId,
} = body as { ... };

// PARA:
const parsed = agentChatRequestSchema.safeParse(body);
if (!parsed.success) {
  return new Response(
    JSON.stringify({ error: "Invalid request", details: parsed.error.flatten().fieldErrors }),
    { status: 400, headers: { "Content-Type": "application/json" } }
  );
}
const { message, provider = DEFAULT_PROVIDER, model = DEFAULT_MODEL, conversationId } = parsed.data;
```

**Step 4: Atualizar `src/app/api/swarm/route.ts` para usar `@backend/schemas`**

```typescript
// Trocar import:
// DE: import { swarmTaskSubmissionSchema } from "@/types/swarm";
// PARA:
import { swarmTaskSubmissionSchema } from "@backend/schemas/swarm.schema";
```

**Step 5: Adicionar validação Zod em `src/app/api/settings/route.ts`**

```typescript
// Adicionar import:
import { settingsUpdateSchema } from "@backend/schemas/settings.schema";

// No PUT handler, substituir loop sem validação:
// DE:
for (const [key, value] of Object.entries(body)) {
  if (typeof value === "string") {
    settingsStore.set(key, value);
  }
}

// PARA:
const parsed = settingsUpdateSchema.safeParse(body);
if (!parsed.success) {
  return NextResponse.json(
    { error: "Invalid settings", details: parsed.error.flatten().fieldErrors },
    { status: 400 }
  );
}
for (const [key, value] of Object.entries(parsed.data)) {
  if (value !== undefined) {
    settingsStore.set(key, String(value));
  }
}
```

**Step 6: Verificar TypeScript**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -50
```

**Step 7: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add src/app/api/
git commit -m "refactor: update API routes to @backend/* aliases + add Zod validation to all routes"
```

---

## Task 11: Atualizar imports nas páginas `src/app/`

**Objetivo:** As páginas Next.js devem importar componentes de `@frontend/` e tipos de `@shared/`.

**Files:**
- Modify: `src/app/layout.tsx`
- Modify: `src/app/page.tsx`
- Modify: `src/app/agent/page.tsx`
- Modify: `src/app/swarm/page.tsx`
- Modify: `src/app/settings/page.tsx`
- Modify: `src/app/logs/page.tsx`

**Step 1: Verificar imports atuais nas páginas**

```bash
grep -rn "from \"@/" src/app/ --include="*.tsx" --include="*.ts" | grep -v "api/"
```

**Step 2: Substituir imports**

```bash
cd /home/levybonito/Projetos/OmniMind
find src/app/ -name "*.tsx" -o -name "*.ts" | grep -v "api/" | xargs sed -i \
  -e 's|from "@/components|from "@frontend/components|g' \
  -e 's|from "@/hooks|from "@frontend/hooks|g' \
  -e 's|from "@/stores|from "@frontend/stores|g' \
  -e 's|from "@/types|from "@shared/types|g'
```

**Step 3: Verificar TypeScript**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -50
```

**Step 4: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add src/app/
git commit -m "refactor: update app/ pages imports to @frontend/* and @shared/* aliases"
```

---

## Task 12: Corrigir `backend/agent/providers.ts` — remover hardpath

**Objetivo:** Remover o path absoluto hardcoded `/home/levybonito/Downloads/serviceAccount/serviceAccountVertex.json` do arquivo providers.

**Files:**
- Modify: `backend/agent/providers.ts`

**Step 1: Verificar a função que usa o hardpath**

```bash
grep -n "DEFAULT_VERTEX_CREDENTIALS_PATH\|levybonito" backend/agent/providers.ts
```

**Step 2: Substituir a constante hardcoded**

No arquivo `backend/agent/providers.ts`:

```typescript
// REMOVER esta linha:
const DEFAULT_VERTEX_CREDENTIALS_PATH =
  "/home/levybonito/Downloads/serviceAccount/serviceAccountVertex.json";

// Em getVertexProjectId(), substituir referências por:
function getVertexProjectId(): string | undefined {
  const credentialsPath =
    process.env.VERTEXAI_CREDENTIALS_PATH ||
    process.env.GOOGLE_APPLICATION_CREDENTIALS;

  if (!credentialsPath) return undefined;

  try {
    const raw = fs.readFileSync(credentialsPath, "utf8");
    const parsed = JSON.parse(raw) as { project_id?: string };
    return parsed.project_id;
  } catch {
    return undefined;
  }
}

// Em ensureVertexEnv(), substituir referências por:
function ensureVertexEnv(): void {
  const credentialsPath =
    process.env.VERTEXAI_CREDENTIALS_PATH ||
    process.env.GOOGLE_APPLICATION_CREDENTIALS;

  if (credentialsPath && !process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    if (fs.existsSync(credentialsPath)) {
      process.env.GOOGLE_APPLICATION_CREDENTIALS = credentialsPath;
    }
  }

  const projectId = getVertexProjectId();
  if (projectId) {
    process.env.GOOGLE_CLOUD_PROJECT ??= projectId;
    process.env.GCLOUD_PROJECT ??= projectId;
  }
}
```

**Step 3: Verificar TypeScript**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -30
```

**Step 4: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add backend/agent/providers.ts
git commit -m "fix: remove hardcoded credentials path from providers.ts, use env vars only"
```

---

## Task 13: Adicionar `import "server-only"` nos módulos críticos de backend

**Objetivo:** Prevenir que módulos server-only (com acesso a DB, FS, env vars de API keys) sejam importados no bundle client.

**Files:**
- Modify: `backend/db/postgres.ts`
- Modify: `backend/agent/index.ts`
- Modify: `backend/agent/providers.ts`
- Modify: `backend/agent/deep-agent-config.ts`
- Modify: `backend/swarm/graph.ts`
- Modify: `backend/swarm/coder.ts`
- Modify: `backend/swarm/live-analyst.ts`
- Modify: `backend/swarm/reviewer.ts`
- Modify: `backend/swarm/orchestrator.ts`
- Modify: `backend/config/index.ts` (já tem)
- Modify: `backend/schemas/` (já tem nos criados acima)

**Step 1: Verificar se `server-only` está no package.json**

```bash
cd /home/levybonito/Projetos/OmniMind && grep '"server-only"' package.json || echo "NOT FOUND"
```

Se não encontrado:
```bash
cd /home/levybonito/Projetos/OmniMind && npm install server-only
```

**Step 2: Adicionar `import "server-only"` como primeira linha nos arquivos listados**

Para cada arquivo, adicionar como primeira linha:
```typescript
import "server-only";
```

Exemplo para `backend/db/postgres.ts`:
```typescript
import "server-only";
import pg from "pg";
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";
// ... resto do arquivo
```

**Step 3: Verificar TypeScript + build**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -30
cd /home/levybonito/Projetos/OmniMind && npm run build 2>&1 | tail -20
```

**Step 4: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add backend/
git commit -m "feat: add server-only guards to all critical backend modules"
```

---

## Task 14: Remover diretórios `src/` que foram migrados

**Objetivo:** Após validar que tudo funciona com a nova estrutura, remover as pastas antigas de `src/` que foram migradas para `frontend/`, `backend/` e `shared/`.

**Files:**
- Delete: `src/components/`
- Delete: `src/hooks/`
- Delete: `src/stores/`
- Delete: `src/lib/`
- Delete: `src/config/`
- Delete: `src/utils/`
- Delete: `src/types/`
- Delete: `src/schemas/` (se foi criado no plano anterior)

**IMPORTANTE:** Só executar esta task após confirmar que o build passa sem erros.

**Step 1: Build final de verificação**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1
cd /home/levybonito/Projetos/OmniMind && npm run build 2>&1 | tail -30
```

Esperado: zero erros.

**Step 2: Remover diretórios migrados**

```bash
cd /home/levybonito/Projetos/OmniMind
rm -rf src/components src/hooks src/stores src/lib src/config src/utils src/types
# Remover src/schemas se existir (do plano anterior)
[ -d src/schemas ] && rm -rf src/schemas
```

**Step 3: Verificar que apenas `src/app/` permanece em `src/`**

```bash
ls src/
```

Esperado: apenas `app/` (e possivelmente `globals.css` se estiver na raiz de src).

**Step 4: Build final pós-limpeza**

```bash
cd /home/levybonito/Projetos/OmniMind && npx tsc --noEmit 2>&1 | head -30
```

**Step 5: Commit**

```bash
cd /home/levybonito/Projetos/OmniMind
git add -A
git commit -m "chore: remove migrated src/ subdirs — code now lives in frontend/, backend/, shared/"
```

---

## Task 15: Criar `.env.example` e verificação final

**Objetivo:** Documentar todas as variáveis de ambiente. Executar build e testes completos.

**Files:**
- Create/Update: `.env.example`

**Step 1: Verificar se já existe `.env.example`**

```bash
ls /home/levybonito/Projetos/OmniMind/.env* 2>/dev/null
```

**Step 2: Criar/substituir `.env.example`**

```bash
# .env.example — OmniMind Environment Variables
# Copy to .env.local and fill in your values.

# ============================================================
# Server
# ============================================================
NODE_ENV=development
PORT=3000

# ============================================================
# Database (PostgreSQL — required for conversation persistence)
# ============================================================
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/omnimind

# ============================================================
# Default LLM Provider & Model
# ============================================================
# Provider options: anthropic | openai | ollama | google | vertexai
DEFAULT_PROVIDER=vertexai
DEFAULT_MODEL=gemini-3-flash-preview
DEFAULT_TEMPERATURE=0.7
MAX_TOKENS=8192
ENABLE_STREAMING=true

# ============================================================
# LLM API Keys (leave empty to configure via Settings UI)
# ============================================================
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# ============================================================
# Google Vertex AI (alternative to GOOGLE_API_KEY)
# ============================================================
# Path to your service account JSON credentials file
VERTEXAI_CREDENTIALS_PATH=
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccount.json
GOOGLE_CLOUD_PROJECT=

# ============================================================
# Web Search (used by Agent tools)
# ============================================================
TAVILY_API_KEY=
SEARXNG_URL=http://localhost:8080

# ============================================================
# Logging
# ============================================================
LOG_LEVEL=info
```

**Step 3: Build completo**

```bash
cd /home/levybonito/Projetos/OmniMind
npx tsc --noEmit 2>&1
npm run build 2>&1 | tail -30
```

Esperado: zero erros.

**Step 4: Rodar testes (se existirem)**

```bash
cd /home/levybonito/Projetos/OmniMind && npm test 2>&1 | tail -20
```

**Step 5: Estrutura final**

```bash
find /home/levybonito/Projetos/OmniMind -maxdepth 3 \
  -not -path "*/node_modules/*" \
  -not -path "*/.next/*" \
  -not -path "*/.git/*" \
  | sort
```

**Step 6: Commit final**

```bash
cd /home/levybonito/Projetos/OmniMind
git add .env.example
git commit -m "docs: add .env.example with all config variables"
git tag -a v2.0.0-refactor -m "Architecture refactor: Option B frontend/backend/shared separation"
```

---

## Resumo das Mudanças

| Área | Antes | Depois |
|------|-------|--------|
| Componentes React | `src/components/` | `frontend/components/` |
| Hooks | `src/hooks/` | `frontend/hooks/` |
| Stores Zustand | `src/stores/agent-store.ts` | `frontend/stores/agent.store.ts` |
| Módulos do agente | `src/lib/agent/` | `backend/agent/` |
| Módulos do swarm | `src/lib/swarm/` | `backend/swarm/` |
| Database | `src/lib/db/` | `backend/db/` |
| Schemas Zod | Misturados em `types/swarm.ts` | `backend/schemas/[domain].schema.ts` |
| Config | `src/config/index.ts` (7 vars) | `backend/config/index.ts` (15+ vars) |
| Logger | `src/utils/logger.ts` | `backend/utils/logger.ts` |
| Tipos TypeScript | `src/types/` (misturado com Zod) | `shared/types/` (somente TypeScript puro) |
| `AnalystAlertLevel` | `ALERT_LEVE/MODERADO/CRITICO` (typo) | `ALERT_LOW/MODERATE/CRITICAL` |
| Validação routes | Apenas swarm validado; chat usa `as {}` | Todas as routes têm `safeParse` |
| Hardpath credenciais | `/home/levybonito/Downloads/...` | Apenas env vars |
| Server-only guards | Nenhum | Todos os módulos críticos marcados |
| `.env.example` | Ausente | Documentado completamente |

## O que NÃO muda

- Lógica dos agentes (LangGraph nodes, swarm graph, deepagents)
- UI das páginas Next.js (`src/app/*/page.tsx`)
- Estrutura das rotas de API (paths `/api/...` permanecem os mesmos)
