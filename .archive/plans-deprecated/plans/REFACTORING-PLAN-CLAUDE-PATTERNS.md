# Plano de Refatoração: MindFlow → Claude Code Patterns

**Data:** 2026-03-31  
**Objetivo:** Migrar MindFlow para padrões enterprise-level do Claude Code CLI mantendo funcionalidades existentes

---

## 📊 Análise Comparativa

### MindFlow (Estado Atual)

**Pontos Fortes:**

- ✅ Sistema Multi-Agente (SPADE/XMPP)
- ✅ CommunicationBus (InternalBus + XMPPBus)
- ✅ Persistência Universal (PostgreSQL + pgvector)
- ✅ Runtime modular (streaming, execution, routing)
- ✅ Missões e Fluxos Agênticos
- ✅ Memória (session, project, shared)
- ✅ LangGraph integration

**Gaps Críticos:**

- ❌ Sistema de Permissões formal
- ❌ Sistema de Hooks
- ❌ QueryEngine para contexto
- ❌ Sistema de Comandos
- ❌ Loops/Cron
- ❌ Gerenciamento de Tasks robusto
- ❌ Tool system maduro (em refatoração)

### Claude Code CLI (Referência)

**Padrões Enterprise:**

- ✅ QueryEngine sofisticado (context management)
- ✅ Permission system granular
- ✅ Hooks system (PreToolUse, PostToolUse, Stop)
- ✅ Task management (local_bash, local_agent, remote_agent, etc.)
- ✅ Command system (80+ comandos)
- ✅ Tool orchestration avançado
- ✅ MCP integration
- ✅ Agent sub-agents pattern
- ✅ Loops/Cron scheduling
- ✅ Memory management (memdir)

---

## 🎯 Estratégia de Migração

### Princípios

1. **Gradual, não Big Bang** - Implementar em fases incrementais
2. **Preservar o Core** - Manter CommunicationBus, Persistência, Missões
3. **Adaptar, não Copiar** - Traduzir padrões TS→Python idiomaticamente
4. **Testes Contínuos** - 80%+ coverage em cada fase
5. **Backward Compatibility** - Manter APIs existentes durante transição

---

## 📋 Fases de Implementação

## FASE 1: Fundação - Permission System & Context Management

**Prioridade:** CRÍTICA  
**Duração:** 2-3 semanas  
**Objetivo:** Estabelecer controle de segurança e gerenciamento de contexto

### 1.1 Permission System

**Arquivos de Referência (Claude Code):**

- `src/types/permissions.ts` - Tipos de permissão
- `src/hooks/toolPermission/` - Handlers de permissão
- `src/utils/permissions/` - Lógica de permissão

**Implementação MindFlow:**

```
python/mindflow_backend/
├── permissions/
│   ├── __init__.py
│   ├── types.py              # PermissionMode, PermissionResult
│   ├── manager.py            # PermissionManager
│   ├── handlers/
│   │   ├── tool_handler.py   # Tool permission logic
│   │   ├── file_handler.py   # File access permissions
│   │   └── bash_handler.py   # Command execution permissions
│   └── policies/
│       ├── default.py        # Default permission policies
│       └── custom.py         # User-defined policies
```

**Tarefas:**

- [ ] Criar `PermissionMode` enum (auto, prompt, deny)
- [ ] Implementar `PermissionManager` com circuit breaker
- [ ] Criar handlers para cada tipo de tool
- [ ] Integrar com runtime existente
- [ ] Adicionar testes (unit + integration)

**Critérios de Sucesso:**

- Todas as tools passam por permission check
- Modo prompt funciona via API/gRPC
- Logs de auditoria de permissões
- 85%+ test coverage

### 1.2 Context Management (QueryEngine)

**Arquivos de Referência (Claude Code):**

- `src/QueryEngine.ts` - Engine principal
- `src/utils/queryContext.ts` - Context fetching
- `src/context/` - Context providers

**Implementação MindFlow:**

```
python/mindflow_backend/
├── context/
│   ├── __init__.py
│   ├── query_engine.py       # Main QueryEngine
│   ├── context_builder.py    # Build context from sources
│   ├── providers/
│   │   ├── git_provider.py   # Git status, diffs
│   │   ├── file_provider.py  # File content
│   │   ├── memory_provider.py # Memory retrieval
│   │   └── mcp_provider.py   # MCP resources
│   └── budget/
│       ├── token_counter.py  # Token budget management
│       └── compressor.py     # Context compression
```

**Tarefas:**

- [ ] Criar `QueryEngine` com budget management
- [ ] Implementar context providers
- [ ] Integrar com memória existente
- [ ] Adicionar compressão de contexto
- [ ] Token counting (tiktoken)

**Critérios de Sucesso:**

- Context budget respeitado (200k tokens)
- Providers funcionam independentemente
- Integração com memória existente
- 80%+ test coverage

---

## FASE 2: Infraestrutura - Hooks & Task Management

**Prioridade:** ALTA  
**Duração:** 2-3 semanas  
**Objetivo:** Extensibilidade e gerenciamento de tarefas assíncronas

### 2.1 Hooks System

**Arquivos de Referência (Claude Code):**

- `src/hooks/` - Hook implementations
- `src/utils/hooks/hookHelpers.ts` - Hook utilities
- `src/types/hooks.ts` - Hook types

**Implementação MindFlow:**

```
python/mindflow_backend/
├── hooks/
│   ├── __init__.py
│   ├── types.py              # HookType, HookContext
│   ├── manager.py            # HookManager
│   ├── registry.py           # Hook registration
│   ├── handlers/
│   │   ├── pre_tool_use.py   # Before tool execution
│   │   ├── post_tool_use.py  # After tool execution
│   │   └── stop.py           # Session end hooks
│   └── builtin/
│       ├── format_hook.py    # Auto-format code
│       ├── lint_hook.py      # Run linters
│       └── test_hook.py      # Run tests
```

**Tarefas:**

- [ ] Criar `HookManager` com async support
- [ ] Implementar hook types (PreToolUse, PostToolUse, Stop)
- [ ] Criar hooks builtin (format, lint, test)
- [ ] Integrar com runtime execution
- [ ] Configuração via settings

**Critérios de Sucesso:**

- Hooks executam antes/depois de tools
- Hooks podem modificar inputs/outputs
- Hooks podem bloquear execução
- 80%+ test coverage

### 2.2 Task Management

**Arquivos de Referência (Claude Code):**

- `src/Task.ts` - Task types e base
- `src/tasks/` - Task implementations
- `src/utils/task/` - Task utilities

**Implementação MindFlow:**

```
python/mindflow_backend/
├── tasks/
│   ├── __init__.py
│   ├── types.py              # TaskType, TaskStatus, TaskState
│   ├── manager.py            # TaskManager
│   ├── implementations/
│   │   ├── bash_task.py      # Shell command tasks
│   │   ├── agent_task.py     # Agent execution tasks
│   │   ├── workflow_task.py  # Multi-step workflows
│   │   └── monitor_task.py   # Monitoring tasks
│   └── storage/
│       ├── disk_output.py    # Task output persistence
│       └── state_store.py    # Task state management
```

**Tarefas:**

- [ ] Criar `TaskManager` com state machine
- [ ] Implementar task types (bash, agent, workflow)
- [ ] Task output streaming
- [ ] Task lifecycle management (spawn, kill, cleanup)
- [ ] Integrar com RabbitMQ existente

**Critérios de Sucesso:**

- Tasks executam em background
- Task status tracking funciona
- Output streaming funciona
- Cleanup automático de tasks finalizadas
- 85%+ test coverage

---

## FASE 3: Orquestração - Commands & Agent Patterns

**Prioridade:** MÉDIA  
**Duração:** 3-4 semanas  
**Objetivo:** Sistema de comandos e padrões de sub-agentes

### 3.1 Command System

**Arquivos de Referência (Claude Code):**

- `src/commands.ts` - Command registry
- `src/commands/` - 80+ command implementations

**Implementação MindFlow:**

```
python/mindflow_backend/
├── commands/
│   ├── __init__.py
│   ├── registry.py           # Command registration
│   ├── parser.py             # Command parsing
│   ├── executor.py           # Command execution
│   ├── builtin/
│   │   ├── help.py           # /help
│   │   ├── status.py         # /status
│   │   ├── memory.py         # /memory
│   │   ├── agents.py         # /agents
│   │   ├── tasks.py          # /tasks
│   │   └── config.py         # /config
│   └── custom/
│       └── user_commands.py  # User-defined commands
```

**Tarefas:**

- [ ] Criar `CommandRegistry` com discovery
- [ ] Implementar command parser (slash commands)
- [ ] Criar comandos essenciais (help, status, memory, agents)
- [ ] Integrar com API/gRPC
- [ ] Documentação de comandos

**Critérios de Sucesso:**

- Comandos funcionam via API
- Help system funciona
- Comandos podem ser estendidos
- 80%+ test coverage

### 3.2 Sub-Agent Orchestration

**Arquivos de Referência (Claude Code):**

- `src/tools/AgentTool/` - Agent tool implementation
- `src/tools/AgentTool/built-in/` - Built-in agents

**Implementação MindFlow:**

```
python/mindflow_backend/
├── agents/
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── agent_tool.py     # AgentTool implementation
│   │   ├── spawner.py        # Agent spawning logic
│   │   ├── coordinator.py    # Multi-agent coordination
│   │   └── definitions/
│   │       ├── planner.py    # Planning agent
│   │       ├── reviewer.py   # Code review agent
│   │       ├── tester.py     # Testing agent
│   │       └── explorer.py   # Codebase exploration agent
```

**Tarefas:**

- [ ] Criar `AgentTool` para spawning
- [ ] Implementar agent definitions (planner, reviewer, etc.)
- [ ] Agent isolation (worktree pattern)
- [ ] Agent communication via CommunicationBus
- [ ] Integrar com missões existentes

**Critérios de Sucesso:**

- Sub-agents podem ser spawned
- Agents se comunicam via bus
- Agent results são retornados
- 80%+ test coverage

---

## FASE 4: Automação - Loops & Scheduling

**Prioridade:** BAIXA  
**Duração:** 1-2 semanas  
**Objetivo:** Tarefas recorrentes e agendamento

### 4.1 Loops & Cron

**Arquivos de Referência (Claude Code):**

- `src/tools/ScheduleCronTool/` - Cron scheduling

**Implementação MindFlow:**

```
python/mindflow_backend/
├── scheduling/
│   ├── __init__.py
│   ├── scheduler.py          # Main scheduler
│   ├── cron_parser.py        # Cron expression parsing
│   ├── job_store.py          # Job persistence
│   └── executors/
│       ├── loop_executor.py  # Loop execution
│       └── cron_executor.py  # Cron execution
```

**Tarefas:**

- [ ] Criar `Scheduler` com APScheduler
- [ ] Implementar cron parsing
- [ ] Job persistence (PostgreSQL)
- [ ] Loop execution
- [ ] Integrar com tasks

**Critérios de Sucesso:**

- Cron jobs funcionam
- Loops executam periodicamente
- Jobs persistem entre restarts
- 80%+ test coverage

---

## 🔧 Implementação Técnica

### Padrões de Código

#### 1. Imutabilidade

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PermissionResult:
    allowed: bool
    reason: str | None = None
    metadata: dict[str, Any] | None = None
```

#### 2. Protocol-based Interfaces

```python
from typing import Protocol

class PermissionHandler(Protocol):
    async def check(self, context: PermissionContext) -> PermissionResult: ...
```

#### 3. Circuit Breaker Pattern

```python
from mindflow_backend.infra.resilience.circuit_breaker import CircuitBreaker

class PermissionManager:
    def __init__(self):
        self._circuit_breaker = CircuitBreaker(name="permissions")
    
    async def check_permission(self, tool: str) -> PermissionResult:
        return await self._circuit_breaker.execute(
            lambda: self._do_check(tool)
        )
```

#### 4. Dependency Injection

```python
class QueryEngine:
    def __init__(
        self,
        memory_service: MemoryService,
        context_providers: list[ContextProvider],
    ):
        self._memory = memory_service
        self._providers = context_providers
```

### Estrutura de Testes

```python
# tests/unit/permissions/test_manager.py
import pytest
from mindflow_backend.permissions import PermissionManager

@pytest.mark.unit
async def test_permission_manager_allows_tool():
    manager = PermissionManager(mode="auto")
    result = await manager.check("read_file", path="/allowed/file.py")
    assert result.allowed is True

@pytest.mark.integration
async def test_permission_manager_with_circuit_breaker():
    # Test circuit breaker behavior
    pass
```

---

## 📊 Métricas de Sucesso

### Por Fase

| Fase | Test Coverage | Performance | Backward Compat |
|------|--------------|-------------|-----------------|
| 1    | 85%+         | <100ms overhead | 100% |
| 2    | 80%+         | <50ms overhead  | 100% |
| 3    | 80%+         | <200ms overhead | 95%  |
| 4    | 80%+         | <10ms overhead  | 100% |

### Métricas Globais

- **Code Quality:** Ruff score 9.5+
- **Type Coverage:** mypy strict mode 90%+
- **Documentation:** 100% public APIs documentadas
- **Performance:** Latência p95 < 500ms
- **Reliability:** Uptime 99.9%+

---

## 🚨 Riscos e Mitigações

### Riscos Identificados

1. **Breaking Changes em APIs Existentes**
   - **Mitigação:** Manter APIs antigas com deprecation warnings
   - **Timeline:** 2 releases para deprecation completa

2. **Performance Degradation**
   - **Mitigação:** Benchmarks contínuos, profiling
   - **Threshold:** Máximo 10% overhead aceitável

3. **Complexidade Aumentada**
   - **Mitigação:** Documentação extensiva, exemplos
   - **Review:** Code review obrigatório para mudanças core

4. **Resistência da Equipe**
   - **Mitigação:** Treinamento, pair programming
   - **Comunicação:** Weekly updates sobre progresso

### Rollback Plan

Cada fase tem rollback independente:

- Feature flags para novas funcionalidades
- Branches de longa duração com merges incrementais
- Testes A/B em produção (canary deployments)

---

## 📅 Timeline

```
Semana 1-3:   FASE 1 - Permission System & Context Management
Semana 4-6:   FASE 2 - Hooks & Task Management
Semana 7-10:  FASE 3 - Commands & Agent Patterns
Semana 11-12: FASE 4 - Loops & Scheduling
Semana 13:    Integração Final & Documentação
Semana 14:    Testing & Hardening
```

**Total:** 14 semanas (~3.5 meses)

---

## 🎓 Recursos de Aprendizado

### Para a Equipe

1. **Claude Code Patterns Study**
   - Ler `src/QueryEngine.ts` completo
   - Estudar `src/hooks/` implementation
   - Analisar `src/tasks/` architecture

2. **Python Enterprise Patterns**
   - Protocol-based design
   - Async/await best practices
   - Circuit breaker pattern

3. **Testing Strategy**
   - pytest fixtures avançados
   - Integration testing patterns
   - Mocking strategies

### Documentação Necessária

- [ ] Architecture Decision Records (ADRs)
- [ ] API documentation (OpenAPI)
- [ ] Developer onboarding guide
- [ ] Migration guide (old → new APIs)

---

## ✅ Checklist de Início

Antes de começar FASE 1:

- [ ] Aprovação do plano pela equipe
- [ ] Setup de feature flags
- [ ] Criação de branches de desenvolvimento
- [ ] Setup de CI/CD para novas fases
- [ ] Documentação de APIs existentes
- [ ] Baseline de performance estabelecido
- [ ] Comunicação com stakeholders

---

## 📝 Próximos Passos Imediatos

1. **Review deste plano** com a equipe
2. **Priorizar FASE 1** - Permission System é crítico
3. **Criar ADR** para decisões arquiteturais
4. **Setup de ambiente** para desenvolvimento paralelo
5. **Iniciar implementação** de `PermissionManager`

---

**Autor:** Claude Code (Sonnet 4.6)  
**Revisão:** Pendente  
**Status:** DRAFT

---

## 📊 Progresso de Implementação

### FASE 2: Hooks System ✅ COMPLETADA (2026-03-31)

**Arquivos criados (14 arquivos):**

```
python/mindflow_backend/hooks/
├── __init__.py                    ✅ Core types + exports
├── types.py                       ✅ HookEvent, HookPermissionBehavior, PermissionMode
├── context.py                     ✅ HookContext dataclass
├── result.py                      ✅ HookResult, AggregatedHookResult, HookCommand, HookMatcher
├── manager.py                     ✅ HookManager singleton (execute, execute_pre_tool, execute_post_tool, etc.)
├── registry.py                    ✅ HookRegistry (config, plugin, agent, function hooks)
├── helpers.py                     ✅ create_hook_input, parse_hook_response, validate_hook_config
├── handlers/
│   ├── __init__.py                ✅ Handler exports
│   ├── pre_tool_use.py            ✅ PreToolUseHandler
│   ├── post_tool_use.py           ✅ PostToolUseHandler
│   ├── post_tool_failure.py       ✅ PostToolFailureHandler
│   ├── stop.py                    ✅ StopHandler
│   ├── session_start.py           ✅ SessionStartHandler
│   ├── user_prompt_submit.py      ✅ UserPromptSubmitHandler
│   └── permission_hook.py         ✅ PermissionRequestHandler, PermissionDeniedHandler
├── builtin/
│   ├── __init__.py                ✅ Builtin hook exports
│   ├── format_hook.py             ✅ Auto-format (ruff, prettier, rustfmt, gofmt)
│   ├── lint_hook.py               ✅ Auto-lint (ruff check, eslint, golangci-lint)
│   ├── test_hook.py               ✅ Auto-test (pytest, vitest, jest, go test)
│   └── git_hook.py                ✅ Git safety (block force push, hard reset, etc.)
└── tests/
    └── unit/hooks/test_hooks.py   ✅ Test suite (40+ tests)
```

**Padrão adaptado de Claude Code:**

- `src/types/hooks.ts` → `types.py` (HookEvent enum)
- `src/utils/hooks/hookHelpers.ts` → `helpers.py` (utilities)
- `src/utils/hooks.ts` → `manager.py` (execution engine)
- `src/hooks/` handlers → `handlers/` (event handlers)
- `src/hooks/builtin/` → `builtin/` (format, lint, test hooks)

**Integração com Runtime:**

- PreToolUse: Chamado ANTES de tool execution via `_stream_tool_aware_direct_agent` em `executor.py`
- PostToolUse: Chamado DEPOIS de tool execution na branch `tool_call` com `result_preview`
- Stop: Chamado após `yield done_event` em cada método de executor
- SessionStart: Chamado em `agent_runtime.py` ao iniciar sessão
- UserPromptSubmit: Chamado antes de chamar `executor.stream_chat_*()`
