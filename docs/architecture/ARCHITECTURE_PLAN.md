# OmniMind Architecture Restructuring Plan (2026)

**Status:** Ready for Implementation
**Created:** 2026-02-27
**Updated:** 2026-02-27
**Target Phases:** 4 (Structure → Security Foundation → Agent System → Tool Registry)

---

## Executive Summary

### Decision: Python Backend Only
- **Backend:** Python-only (FastAPI + LangGraph + DeepAgents)
- **NO TypeScript migration** - LangGraph Python SDK is primary, DeepAgents is Python-only
- **Frontend:** Future React/Vite communicates via HTTP/SSE only - backend language irrelevant
- **Rationale:** 3,174 lines of working Python code, LangGraph SDK advantage, DeepAgents availability, ecosystem maturity

### Core Vision
- **5 Agent Personalities:** Coder, Analyst, Researcher, ArchTech, Critic (from Obsidian docs)
- **Orchestrator Layer:** Routes user requests → personality selection → LangGraph execution
- **Decomposition Thinking (DT):** Complexity-gated multi-step reasoning (Phase 3)
- **Tool Registry:** Per-agent tool scopes (filesystem, shell, web_search, code_analysis)
- **Incremental Migration:** Current code preserved, new system additive via flags

---

## Architectural Principles

### 1. Separation of Concerns
```
agents/          = WHAT (personality definitions: prompts, tools, config)
runtime/         = HOW (execution infrastructure: streaming, providers, events)
orchestrator/    = WHERE (routing: who does what when)
```

### 2. Clean Dependency Graph
```
infra ← foundation (no omnimind imports)
  ↑
schemas ← data contracts
  ↑
storage, agents, runtime
  ↑
orchestrator ← decision layer
  ↑
api ← transport layer
```

### 3. Agent as Composable Unit
Each personality is a **self-contained package**:
- System prompt (agents/prompts/)
- Tool set (agents/tools/)
- Config (thinking level, model, sandbox)
- Registered in AgentRegistry at startup

### 4. Orchestrator as Decision Engine
Single point for:
- User message analysis
- Complexity scoring
- Agent selection
- Tool scope authorization
- DT activation

---

## Target Folder Structure

```
omnimind_backend/
├── __init__.py
├── main.py                          # KEEP: FastAPI entry (add register_all_personalities())
├── agents/                          # Agent personality definitions
│   ├── __init__.py                 # Re-export: get_agent, AgentRegistry
│   ├── _base.py                    # NEW: AgentPersonality protocol, BaseAgent
│   ├── _registry.py                # NEW: AgentRegistry singleton
│   ├── personalities/
│   │   ├── __init__.py
│   │   ├── coder.py                # NEW: CoderAgent factory
│   │   ├── analyst.py              # NEW: AnalystAgent factory
│   │   ├── researcher.py           # NEW: ResearcherAgent factory
│   │   ├── arch_tech.py            # NEW: ArchTechAgent factory
│   │   └── critic.py               # NEW: CriticAgent factory
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── base.py                 # NEW: SYSTEM_PROMPT constants, prompt builder
│   │   ├── coder.py                # NEW: CODER_SYSTEM_PROMPT
│   │   ├── analyst.py              # NEW: ANALYST_SYSTEM_PROMPT
│   │   ├── researcher.py           # NEW: RESEARCHER_SYSTEM_PROMPT
│   │   ├── arch_tech.py            # NEW: ARCH_TECH_SYSTEM_PROMPT
│   │   └── critic.py               # NEW: CRITIC_SYSTEM_PROMPT
│   └── tools/
│       ├── __init__.py             # NEW: ToolRegistry, re-exports
│       ├── search_web.py           # MOVE: search_web() from agents/tools.py
│       ├── filesystem.py           # NEW: File tools (read, write, list, search)
│       ├── shell.py                # NEW: Shell execution tools (SafeBackend-wrapped)
│       └── code_analysis.py        # NEW: Code analysis tools (lint, test)
├── orchestrator/                   # Decision & routing layer
│   ├── __init__.py                # Public API: OrchestratorRuntime
│   ├── decision.py                # Re-export from schemas/orchestrator.py
│   ├── router.py                  # NEW: Message → OrchestratorDecision
│   ├── graph.py                   # NEW: LangGraph StateGraph
│   ├── complexity.py              # NEW: Complexity scorer (heuristic + LLM)
│   └── decomposition/             # Phase 3: Decomposition Thinking pipeline
│       ├── __init__.py
│       ├── classifier.py          # NEW: Classify task complexity
│       ├── decomposer.py          # NEW: Break into sub-tasks (DAG)
│       ├── scheduler.py           # NEW: Topological scheduling
│       ├── resolver.py            # NEW: Iterative component resolution
│       ├── synthesizer.py         # NEW: Final synthesis
│       └── scoring.py             # NEW: Component scoring
├── runtime/                       # Streaming infrastructure
│   ├── __init__.py
│   ├── stream.py                  # MOVE: AgentRuntime.stream_chat()
│   ├── normalizer.py              # MOVE: AgentChatStreamNormalizer
│   ├── output_categorizer.py      # MOVE: categorize_output()
│   ├── stream_event_queue.py      # MOVE: StreamEventQueue
│   ├── node_registry.py           # MOVE: NodeCategory, classify_node()
│   ├── log_bus.py                 # MOVE: AgentLogBus
│   ├── safe_backend.py            # MOVE: SafeBackend execution
│   ├── providers.py               # MOVE: get_model_for_provider()
│   └── deep_agent_factory.py      # MOVE: DeepAgents factory
├── api/
│   ├── __init__.py
│   ├── router.py                  # KEEP
│   ├── sse.py                     # KEEP
│   └── v1/
│       ├── __init__.py
│       └── agent.py               # KEEP: POST /v1/agent/chat/stream
├── schemas/
│   ├── __init__.py
│   ├── agent.py                   # KEEP + EXTEND: add thinking_mode field
│   ├── common.py                  # KEEP: LLMProvider enum
│   ├── settings.py                # KEEP
│   ├── orchestrator.py            # NEW: OrchestratorDecision, enums
│   └── decomposition.py           # NEW: DT schemas
├── storage/
│   ├── __init__.py
│   ├── db.py                      # KEEP
│   ├── models.py                  # KEEP + EXTEND: add DT models (Phase 3)
│   ├── repositories.py            # KEEP
│   ├── langgraph_checkpointer.py  # KEEP
│   └── migrations/
│       └── versions/
│           ├── 20260227_0001_initial.py
│           ├── 20260227_0002_agent_mind_refactor.py
│           └── 202602XX_0003_decomposition_thinking.py  # NEW (Phase 3)
├── infra/
│   ├── __init__.py
│   ├── config.py                  # KEEP + EXTEND (security/rate-limit settings)
│   ├── logging.py                 # EVOLVE: structured JSON + correlation
│   ├── redis.py                   # KEEP
│   ├── sanitizer.py               # NEW: input sanitization utilities (L2)
│   ├── resilience.py              # NEW: retry, circuit breaker, timeout configs
│   └── middleware/                # NEW: FastAPI middleware stack
│       ├── __init__.py
│       ├── security_headers.py    # NEW: Helmet-equivalent HTTP headers
│       ├── rate_limiter.py        # NEW: Redis-backed sliding window
│       ├── request_context.py     # NEW: X-Request-ID, correlation, timing
│       └── auth.py                # NEW: API key / JWT authentication
├── workers/
│   ├── __init__.py
│   ├── worker.py                  # KEEP
│   ├── queue.py                   # KEEP
│   └── tasks.py                   # KEEP + EXTEND: add DT jobs (Phase 3)
└── grpc/
    ├── __init__.py
    ├── server.py                  # KEEP
    ├── client.py                  # KEEP
    ├── services/
    │   ├── __init__.py
    │   └── agent_runtime_service.py  # KEEP
    ├── proto/
    └── generated/

omnimind_cli/
├── __init__.py
├── __main__.py                      # KEEP
├── app.py                           # SPLIT: just wiring (Typer root)
├── commands/                        # NEW: Command modules
│   ├── __init__.py
│   ├── chat.py                      # NEW: chat + connect commands
│   ├── health.py                    # NEW: health command
│   └── workflow.py                  # NEW: workflow run command
├── render/                          # NEW: Rendering components
│   ├── __init__.py
│   ├── chat_stream.py               # MOVE: ChatStreamRenderer from render.py
│   ├── theme.py                     # NEW: Rich theme constants
│   └── panels.py                    # NEW: Reusable Rich panels
├── client.py                        # KEEP
└── sse.py                           # KEEP

omnimind_desktop/                   # FROZEN (deprecated per ADR-0002)
├── DEPRECATED.md                   # NEW: Deprecation notice
└── [rest unchanged]

tests/
├── __init__.py
├── conftest.py                      # NEW: Shared fixtures
├── test_runtime_stream.py           # RENAME: test_agent_runtime_stream_contract.py
├── test_providers.py                # KEEP: update imports
├── test_node_registry.py            # KEEP: update imports
├── test_output_categorizer.py       # KEEP: update imports
├── test_safe_backend.py             # KEEP: update imports
├── test_stream_event_queue.py       # KEEP: update imports
├── test_schemas.py                  # KEEP
├── test_storage_models.py           # KEEP
├── test_cli_commands.py             # KEEP: update imports
├── test_orchestrator_decision.py    # NEW: OrchestratorDecision validation
├── test_agent_personalities.py      # NEW: Personality creation
├── test_agent_registry.py           # NEW: Registry operations
└── test_complexity_scorer.py        # NEW: Complexity scoring (Phase 3)
```

---

## Naming Conventions

### Files (snake_case)
```python
# Regular modules
agents/runtime.py
runtime/providers.py

# Private/internal modules (prefixed with _)
agents/_base.py
agents/_registry.py

# Prompt files
agents/prompts/coder.py
agents/prompts/analyst.py

# Tests
test_orchestrator_decision.py
test_agent_personalities.py
```

### Classes (PascalCase)
```python
# Agent personalities
class CoderAgent(BaseAgent): ...
class AnalystAgent(BaseAgent): ...

# Base classes/protocols
class AgentPersonality(Protocol): ...
class BaseAgent: ...

# Schemas
class OrchestratorDecision(BaseModel): ...
class StreamEvent(BaseModel): ...

# Enums (StrEnum for JSON)
class AgentType(StrEnum):
    CODER = "coder"
    ANALYST = "analyst"

# Services
class AgentRuntime: ...
class OrchestratorRuntime: ...
class ChatStreamRenderer: ...
```

### Module Organization (__init__.py)
- **Public API only:** Re-exports public symbols, no logic
- **Private modules:** Prefixed with `_`, never exported
- **Circular import prevention:** Avoid sibling imports at module load time

---

## Pydantic Schemas (schemas/orchestrator.py)

```python
class AgentType(StrEnum):
    CODER = "coder"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    ARCH_TECH = "arch_tech"
    CRITIC = "critic"

class ThinkingLevel(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ThinkingMode(StrEnum):
    NORMAL = "normal"
    DECOMPOSITION = "decomposition"

class ToolScope(StrEnum):
    FILESYSTEM = "filesystem"
    SHELL = "shell"
    WEB_SEARCH = "web_search"
    CODE_ANALYSIS = "code_analysis"
    DATABASE = "database"

class SandboxMode(StrEnum):
    NONE = "none"
    READ_ONLY = "read_only"
    FULL = "full"

class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class OrchestratorDecision(BaseModel):
    rationale: str                      # Why this routing decision
    agent: AgentType                    # Primary agent
    task: str                           # Reformulated task
    model: str | None                   # Model override
    thinking: ThinkingLevel             # Thinking depth
    thinking_mode: ThinkingMode         # Normal or decomposition
    tools: list[ToolScope]              # Enabled tools
    priority: Priority                  # Execution priority
    keep_context: bool                  # Maintain context
    sandbox: SandboxMode                # Sandbox level
    chain: list[ChainStep]              # Multi-agent chain
    complexity_score: float             # 0.0-1.0 (≥0.65 triggers DT)
```

---

## Agent Personality Definition Pattern

### File: agents/personalities/coder.py
```python
from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.coder import CODER_SYSTEM_PROMPT
from omnimind_backend.agents.tools import filesystem_tools, shell_tools
from omnimind_backend.schemas.orchestrator import AgentType

def create_coder_agent() -> BaseAgent:
    return BaseAgent(
        agent_type=AgentType.CODER,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=[*filesystem_tools(), *shell_tools()],
        default_model=None,
        thinking_level="HIGH",
        sandbox_enabled=True,
        keep_context=True,
    )
```

### File: agents/prompts/coder.py
```python
CODER_SYSTEM_PROMPT = """\
You are OmniMind Coder, a senior software engineer specializing in implementation.

## Core Behaviors
- Write production-quality code with proper error handling
- Follow existing project conventions and patterns
- Explain architectural decisions briefly
- Use available tools for file operations and shell commands

## Constraints
- Never modify files outside the designated workspace
- Always validate inputs before processing
- Prefer explicit over implicit code
"""
```

---

## Dependency Rules (Strict)

### Import Map (who can import whom)

```
Foundation Layer (no omnimind imports allowed):
├── infra/     (config, logging, redis)
└── schemas/   (Pydantic models)

Core Layer (import foundation only):
├── storage/   (imports schemas, infra)
├── agents/    (imports schemas, infra)
└── runtime/   (imports agents, schemas, infra, storage)

Decision Layer:
└── orchestrator/ (imports agents, runtime, schemas, infra, storage)

Transport Layer:
├── api/       (imports orchestrator, runtime, schemas, infra)
└── grpc/      (imports runtime, schemas, infra)

Client Layer:
└── omnimind_cli/ (imports ONLY schemas via HTTP)
```

### Strict Rules
1. **No circular imports:** agents ↔ runtime, agents ↔ orchestrator
2. **No upward imports:** Foundation layers never import from higher layers
3. **CLI isolated:** omnimind_cli only imports schemas.agent (for StreamEvent)
4. **No config at import time:** Use get_settings() inside functions
5. **No god modules:** Max ~300 lines per file
6. **No runtime logic in __init__.py:** Init files are for re-exports only

---

## Security & Hardening

### 1. Security Headers (Helmet Equivalent)

Middleware `infra/middleware/security_headers.py` adds defensive HTTP headers to all responses:

```python
# Headers applied:
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains  # production only
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-store  # sensitive endpoints only
```

### 2. Rate Limiting

Middleware `infra/middleware/rate_limiter.py` using Redis sliding window:

```python
# Tiers:
# Global:     100 req/min per IP
# Chat/Stream: 20 req/min per IP (LLM calls are expensive)
# gRPC:       interceptor with 50 req/min per peer
# Multi-tenant (future): per API key / user_id

class RateLimitConfig(BaseModel):
    global_limit: int = 100
    chat_stream_limit: int = 20
    window_seconds: int = 60
```

Settings in `infra/config.py`:
- `RATE_LIMIT_GLOBAL`
- `RATE_LIMIT_CHAT_STREAM`
- `RATE_LIMIT_WINDOW_SECONDS`

### 3. Authentication & Authorization

Phased approach in `infra/middleware/auth.py`:

```
Phase 1.5 — API Key (MVP):
├── Header: Authorization: Bearer <api-key>
├── Storage: table `api_keys` in PostgreSQL
├── Middleware: dependency injected per-route
└── Rate limit tied to API key instead of IP

Phase 2+ — JWT + RBAC (future):
├── JWT tokens with claims (user_id, org_id, roles)
├── Roles: admin, developer, viewer
├── Per-agent scope (access to Coder/Analyst/etc.)
└── Identity provider integration (Auth0/Keycloak/Supabase)

Phase 3+ — Multi-tenancy (future):
├── Tenant isolation via org_id in all queries
├── Row-Level Security in PostgreSQL
├── Quota management per tenant
└── Billing hooks
```

### 4. CORS Hardening

Refine defaults for production in `infra/config.py`:

```python
# Development (unchanged):
cors_allow_methods = "*"
cors_allow_headers = "*"

# Production:
cors_allow_methods = "GET,POST,OPTIONS"
cors_allow_headers = "Authorization,Content-Type,X-Request-ID"
cors_expose_headers = "X-Request-ID"
```

### 5. gRPC Security

Conditional TLS in `grpc/server.py`:

```python
if settings.app_env == "production":
    credentials = grpc.ssl_server_credentials(...)
    server.add_secure_port(f"{host}:{port}", credentials)
else:
    server.add_insecure_port(f"{host}:{port}")
```

Alternative for same-host deployments: Unix Domain Socket (`unix:///tmp/omnimind.sock`).

---

## Observability

### 1. Structured Logging

Evolve `infra/logging.py` to support dual output:

```python
# Development: Rich console (human-friendly)
# Production: JSON structured (machine-parseable)

# JSON format:
{
  "timestamp": "2026-02-27T23:12:13.456Z",
  "level": "INFO",
  "logger": "omnimind.api.agent",
  "message": "Stream chat started",
  "request_id": "req-abc123",
  "session_id": "turn-def456",
  "user_id": "usr-789",          # future multi-tenant
  "provider": "vertexai",
  "model": "gemini-3-flash",
  "duration_ms": 1234
}
```

Dependency: `structlog` (integrates with stdlib logging).

### 2. Request Context & Correlation

Middleware `infra/middleware/request_context.py`:

```python
# Responsibilities:
# 1. Generate/propagate X-Request-ID header
# 2. Store in ContextVar (accessible throughout the stack)
# 3. Log request/response with timing
# 4. Propagate to gRPC metadata for cross-service tracing

class RequestContextMiddleware:
    # On request: generate request_id, set ContextVar, log start
    # On response: add X-Request-ID header, log duration
```

### 3. Middleware Stack Order

Order matters — applied from outermost to innermost in `main.py`:

```python
# 1. RequestContextMiddleware    — generates request_id first
# 2. SecurityHeadersMiddleware   — adds security headers
# 3. RateLimiterMiddleware       — rate limit check
# 4. CORSMiddleware              — CORS (already exists)
# Auth is applied as FastAPI Depends() per-route, not as global middleware
```

---

## Resilience

### 1. Retry Logic

Module `infra/resilience.py`:

```python
class RetryConfig(BaseModel):
    max_retries: int = 3
    backoff_base: float = 1.0       # exponential: 1s, 2s, 4s
    backoff_max: float = 30.0
    retry_on_status: list[int] = [429, 500, 502, 503, 504]
    jitter: bool = True             # avoid thundering herd
```

Apply to:
- `agents/runtime.py` → `llm.ainvoke()` (most critical)
- `agents/tools.py` → `search_web()` external HTTP calls
- `grpc/client.py` → gRPC calls

Dependency: `tenacity` (mature retry library with decorator pattern).

### 2. Circuit Breaker

In `infra/resilience.py`:

```python
class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5       # failures before opening
    recovery_timeout: float = 60.0   # seconds in "open" state
    half_open_max: int = 1           # test requests in half-open
```

Apply per-provider to avoid cascading failures when one LLM provider is down.

---

## Input Sanitization

Three-layer defense model:

| Layer | What | Where | Phase |
|-------|------|-------|-------|
| **L1 — Schema** | Pydantic type/length validation | `schemas/agent.py` (✅ exists) | Done |
| **L2 — Sanitizer** | Control chars, Unicode normalization, suspicious patterns | `infra/sanitizer.py` (NEW) | 1.5 |
| **L3 — Prompt Guard** | Prompt injection detection before LLM dispatch | `agents/tools/prompt_guard.py` (NEW) | 2 |

### L2 Sanitizer (Phase 1.5)

```python
# infra/sanitizer.py
def sanitize_message(text: str) -> str:
    # 1. Strip null bytes and control chars (U+0000-U+001F except \n \t)
    # 2. Unicode NFKC normalization
    # 3. Limit markdown nesting depth
    # 4. Strip HTML tags
    # 5. Reject if matches SQL injection patterns (defense-in-depth)
    ...
```

### L3 Prompt Guard (Phase 2)

```python
# agents/tools/prompt_guard.py
def detect_injection(text: str) -> InjectionResult:
    # Heuristic patterns: "ignore previous instructions", role override, etc.
    # Score: 0.0-1.0 confidence
    # Action: warn (log) or block (reject)
    ...
```

---

## New Dependencies

| Package | Purpose | Phase |
|---------|---------|-------|
| `structlog` | Structured logging (JSON + console) | 1.5 |
| `tenacity` | Retry/backoff decorators | 1.5 |
| `python-jose[cryptography]` | JWT validation | 2+ |

---

## Migration Strategy (3 Phases)

### Phase 1: Structure (Move files, no logic changes)
**Goal:** Rearrange into target structure. All tests pass. No behavior changes.

**Steps:**
1. Create new directories (orchestrator, runtime, agents/personalities, agents/prompts, agents/tools, omnimind_cli/commands, omnimind_cli/render)
2. Move 9 execution files from agents/ → runtime/
3. Move tools.py → agents/tools/search_web.py
4. Split CLI app.py → commands/chat.py, health.py, workflow.py
5. Move render.py → render/chat_stream.py
6. Add re-export shims in old locations for backwards compatibility
7. Update all internal imports
8. Run full test suite (pytest, ruff check, mypy)
9. Remove shims after verification

**Risk:** LOW - structural only, no behavior changes

### Phase 1.5: Security Foundation (NEW)
**Goal:** Hardening basics before exposing API to multiple users. All additive — no behavior changes to existing flows.

**Task Breakdown (execute one at a time):**

#### Task 1.5.1 — Security Headers Middleware
```
Create: infra/middleware/__init__.py
Create: infra/middleware/security_headers.py
Modify: main.py (add middleware)
Create: tests/test_security_headers.py
Verify: all responses include security headers
```

#### Task 1.5.2 — Request Context & Correlation ID
```
Create: infra/middleware/request_context.py
Modify: main.py (add middleware before security headers)
Modify: infra/logging.py (add request_id to log format)
Create: tests/test_request_context.py
Verify: X-Request-ID in all responses, visible in logs
```

#### Task 1.5.3 — Structured Logging
```
Add dependency: structlog
Modify: infra/logging.py (JSON formatter for production, Rich for dev)
Modify: infra/config.py (add LOG_FORMAT setting: json|console)
Update: all existing get_logger() callsites
Create: tests/test_structured_logging.py
Verify: JSON output in production mode, human-friendly in dev
```

#### Task 1.5.4 — Rate Limiting
```
Create: infra/middleware/rate_limiter.py
Modify: infra/config.py (add rate limit settings)
Modify: main.py (add middleware)
Create: tests/test_rate_limiter.py
Verify: 429 response when limit exceeded, Redis sliding window works
```

#### Task 1.5.5 — Input Sanitization (L2)
```
Create: infra/sanitizer.py
Modify: api/v1/agent.py (apply sanitizer before processing)
Create: tests/test_sanitizer.py
Verify: control chars stripped, Unicode normalized, SQL patterns rejected
```

#### Task 1.5.6 — Retry & Circuit Breaker
```
Add dependency: tenacity
Create: infra/resilience.py
Modify: agents/runtime.py (wrap llm.ainvoke with retry)
Modify: agents/tools.py (wrap search_web with retry)
Create: tests/test_resilience.py
Verify: retry on 429/5xx, circuit opens after threshold
```

#### Task 1.5.7 — API Key Authentication
```
Create: infra/middleware/auth.py
Create: storage/migrations/versions/202602XX_api_keys.py
Modify: storage/models.py (add ApiKey model)
Modify: api/v1/agent.py (add auth dependency)
Modify: infra/config.py (add AUTH_ENABLED, AUTH_SKIP_PATHS)
Create: tests/test_auth.py
Verify: 401 without key, 200 with valid key, /health remains open
```

#### Task 1.5.8 — CORS & gRPC Hardening
```
Modify: infra/config.py (add production CORS defaults)
Modify: main.py (apply production CORS when APP_ENV=production)
Modify: grpc/server.py (conditional TLS)
Create: tests/test_cors_production.py
Verify: restricted methods/headers in production, TLS on gRPC
```

**Risk:** LOW-MEDIUM — All additive changes. Feature-flagged where applicable (`AUTH_ENABLED`, `RATE_LIMIT_ENABLED`). Existing behavior preserved when flags are off.

### Phase 2: Agent System (Add personalities + orchestrator)
**Goal:** Introduce 5 agent personalities and orchestrator routing.

**Steps:**
1. Create schemas/orchestrator.py with full OrchestratorDecision model
2. Create agents/_base.py (AgentPersonality protocol, BaseAgent)
3. Create agents/_registry.py (AgentRegistry, register_all_personalities())
4. Create all 5 personality files in agents/personalities/
5. Create all 5 prompt files in agents/prompts/
6. Create orchestrator/router.py (keyword-based initial routing)
7. Create orchestrator/graph.py (LangGraph StateGraph)
8. Wire orchestrator into runtime/stream.py via orchestrate flag
9. Call register_all_personalities() in main.py startup
10. Add comprehensive tests

**Risk:** MEDIUM - orchestrator is additive, existing flow preserved by flag

### Phase 3: Tool Registry + Decomposition Thinking
**Goal:** Formalize tool scopes and implement complexity-gated DT.

**Steps:**
1. Create agents/tools/__init__.py (ToolRegistry class)
2. Implement tool modules (filesystem, shell, code_analysis)
3. Create orchestrator/complexity.py (complexity scorer)
4. Create orchestrator/decomposition/ pipeline (5 modules)
5. Create schemas/decomposition.py (DT session/component models)
6. Add Alembic migration for DT tables
7. Add DT job types to workers/tasks.py
8. Comprehensive DT tests

**Risk:** MEDIUM-HIGH - DT is complex, gate behind thinking_mode flag

---

## Success Criteria

### Phase 1 (Structure)
- ✅ All existing tests pass
- ✅ No import errors
- ✅ mypy passes (strict mode)
- ✅ ruff lint passes
- ✅ No behavior changes to API/CLI

### Phase 1.5 (Security Foundation)
- ✅ All Phase 1 tests pass + new security tests
- ✅ Security headers present in all HTTP responses
- ✅ X-Request-ID generated and propagated in logs
- ✅ Structured JSON logging in production mode
- ✅ Rate limiting enforced on `/v1/agent/chat/stream` (429 on excess)
- ✅ Input sanitization strips control chars and normalizes Unicode
- ✅ LLM calls retry on transient failures (429, 5xx)
- ✅ Circuit breaker opens after failure threshold
- ✅ API key authentication rejects unauthenticated requests
- ✅ `/health` remains open without authentication
- ✅ CORS restricted in production mode
- ✅ gRPC uses TLS in production mode
- ✅ All security features are feature-flagged (safe rollback)

### Phase 2 (Agent System)
- ✅ All Phase 1 + 1.5 tests + new tests pass
- ✅ 5 personalities register correctly
- ✅ orchestrate=False path unchanged (backwards compatible)
- ✅ orchestrate=True path works end-to-end
- ✅ Orchestrator decision schema validates correctly

### Phase 3 (Tool Registry + DT)
- ✅ All previous tests pass
- ✅ Tool registry works with per-agent scopes
- ✅ Complexity scorer gates DT activation correctly (≥0.65)
- ✅ DT pipeline decomposes tasks into DAG
- ✅ Component resolution loop works iteratively
- ✅ Final synthesis produces coherent output

### Overall
- ✅ 85%+ code coverage (core modules)
- ✅ No breaking API/CLI changes
- ✅ All conventions followed (naming, imports, dependencies)
- ✅ Zero circular imports
- ✅ Type safety maintained
- ✅ Security baseline verified (headers, auth, rate limit, logging)

---

## Next Steps

1. **User approval:** Review this plan, identify concerns
2. **Setup worktree:** Isolated branch for implementation (superpowers:using-git-worktrees)
3. **Execute Phase 1:** File moves + re-export shims
4. **Execute Phase 1.5:** Security foundation (8 tasks, one at a time)
5. **Execute Phase 2:** Agent personalities + orchestrator
6. **Execute Phase 3:** Tool registry + DT (if approved)
7. **Final verification:** Full test suite + manual testing
8. **Merge & deploy:** Clean up worktree, merge to master

---

**Plan Status:** Updated with Security & Observability — Ready for Architect Review & Approval ✓
**ADR:** `docs/adr/0003-security-hardening-foundation.md`
