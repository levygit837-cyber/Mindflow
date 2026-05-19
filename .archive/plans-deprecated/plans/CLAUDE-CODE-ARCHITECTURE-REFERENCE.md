# Claude Code CLI — Referência Arquitetural para MindFlow

> **Objetivo:** Documentar os padrões arquiteturais do Claude Code CLI (1.903 arquivos, ~231K linhas TypeScript) como referência para implementação dos serviços do MindFlow.

---

## 1. Visão Geral do Sistema

### Arquitetura de Alto Nível

```
┌──────────────────────────────────────────────────────────┐
│                    Interactive TUI (Ink/React)            │
│  ┌──────────┐  ┌───────────┐  ┌─────────────────────┐   │
│  │ REPL.tsx  │  │ AppState  │  │ Message Queue       │   │
│  └─────┬────┘  └─────┬─────┘  └──────────┬──────────┘   │
│        └──────────────┼──────────────────┘                │
└───────────────────────┼──────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────┐
│              Query Layer                                 │
│  ┌───────────────────┼─────────────┐                     │
│  │  QueryEngine.ts    │             │                     │
│  │     (turn loop)    │             │                     │
│  └──────────┬─────────┘             │                     │
│             │                       │                     │
│  ┌──────────┼─────────────────────┐ │                     │
│  │   query.ts  (streaming loop)   │ │                     │
│  └──────────┬─────────────────────┘ │                     │
└─────────────┼───────────────────────┼─────────────────────┤
              │                       │
┌─────────────┼───────────────────────┼─────────────────────┐
│    Tool Execution Layer             │                     │
│  ┌──────────┼──────────┐  ┌────────┼───────────┐        │
│  │ 60+ Built-in Tools │  │  MCP   │  Tools    │        │
│  │ Bash/Read/Edit/    │  │ Server │  (dynamic)│        │
│  │ Agent/Search/etc   │  │ Connect│           │        │
│  └──────────┬─────────┘  └────────┴───────────┘        │
└─────────────┼────────────────────────────────────────────┘
              │
┌─────────────┼────────────────────────────────────────────┐
│    Task/Agent Layer                  │                    │
│  ┌──────────┐ ┌───────────┐ ┌───────┼──────────┐        │
│  │LocalAgent│ │RemoteAgent│ │LocalShell│ Tasks   │       │
│  │Task      │ │Task       │ │Task      │ (bg)   │       │
│  └──────────┘ └───────────┘ └────────┴──────────┘       │
│  ┌──────────────────────────────────────┐                │
│  │ Coordinator Mode (distribute work)   │                │
│  └──────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────┘
```

### Componentes Principais

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| **Entry Point** | `main.tsx` (804KB) | CLI setup, commander.js parser, mode detection, REPL launch |
| **Query Engine** | `QueryEngine.ts` (47KB) | Turn loop — cada chamada `submitMessage()` é um turno da conversa |
| **Query Loop** | `query.ts` | Streaming loop — chama o modelo, executa ferramentas, gerencia contexto |
| **Tool Registry** | `Tool.ts` (30KB) | Interface de ferramenta, type system, `buildTool()` factory |
| **Tool Pool** | `tools.ts` | Assembly do pool de ferramentas, filtering, presets |
| **Commands** | `commands.ts` (25KB) | Sistema de comandos slash (`/help`, `/compact`, etc.) |
| **Task System** | `Task.ts` (3KB) | Tipos de tarefa, IDs, estados |
| **Context** | `context.ts` (6KB) | System prompt injection (git status, CLAUDE.md, date) |
| **Setup** | `setup.ts` | Inicialização do ambiente (cwd, hooks, worktree, terminal backup) |

---

## 2. Tool System — Arquitetura Detalhada

### 2.1 Interface Tool (Tool.ts)

Cada ferramenta implementa a interface `Tool<Input, Output, Progress>`:

```typescript
type Tool<Input, Output, Progress> = {
  name: string                    // Nome único (ex: "Bash", "Read")
  aliases?: string[]              // Nomes alternativos para compatibilidade
  description: (input, context) => Promise<string>  // Descrição para o modelo
  call: (args, context, canUseTool, parentMsg, onProgress) => Promise<ToolResult<Output>>
  inputSchema: z.ZodType<Input>   // Schema Zod para validação
  outputSchema?: z.ZodType<Output>
  
  // Permission & Safety
  checkPermissions: (input, context) => Promise<PermissionResult>
  validateInput?: (input, context) => Promise<ValidationResult>
  isConcurrencySafe: (input) => boolean   // Pode rodar em paralelo?
  isReadOnly: (input) => boolean          // Opera sem side-effects?
  isDestructive?: (input) => boolean      // Operação irreversível?
  isOpenWorld?: (input) => boolean        // Resultado imprevisível?
  
  // Deferral (ToolSearch)
  shouldDefer?: boolean           // ToolSearch required antes de usar
  alwaysLoad?: boolean            // Nunca deferir (sempre visível)
  strict?: boolean                // Strict mode para prompt instructions
  
  // UI Rendering (REPL/TUI)
  renderToolUseMessage: (input, opts) => React.ReactNode
  renderToolResultMessage?: (output, progress, opts) => React.ReactNode
  renderToolUseProgressMessage?: (progress[], opts) => React.ReactNode
  renderToolUseRejectedMessage?: (input, opts) => React.ReactNode
  renderToolUseErrorMessage?: (error, opts) => React.ReactNode
  renderToolUseQueuedMessage?: () => React.ReactNode
  renderGroupedToolUse?: (toolUses[], opts) => React.ReactNode | null
  
  // Display
  userFacingName: (input?) => string
  getToolUseSummary?: (input?) => string | null
  getActivityDescription?: (input?) => string | null  // Para spinner
  renderToolUseTag?: (input?) => React.ReactNode  // Tag adicional
  
  // Advanced
  interruptBehavior?: () => 'cancel' | 'block'  // Comportamento no interrupt
  preparePermissionMatcher?: (input) => Promise<(pattern: string) => boolean>
  getPath?: (input) => string     // Para ferramentas que operam em arquivos
  toAutoClassifierInput: (input) => unknown  // Para security classifier
  backfillObservableInput?: (input) => void   // Para hooks/transcript
  extractSearchText?: (output) => string      // Para busca em transcript
}
```

### 2.2 Tool Factory Pattern

```typescript
// Padrão buildTool() — preenche defaults automaticamente
const TOOL_DEFAULTS = {
  isEnabled: () => true,
  isConcurrencySafe: () => false,   // Assume não-seguro por padrão
  isReadOnly: () => false,          // Assume escrita por padrão
  isDestructive: () => false,
  checkPermissions: (input) => ({ behavior: 'allow', updatedInput: input }),
  toAutoClassifierInput: () => '',
  userFacingName: () => this.name,
}

// Uso: todas as 60+ ferramentas usam buildTool()
export const BashTool = buildTool({
  name: 'Bash',
  inputSchema: z.object({ command: z.string(), description: z.string() }),
  call: async (args, context, canUseTool, parentMsg, onProgress) => { ... },
  description: async (input) => { ... },
  // ... overrides dos defaults
})
```

### 2.3 Tool Pool Assembly (tools.ts)

O pool de ferramentas é montado em camadas:

```
getAllBaseTools() → ~60 ferramentas built-in
    │
    ├── Feature flags (feature(), env vars)
    ├── Permission context (filterToolsByDenyRules)
    ├── Mode filtering (simple/coordinator/repl)
    └── isEnabled() check
         │
         ├── getTools(permissionContext) → built-in tools
         ├── MCP tools (dynamic, from servers)
         └── SkillTool, AgentTool (conditional)
              │
              └── assembleToolPool(builtIn, mcpTools) → pool final
```

### 2.4 Lista Completa de Ferramentas

| Ferramenta | Tipo | ReadOnly | Concurrency | Descrição |
|-----------|------|----------|-------------|-----------|
| AgentTool | Agent spawn | No | Yes | Spawn subagents (sync/async/teammate) |
| BashTool | Shell | No* | Yes | Executar comandos shell com sandbox |
| FileReadTool | File | Yes | Yes | Ler arquivos com cache |
| FileEditTool | File | No | No | Editar arquivos (diff apply) |
| FileWriteTool | File | No | No | Escrever/criar arquivos |
| GrepTool | Search | Yes | Yes | Busca regex com ripgrep |
| GlobTool | Search | Yes | Yes | Pattern matching com glob |
| WebFetchTool | Network | Yes | No | Fetch URLs/web content |
| WebSearchTool | Network | Yes | No | Busca na web |
| TodoWriteTool | State | No | No | Gerenciar todo list |
| NotebookEditTool | File | No | No | Editar Jupyter notebooks |
| ExitPlanModeV2Tool | Mode | No | No | Sair do plan mode |
| EnterPlanModeTool | Mode | No | No | Entrar no plan mode |
| TaskStopTool | Task | No | Yes | Parar tarefa em execução |
| TaskOutputTool | Task | Yes | Yes | Output de tarefa |
| AskUserQuestionTool | UI | Yes | No | Perguntar ao usuário |
| SkillTool | Skill | Yes | No | Invocar skills do diretório |
| ToolSearchTool | Search | Yes | No | Descobrir ferramentas disponíveis |
| ConfigTool | Config | No | No | Gerenciar configurações (ant) |
| TungstenTool | Debug | No | No | Debug/inspeção (ant) |
| LSPTool | LSP | Yes | No | Language Server Protocol |
| ListMcpResourcesTool | MCP | Yes | Yes | Listar recursos MCP |
| ReadMcpResourceTool | MCP | Yes | No | Ler recurso MCP |
| SleepTool | Control | Yes | Yes | Pausar execução (proactive mode) |
| BriefTool | Brief | Yes | No | Gerar briefing document |

### 2.5 Tool Execution Pipeline

```
Model response with tool_use blocks
    │
    ├── StreamingToolExecutor.addTool(toolBlock, assistantMsg)
    │   ├── Queue tool for parallel execution
    │   ├── Apply permission checks (canUseTool)
    │   │   ├── Step 1a: Check deny rules (always-deny)
    │   │   ├── Step 1b: Run validateInput()
    │   │   ├── Step 2: Check permission mode (auto/plan/bypass)
    │   │   ├── Step 3: Run checkPermissions()
    │   │   ├── Step 4: Run hooks (PreToolUse)
    │   │   └── Step 5: Ask user if needed
    │   └── Execute tool.call()
    │       ├── Progress updates (onProgress)
    │       └── Return ToolResult<Output>
    │
    └── StreamingToolExecutor.getCompletedResults()
        └── Yield UserMessage with tool_result blocks
```

### 2.6 Permission System (4 camadas)

```
┌─────────────────────────────────────────────────┐
│ Permission Mode                                  │
│  auto  → classifier + hooks (no prompt)          │
│  plan  → model decides                         │
│  default → user asked per tool                  │
│  bypassPermissions → all allowed               │
└─────────────────────────────────────────────────┘
    │
┌───┼─────────────────────────────────────────────┐
│   ▼                                             │
│ Permission Rules (from settings)                │
│  alwaysAllowRules: { "Bash(git *)": {...} }     │
│  alwaysDenyRules:  { "Bash(rm -rf /)": {...} }  │
│  alwaysAskRules:   { "Bash(curl *)": {...} }    │
└───┼─────────────────────────────────────────────┘
    │
┌───┼─────────────────────────────────────────────┐
│   ▼                                             │
│ Tool-Level Check                                │
│  tool.checkPermissions(input, context)          │
│  → { behavior: 'allow' | 'deny' | 'ask',        │
│      updatedInput?, reason? }                   │
└───┼─────────────────────────────────────────────┘
    │
┌───┼─────────────────────────────────────────────┐
│   ▼                                             │
│ Hooks                                           │
│  PreToolUse hook → can block/modify             │
│  PostToolUse hook → observe/audit               │
└──────────────────────────────────────────────────┘
```

---

## 3. Query Loop — Arquitetura Detalhada

### 3.1 QueryEngine.ts — Turn Loop

```
QueryEngine.submitMessage(prompt):
    │
    ├── 1. Build system prompt (customSystemPrompt + memoryMechanicsPrompt)
    ├── 2. Process user input (slash commands, attachments)
    ├── 3. Push messages to mutableMessages[]
    ├── 4. Persist transcript (recordTranscript)
    ├── 5. Build ToolPermissionContext from allowedTools
    ├── 6. Load skills/plugins (getSkills(), loadAllPluginsCacheOnly())
    ├── 7. Yield system init message (SDK)
    ├── 8. Call query() generator:
    │    │
    │    ├── for await (message of query({ ... })):
    │    │   │
    │    │   ├── yield message to SDK/REPL
    │    │   ├── Track usage, permission denials
    │    │   ├── Check budget limits
    │    │   └── Handle compaction boundaries
    │    │
    │    └── query() retorna quando stop_reason !== 'tool_use'
    │
    ├── 9. Yield final result message (SDK)
    └── 10. Return (session continues)
```

### 3.2 query.ts — Streaming Loop

```
query({ messages, systemPrompt, tools, canUseTool, ... }):
    │
    └── while (true):
         │
         ├── Setup iteration:
         │   ├── Decompress state (messagesForQuery)
         │   ├── Apply tool result budget (applyToolResultBudget)
         │   ├── Apply snip compact (if HISTORY_SNIP)
         │   ├── Apply microcompact (cache-based)
         │   ├── Apply context collapse (if CONTEXT_COLLAPSE)
         │   └── Build full system prompt
         │
         ├── Auto-compact check:
         │   ├── Calculate token count
         │   ├── If near blocking limit → run auto-compact
         │   ├── Build post-compact messages
         │   └── Yield compact boundary messages
         │
         ├── API call (streaming):
         │   └── for await (message of deps.callModel({ ... })):
         │       │
         │       ├── 'assistant' → push to assistantMessages[]
         │       │   └── If tool_use blocks found → set needsFollowUp=true
         │       ├── 'stream_event' → track usage (message_delta)
         │       └── Handle streaming fallback (model overload)
         │
         ├── Post-sampling hooks (executePostSamplingHooks)
         │
         ├── Tool execution:
         │   ├── If streamingToolExecutor: getRemainingResults()
         │   ├── Else: runTools(toolUseBlocks, canUseTool, toolUseContext)
         │   │   │
         │   │   └── for each tool in parallel:
         │   │       ├── canUseTool(tool, input, context)
         │   │       ├── tool.call(args, context, ...)
         │   │       ├── Progress updates
         │   │       └── Return ToolResult
         │   │
         │   └── Normalize messages for API (normalizeMessagesForAPI)
         │
         ├── Attachment processing:
         │   ├── Process queued commands as attachments
         │   ├── Process file change events
         │   ├── Process memory prefetch results
         │   └── Process skill discovery results
         │
         ├── Continue/Return decision:
         │   ├── If needsFollowUp (tool_use found):
         │   │   ├── Build next state
         │   │   ├── Check maxTurns limit
         │   │   └── continue (recurse)
         │   │
         │   ├── If noFollowUp (model finished):
         │   │   ├── Handle stop hooks (handleStopHooks)
         │   │   │   ├── If blocking errors → continue with error injected
         │   │   │   └── If continuation prevented → return
         │   │   ├── Check token budget (if TOKEN_BUDGET)
         │   │   │   └── If under budget → continue with nudge message
         │   │   └── return { reason: 'completed' }
         │
         └── Return terminal event
```

### 3.3 Recovery Patterns

| Pattern | Trigger | Recovery | Max Attempts |
|---------|---------|----------|-------------|
| **Streaming Fallback** | Model overload | Switch to fallbackModel | 1 per turn |
| **Max Output Tokens** | Token limit hit | Inject "resume directly" message | 3 attempts |
| **OTK Escalation** | 8k default limit | Retry with 64k max | 1 per turn |
| **Prompt Too Long** | 413 error | Drain context collapses → reactive compact | 1 each |
| **Media Size Error** | Image too large | Reactive compact (strip + retry) | 1 attempt |
| **Stop Hook Blocking** | Hook injects error | Continue with error message | ∞ (circuit breaker) |
| **Token Budget** | Budget exhausted | Injection nudge message | Configurable |

---

## 4. Command/Skill System

### 4.1 Command Types

```typescript
type Command = PromptCommand | LocalCommand | LocalJSXCommand

// Prompt Command → expande para texto de prompt
{
  type: 'prompt',
  name: 'skill-name',
  description: 'What this skill does',
  getPromptForCommand(args, context): Promise<string>,
  loadedFrom: 'skills' | 'plugin' | 'bundled' | 'mcp',
  disableModelInvocation?: boolean,  // Não enviar para o modelo
  allowedTools?: string[],           // Tools restricted
  context?: 'inline' | 'fork',       // How it runs
  agent?: string,                    // Which agent uses it
}

// Local Command → output de terminal
{
  type: 'local',
  name: 'version',
  description: 'Show version',
  async run(args, context): Promise<string>,
  supportsNonInteractive: true,
}

// Local JSX Command → Ink UI
{
  type: 'local-jsx',
  name: 'skills',
  description: 'List skills',
  async load(): Promise<{ default: (props) => React.ReactNode }>,
}
```

### 4.2 Skill System

```
Skill Loading Pipeline:
    │
    ├── Bundled Skills (src/skills/bundled/)
    │   └── Registered at startup (<1ms, in-memory)
    │
    ├── Skill Directory (.claude/skills/, project-level)
    │   └── loadSkillsDir(cwd) → file scan + SKILL.md parse
    │
    ├── Plugin Skills
    │   └── loadPluginSkills() → from installed plugins
    │
    └── MCP Skills
        └── From MCP server prompts/commands

Skill Discovery:
    ├── SkillTool → model can search skills by name/description
    ├── services/skillSearch/ → local search index
    └── startSkillDiscoveryPrefetch() → background prefetch during model streaming
```

### 4.3 100+ Comandos Built-in

Principais categorias:

- **Session**: /resume, /continue, /cost, /session, /share
- **Configuration**: /model, /effort, /theme, /color, /config, /settings
- **Git**: /commit, /review, /pr-comments
- **MCP**: /mcp (list, add, remove, get)
- **Help**: /help, /doctor, /status
- **Utility**: /vscode, /vscode-insiders, /v im, /clear, /exit

---

## 5. Agent/Subagent System

### 5.1 Tipos de Agentes

```
Agent Definitions:
    ├── Built-in Agents (definidos em código)
    │   ├── code_reviewer
    │   ├── planner
    │   └── ... outros
    │
    ├── Custom Agents (do usuário)
    │   ├── .claude/agents/*.json ou .md
    │   │   └── { name, description, model, prompt }
    │   └── --agents flag (JSON inline)
    │
    └── Dynamic Agents (spawned)
        ├── AgentTool → spawn subagent
        └── Fork → clone conversation state
```

### 5.2 Subagent Execution

```
AgentTool.call({ name, prompt, model?, ... }):
    │
    ├── Resolve agent definition
    │   ├── Check built-in, custom, CLI agents
    │   └── Apply model/prompt overrides
    │
    ├── Execution path selection:
    │   ├── Sync path (short-lived agent):
    │   │   └── Create child QueryEngine → run in same process
    │   │
    │   ├── Async path (long-lived agent):
    │   │   └── Register as LocalAgentTask → background execution
    │   │
    │   ├── Fork path (clone current conversation):
    │   │   └── Copy messages, file cache, continue with new prompt
    │   │
    │   └── In-process teammate (swarm mode):
    │       └── Shared state, no isolation
    │
    ├── Isolation:
    │   ├── File state (clone parent's readFileState)
    │   ├── Permission context (may differ from parent)
    │   └── Memory (agent-specific memory scope)
    │
    └── Result collection:
        ├── Sync → return directly
        └── Async → TaskOutputTool → poll for result
```

### 5.3 Task System

```typescript
type TaskType =
  | 'local_bash'       // Shell command background task
  | 'local_agent'      // Local subagent
  | 'remote_agent'     // Remote CCR session
  | 'in_process_teammate' // Swarm teammate
  | 'local_workflow'   // Workflow script
  | 'monitor_mcp'      // MCP monitoring
  | 'dream'            // Background ideation

type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'killed'

// Task IDs: prefix + 8 random chars
// b1a2b3c4 (bash), a5d6e7f8 (agent), r9g0h1i2 (remote), etc.
```

### 5.4 Coordinator Mode

```
Coordinator Mode (COORDINATOR_MODE feature flag):
    │
    ├── Coordinator agent (main thread)
    │   ├── Creates tasks for workers
    │   ├── Uses TaskCreateTool to delegate
    │   └── Monitors completion via TaskOutputTool
    │
    ├── Worker agents (spawned subagents)
    │   ├── Each gets specific task
    │   ├── Filtered tool pool (TaskStop, SendMessage only)
    │   └── Results reported back to coordinator
    │
    └── Allowed tools: COORDINATOR_MODE_ALLOWED_TOOLS
        ├── TaskStopTool
        ├── SendMessageTool
        └── ... limited set
```

---

## 6. Context/Compaction Management

### 6.1 Token Budget Strategies

```
┌────────────────────────────────────────────────────┐
│ Context Window Management                           │
│                                                    │
│ 1. Microcompact (fast, cache-based)                │
│    - Remove old tool results from cache            │
│    - ~0ms latency, preserves context               │
│                                                    │
│ 2. Auto-Compact (model-based summarization)        │
│    - Haiku model summarizes old turns              │
│    - ~1-2s latency, keeps system prompt + recent   │
│    - Triggered at token threshold                   │
│    - Circuit breaker on consecutive failures       │
│                                                    │
│ 3. Reactive Compact (error-based)                  │
│    - Triggered by prompt-too-long (413 error)      │
│    - Strip tool results, compact, retry            │
│    - Single-shot (no spiral)                       │
│                                                    │
│ 4. Context Collapse (CONTEXT_COLLAPSE)             │
│    - Staged collapse of old turns                   │
│    - Drain on recovery before reactive compact     │
│                                                    │
│ 5. Snip (HISTORY_SNIP)                             │
│    - Yield system message for snipped history      │
│    - Project-based view on full history            │
│                                                    │
│ Blocking Limit (hard cap):                         │
│  - Reserve ~10K tokens for user commands           │
│  - Skip check if compact just ran (no staleness)   │
└────────────────────────────────────────────────────┘
```

### 6.2 Tool Result Budget

```
Tool Result Storage System:
    ├── Aggregate budget per message (not per tool)
    ├── Content replacement: large results → file reference
    ├── Persist to sessionStorage (resume support)
    ├── Clone for subagents (inherit parent's replacements)
    └── Applied BEFORE microcompact (invisible to cache)
```

---

## 7. State Management

### 7.1 AppState (Redux-like Store)

```typescript
type AppState = {
  // Authentication/Authz
  auth: { token, org, subscription }

  // Tools
  toolPermissionContext: {
    mode: PermissionMode,
    alwaysAllowRules,
    alwaysDenyRules,
    alwaysAskRules,
    ...
  }

  // MCP
  mcp: {
    clients: MCPClient[],
    tools: Tool[],
    commands: Command[],
    resources: { [serverName]: Resource[] }
  }

  // Model
  mainLoopModel: string
  fastMode: boolean

  // Tasks
  tasks: { [taskId]: TaskState }

  // UI
  verbose: boolean
  expandedView: 'none' | 'tasks' | 'teammates'
  notifications: { queue: Notification[] }

  // Memory
  fileHistory: { snapshots, trackedFiles }
  attribution: { commits, branches }
}

// Store API
const store = createStore(initialState, onChangeAppState)
store.getState()
store.setState(prev => ({ ...prev, ...updates }))
```

### 7.2 Session Storage

```
Session Transcript (JSONL):
    ├── ~/.claude/projects/<cwd>/sessions/<id>.jsonl
    ├── One JSON line per message
    ├── Append-only (recordTranscript)
    ├── Buffered writes (100ms lazy stringify)
    └── Flush on result message (before exit)

Session Cost/Usage:
    ├── Persisted to project config (settings.json)
    ├── Restored on --continue/--resume
    └── Includes: cost, tokens, duration, FPS
```

---

## 8. Hooks System

```typescript
// Hook Types
type Hook = {
  trigger: 'SessionStart' | 'Setup' | 'Stop' | 'UserPromptSubmit' |
           'PreToolUse' | 'PostToolUse' | 'Compaction' | ...,
  if?: {
    hookName?: string,
    toolName?: string,       // "Bash(git *)" pattern
    toolType?: string,
    ...
  },
  run?: string,              // Shell command
  prompt?: string,           // Prompt injection
  ...
}

// Hook Execution
processSessionStartHooks('startup', { agentType, model })
    ├── For each hook:
    │   ├── Run shell command (if configured)
    │   ├── Inject prompt (if configured)
    │   └── Record metrics
    └── Return blocking error messages (if any)

processStopHooks(messages, toolUseContext)
    ├── Prevent continuation (if hook_stopped_continuation)
    └── Inject blocking error messages
```

---

## 9. MCP Integration

### 9.1 MCP Client Architecture

```
MCP Server Config Sources:
    ├── .mcp.json (project-level)
    ├── settings.json (user/project/local)
    ├── --mcp-config flag (CLI)
    ├── Plugin MCP servers
    └── claude.ai proxy servers (Gmail, Slack, BigQuery, etc.)

MCP Server Types:
    ├── stdio (subprocess)
    ├── SSE (HTTP endpoint)
    ├── http (Streamable HTTP)
    ├── websocket
    └── sdk (passed from SDK caller)

MCP Tool Registration:
    ├── Tools → added to appState.mcp.tools
    ├── Resources → added to appState.mcp.resources
    ├── Commands → added to appState.mcp.commands
    └── Each with mcpInfo: { serverName, toolName }

MCP Lifecycle:
    ├── Prefetch at startup (connect all servers)
    ├── Reconnect on settings change (hot reload)
    └── Policy enforcement (enterprise MCP config overrides)
```

### 9.2 MCP Dedup

```
MCP Tool Deduplication:
    ├── Built-in tools take precedence over MCP tools
    ├── Enterprise MCP config → blocks dynamic MCP configs
    ├── claude.ai servers dedup against manual servers (URL signature)
    └── Plugin MCP servers dedup against claude.ai connectors
```

---

## 10. Analytics/Telemetry

```
Events (Statsig/Datadog):
    ├── tengu_started — process started
    ├── tengu_timer — performance metrics
    ├── tengu_query_error — query failures
    ├── tengu_model_fallback_triggered — model fallback
    ├── tengu_auto_compact_succeeded — auto-compact metrics
    ├── tengu_worktree_created — worktree usage
    ├── tengu_exit — previous session summary
    └── ... 100+ events

Session Identification:
    ├── Session ID (UUID per conversation)
    ├── Query chain ID (links recursive queries)
    └── Project root (multi-project tracking)
```

---

## 11. Padrões de Design Extratos para MindFlow

### 11.1 Tool Orchestration Pattern

**Problema:** Executar N ferramentas em paralelo e coletar resultados.

**Solução do Claude:**

```
1. StreamingToolExecutor → queue tools as they stream
2. Parallel execution → canUseTool checks first
3. Progress updates → yield during execution
4. Result normalization → strip thinking/redacted blocks
5. Continuation → model gets all tool_results and continues
```

**Aplicação ao MindFlow:** MissionLauncher + TeamOrchestrator devem usar o mesmo pattern de queue → execute → collect → continue.

### 11.2 Permission System Pattern

**Problema:** Controle granular de permissões sem bloquear a experiência.

**Solução do Claude:**

```
Permission Mode → Rules → Tool Check → Hooks → User Prompt
    (gate)      (cache)   (specific)   (policy)  (last resort)
```

**Aplicação ao MindFlow:** Sistema de permissões para missões — quais ferramentas um agente pode usar, quais recursos acessar.

### 11.3 Query Loop Pattern

**Problema:** Manter uma conversa com múltiplos turnos de ferramenta.

**Solução do Claude:**

```
while (true):
    → Model call
    → If tool_use → execute tools → continue
    → If done → stop hooks → return
```

**Aplicação ao MindFlow:** O RuntimeRouter deve usar este pattern para execução de agentes.

### 11.4 Compaction Pattern

**Problema:** Gerenciar contexto limitado do modelo.

**Solução do Claude:**

```
Multiple layers:
1. Microcompact (fast, cache-only)
2. Auto-Compact (model summarization)
3. Reactive Compact (error recovery)
4. Context Collapse (staged drain)

Each layer has specific triggers, costs, and fallbacks.
```

**Aplicação ao MindFlow:** Memory system deve ter estratégias similares de compactação.

### 11.5 State Management Pattern

**Problema:** Estado compartilhado entre componentes assíncronos.

**Solução do Claude:**

```
Redux-like store:
  - Immutable snapshots
  - Functional updates (setState(fn))
  - Selective rendering via selectors
  - External store (no React dependency)
```

**Aplicação ao MindFlow:** Runtime/Orchestrator devem usar o mesmo pattern para manter agente/missão/estado de equipe.

---

## 12. Referências de Arquivos

### Core (Root Level)

- `main.tsx` — CLI entry point, commander.js setup, REPL launch
- `QueryEngine.ts` — Turn loop, submitMessage()
- `query.ts` — Streaming loop, tool execution orchestration
- `Tool.ts` — Tool interface type, buildTool() factory
- `tools.ts` — Tool pool assembly, getTools(), assembleToolPool()
- `Task.ts` — Task types, IDs, states
- `commands.ts` — Command registry, skill/tool loading
- `history.ts` — Command history, prompt storage
- `context.ts` — System context (git, CLAUDE.md, date)
- `cost-tracker.ts` — Token cost tracking
- `setup.ts` — Environment initialization

### Key Directories

- `src/tools/` — 60+ tool implementations
- `src/commands/` — 100+ slash commands
- `src/services/` — API, MCP, analytics, compaction
- `src/state/` — AppState types and store
- `src/tasks/` — Task implementations
- `src/hooks/` — Hook system
- `src/components/` — React UI components
- `src/screens/` — Main REPL screen
- `src/utils/` — 400+ utility modules
- `src/bootstrap/` — App initialization state
- `src/memory/` — Memory systems
- `src/memory/` — Shared memory retrieval
