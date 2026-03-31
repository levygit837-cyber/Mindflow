# Claude Code CLI → MindFlow Integration Plan

## 1. Análise Completa dos Sistemas de Execução

### 1.1 Claude Code CLI (src/)

**Fluxo de Execução Input → Output:**

```
User Input → REPL → QueryEngine.submitMessage()
  │
  ├── Context Building
  │   ├── getSystemContext() (git status, injection)
  │   ├── getUserContext() (CLAUDE.md, date)
  │   └── Token budget check
  │
  ├── API Call (streaming)
  │   └── while (true) loop:
  │       ├── Auto-compact check (token limit)
  │       ├── callModel() (streaming API)
  │       ├── Post-sampling hooks
  │       └── Tool execution:
  │           ├── runPreToolUseHooks() ← pode MODIFICAR input
  │           ├── checkRuleBasedPermissions()
  │           ├── tool.call()
  │           └── runPostToolUseHooks() ← feedback loop
  │
  └── Yield result / Session continue
```

**Componentes-Chave do Claude Code:**

| Componente | Arquivo | Função |
|-----------|---------|--------|
| QueryEngine | QueryEngine.ts | Motor de conversas principal |
| Tool System | Tool.ts | Interface padrão para ferramentas |
| Tool Hooks | toolHooks.ts | Pre/Post hooks com AsyncGenerator |
| Permission Hooks | hooks.ts | PermissionRequest hooks |
| Cost Tracker | cost-tracker.ts | Rastreamento de custo por modelo |
| Auto Compact | autoCompact.ts | Compactação automática de contexto |
| Task System | Task.ts | Sistema de tarefas multi-agente |

### 1.2 MindFlow Backend (python/)

**Fluxo de Execução Input → Output:**

```
User Input → API → AgentRuntime.stream_chat_orchestrated()
  │
  ├── Load History + Build Graph Input
  │
  ├── IntelligentRouter → Route Decision
  │   ├── DIRECT_RESPONSE (orchestrator responde)
  │   ├── DELEGATE (delega a agente específico)
  │   ├── CHAIN (execução sequencial)
  │   ├── GRAPH (LangGraph execution)
  │   └── TEAM_SESSION (multi-agent colaborativo)
  │
  └── ExecuteNode (Deep Work Loop)
      ├── AgentBridge → invoke_with_tools()
      └── while depth < max_depth:
          ├── LLM call + tools
          ├── Accumulate response
          └── check_should_continue_investigation()
```

**Componentes-Chave do MindFlow:**

| Componente | Arquivo | Função |
|-----------|---------|--------|
| AgentRuntime | runtime/execution/executor.py | Runtime principal com streaming |
| ExecuteNode | nodes/implementations/orchestrator/execute_node.py | LLM node com Deep Work loop |
| LoopNode | nodes/implementations/control/loop_node.py | Controle iterativo |
| IntelligentRouter | orchestrator/routing/intelligent_router.py | Roteamento com 5 estratégias |
| HookManager | hooks/manager.py | Registry e execution de hooks |
| MissionLauncher | execution/missions/mission_launcher.py | Lançamento de missões |
| TeamOrchestrator | execution/teams/team_orchestrator.py | Orquestração multi-agent |

---

## 2. Comparação Direta

| Aspecto | Claude Code CLI | MindFlow | Diferença |
|---------|----------------|----------|-----------|
| **Loop Principal** | Query loop simples (while true) | Graph-based (LangGraph) | Claude = mais simples; MindFlow = mais estruturado |
| **Deep Work** | Loop contínuo com acumulação | ExecuteNode com max_depth | Similar conceitualmente |
| **Hooks Pré-Tool** | ✅ Input mutation (modifica tool_input) | ❌ Hooks apenas observação | **Claude é mais poderoso** |
| **Hooks Pós-Tool** | ✅ Feedback loop + retry | ⚠️ Observação apenas | Claude é mais interativo |
| **Permission Hooks** | ✅ Programmatic approval | ⚠️ Separado do hook system | **Diferença significativa** |
| **Auto-Compact** | ✅ Snip, cache, collapse | ❌ Não implementado | **Claude gerencia contexto** |
| **Token Budget** | ✅ Per session, per model | ⚠️ TokenCounter básico | Claude é mais granular |
| **Cost Tracking** | ✅ By model, per session | ⚠️ Não integrado | Claude rastreia custos |
| **Multi-Agent** | ✅ Task types (local/remote) | ✅ Mission + Team protocol | **Ambos robustos** |
| **Orchestration** | ✅ Single agent selection | ✅ 5 strategies (DIRECT/DELEGATE/CHAIN/GRAPH/TEAM) | **MindFlow é superior** |
| **Memory** | ❌ Session-only | ✅ Project Memory + RAG | **MindFlow é superior** |

### 2.1 Pontos Fortes do Claude Code (para adotar)

1. **PreToolUse com Input Mutation** - hooks podem modificar parâmetros de ferramentas
2. **AsyncGenerator Pattern** - streaming de progresso dos hooks
3. **Auto-Compact System** - snip, cache, collapse automáticos
4. **Token Budget Management** - limites por sessão, modelo, custo
5. **Permission Request Hooks** - aprovação/negação programática
6. **PostToolUse Feedback Loop** - retry com sugestões automáticas

### 2.2 Pontos Fortes do MindFlow (para manter)

1. **Graph-Based Execution** - execução estruturada via LangGraph
2. **Intelligent Router** - 5 estratégias de roteamento
3. **Mission/Team System** - orquestração multi-agent sofisticada
4. **Project Memory** - persistência cross-session
5. **ContextPlus** - análise semântica do codebase
6. **Communication Bus** - XMPP-based agent communication

---

## 3. Implementação Realizada

### 3.1 TokenBudgetManager

**Arquivo:** `python/mindflow_backend/query/budget/token_budget_manager.py`

**Features implementadas:**

- TokenUsage per API call (input, output, cache tokens)
- TokenBudgetConfig com limites configuráveis
- Model-specific token tracking
- Cost tracking (USD)
- Warning thresholds (85%)
- Auto-compact trigger (90%)
- Budget status API

**Exemplo de uso:**

```python
from python.mindflow_backend.query.budget import TokenBudgetManager, TokenUsage

manager = TokenBudgetManager(session_id="abc123")
manager.record_usage(TokenUsage(
    input_tokens=1000,
    output_tokens=500,
    model="claude-sonnet-4-20250514",
    cost_usd=0.015
))
status = manager.get_budget_status()
# {"total_tokens_used": 1500, "token_ratio": 0.0075, "should_compact": False, ...}
```

### 3.2 AutoCompactService

**Arquivo:** `python/mindflow_backend/query/budget/auto_compact.py`

**Features implementadas:**

- Snip Compact (remove oldest messages, insert placeholder)
- Context Collapse (merge consecutive messages)
- Summary Compact stub (para integração com LLM)
- Cache Compact stub (para integração com cache de modelo)
- Configurable thresholds
- Multiple CompactStrategy enum

**Exemplo de uso:**

```python
from python.mindflow_backend.query.budget import AutoCompactService, CompactConfig

service = AutoCompactService(CompactConfig(
    max_context_tokens=180_000,
    target_window_size=128_000,
))

if service.should_compact(current_tokens):
    result = service.compact(messages, current_tokens)
    # result.strategy_used = CompactStrategy.SNIP
    # result.tokens_saved = 45000
```

### 3.3 ClaudeStyleHookManager

**Arquivo:** `python/mindflow_backend/hooks/claude_style_hooks.py`

**Features implementadas:**

- PreToolUse hooks com **input mutation** (diferencial principal)
- PostToolUse hooks com feedback loop e retry
- PermissionRequest hooks para aprovação programática
- PostToolUseFailure hooks com recovery suggestions
- AsyncGenerator pattern para streaming
- Wildcard pattern matching para hooks globais
- Decorator-based registration

**Exemplo de uso:**

```python
from python.mindflow_backend.hooks.claude_style_hooks import (
    get_claude_hook_manager, HookResult, PermissionBehavior
)

manager = get_claude_hook_manager()

@manager.register_hook(HookEvent.PRE_TOOL_USE, "bash")
async def validate_bash_command(**kwargs):
    tool_input = kwargs["tool_input"]
    if "rm -rf" in tool_input.get("command", ""):
        yield HookResult(
            permission_behavior=PermissionBehavior.DENY,
            blocking_error="Destructive command blocked",
        )
    else:
        # Input mutation - adiciona redirect de stderr
        yield HookResult(
            updated_input={"command": tool_input["command"] + " 2>&1"},
        )

# Execution:
async for result in manager.execute_pre_tool_use_hooks("bash", tool_input):
    if result.updated_input:
        tool_input = result.updated_input  # Usa input modificado!
```

### 3.4 Tipos Atualizados

**Arquivo:** `python/mindflow_backend/hooks/types.py`

**Adições:**

- `HookEvent.PRE_TOOL_USE_FAILURE`
- `HookEvent.POST_TOOL_USE_FAILURE`
- `HookPermissionBehavior` (ALLOW, DENY, ASK, PASSTHROUGH)

**Arquivo:** `python/mindflow_backend/query/budget/__init__.py`

**Exports adicionados:**

- TokenBudgetManager, TokenBudgetConfig, TokenUsage
- AutoCompactService, CompactConfig, CompactResult, CompactStrategy

---

## 4. Componentes Pendentes

### 4.1 UnifiedExecutionEngine (ExecuteNode + LoopNode)

**Objetivo:** Integrar o loop de execução do Claude com o graph-based execution do MindFlow.

**Design:**

```python
@dataclass
class UnifiedExecutionConfig:
    max_iterations: int = 1000
    token_budget: TokenBudgetConfig | None = None
    compact_service: AutoCompactService | None = None
    hook_manager: ClaudeStyleHookManager | None = None
    break_condition: Callable[[dict[str, Any]], bool] | None = None
    continue_condition: Callable[[dict[str, Any]], bool] | None = None

class UnifiedExecutionEngine:
    """Combina ExecuteNode + LoopNode + Claude patterns."""
    
    async def execute(self, config: UnifiedExecutionConfig, state: dict) -> dict:
        current_depth = 0
        while current_depth < config.max_iterations:
            # Budget check
            if config.token_budget and config.token_budget.manager.should_compact():
                compact_result = config.compact_service.compact(messages, tokens)
            
            # Hook execution with input mutation
            async for hook_result in hook_manager.execute_pre_tool_use_hooks(...):
                if hook_result.updated_input:
                    state["tool_input"] = hook_result.updated_input
            
            # Tool execution
            result = await self.call_tool(state["tool_input"])
            
            # Post hooks with feedback
            async for hook_result in hook_manager.execute_post_tool_use_hooks(...):
                if hook_result.retry:
                    continue  # Retry with modified input
            
            # Check break condition
            if config.break_condition and config.break_condition(state):
                break
            
            current_depth += 1
        
        return state
```

### 4.2 Dynamic Delegation

**Objetivo:** LLM decide quantos agentes delegar e em que sequência.

**Design:**

```python
class DynamicDelegationEngine:
    """LLM decide delegation plan dynamically."""
    
    async def create_delegation_plan(self, task: str) -> DelegationPlan:
        """LLM generates a delegation plan."""
        prompt = f"""
        For the following task: "{task}"
        
        Determine:
        1. Is this a single-agent or multi-agent task?
        2. If multi-agent, which agents are needed?
        3. What's the best execution order?
        4. Are there dependencies between agents?
        
        Return a delegation plan with:
        - agents: list of AgentType
        - execution_order: parallel | sequential | dag
        - dependencies: list of (agent_a, agent_b)
        """
        response = await self._llm(prompt)
        return DelegationPlan.model_validate_json(response)
```

---

## 5. Timeline de Implementação

| Fase | Componente | Status | Arquivo |
|------|-----------|--------|---------|
| 1 | TokenBudgetManager | ✅ Pronto | query/budget/token_budget_manager.py |
| 2 | AutoCompactService | ✅ Pronto | query/budget/auto_compact.py |
| 3 | ClaudeStyleHookManager | ✅ Pronto | hooks/claude_style_hooks.py |
| 4 | UnifiedExecutionEngine | ⏳ Pendente | execution/unified_engine.py |
| 5 | Dynamic Delegation | ⏳ Pendente | orchestrator/delegation/dynamic.py |
| 6 | Integration Tests | ⏳ Pendente | tests/unit/budget/ |
| 7 | Documentation | ⏳ Pendente | docs/budget-management.md |

---

## 6. Referências

### Claude Code CLI

- `src/QueryEngine.ts` - Motor de conversas
- `src/Tool.ts` - Interface de ferramentas
- `src/services/tools/toolHooks.ts` - Hooks com input mutation
- `src/utils/hooks.ts` - Hook execution system
- `src/cost-tracker.ts` - Rastreamento de custos
- `services/autoCompact.ts` - Compactação automática

### MindFlow Backend

- `nodes/implementations/orchestrator/execute_node.py` - ExecuteNode
- `nodes/implementations/control/loop_node.py` - LoopNode
- `runtime/execution/executor.py` - AgentRuntime
- `orchestrator/routing/intelligent_router.py` - IntelligentRouter
- `hooks/manager.py` - HookManager existente
- `hooks/types.py` - Tipos de hooks

---

*Gerado em 31/03/2026 - Análise Claude Code CLI vs MindFlow + Plano de Integração*
