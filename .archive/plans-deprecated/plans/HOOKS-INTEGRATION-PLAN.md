# Plano de Integração — Sistema de Hooks MindFlow

**Data:** 01/04/2026
**Versão:** 1.0
**Status:** Aprovado para Implementação

---

## 1. Objetivo

Integrar completamente o sistema de hooks do MindFlow com o padrão Claude Code, passando de **14 eventos** para **27 eventos**, corrigindo a integração atual no runtime, implementando config loading automático e unificando os dois sistemas de hook coexistentes.

**Resultado esperado:** 90%+ de paridade com Claude Code, mantendo vantagens exclusivas do MindFlow.

---

## 2. Estado Atual

### 2.1 Estrutura Atual

```
python/mindflow_backend/hooks/
├── __init__.py              # Exports
├── types.py                 # HookEvent (14 eventos)
├── context.py               # HookContext
├── result.py                # HookResult, AggregatedHookResult
├── registry.py              # HookRegistry
├── manager.py               # HookManager (singleton)
├── helpers.py               # Utilitários
├── claude_style_hooks.py    # SISTEMA REDUNDANTE
├── handlers/
│   ├── __init__.py
│   ├── pre_tool_use.py
│   ├── post_tool_use.py
│   ├── post_tool_failure.py
│   ├── stop.py
│   ├── session_start.py
│   ├── user_prompt_submit.py
│   ├── instructions_loaded.py
│   └── permission_hook.py
└── builtin/
    ├── __init__.py
    ├── format_hook.py
    ├── lint_hook.py
    ├── test_hook.py
    └── git_hook.py
```

### 2.2 Problemas Identificados

1. **14 eventos** vs 27 do Claude Code (52% cobertura)
2. `streaming_executor.py` verifica `behavior == "block"` em vez de `"deny"`
3. `updated_input` (input mutation) nunca é aplicado
4. `additional_context` nunca é injetado no prompt
5. `PostToolUse` não integrado no fluxo principal
6. `claude_style_hooks.py` cria sistema paralelo redundante
7. Não há config loading automático de `settings.yaml`
8. Não há plugin hooks loading
9. Não há event broadcasting para UI

---

## 3. Estrutura Nova

```
python/mindflow_backend/hooks/
├── __init__.py              # [MOD] Novos exports
├── types.py                 # [MOD] 14 → 27 eventos
├── context.py               # [MOD] Novos campos para novos eventos
├── result.py                # [MANTER]
├── registry.py              # [MANTER]
├── manager.py               # [MOD] Novos execute_* methods
├── helpers.py               # [MOD] Novos match_query
├── config_loader.py         # [NOVO] Carregar hooks de settings.yaml
├── plugin_loader.py         # [NOVO] Carregar hooks de plugins
├── event_broadcaster.py     # [NOVO] Sistema de broadcast
├── handlers/
│   ├── __init__.py          # [MOD] Novos imports
│   ├── pre_tool_use.py      # [MANTER]
│   ├── post_tool_use.py     # [MANTER]
│   ├── post_tool_failure.py # [MANTER]
│   ├── stop.py              # [MANTER]
│   ├── session_start.py     # [MANTER]
│   ├── session_end.py       # [NOVO]
│   ├── user_prompt_submit.py# [MANTER]
│   ├── instructions_loaded.py# [MANTER]
│   ├── permission_hook.py   # [MANTER]
│   ├── pre_compact.py       # [NOVO]
│   ├── post_compact.py      # [NOVO]
│   ├── notification.py      # [NOVO]
│   ├── task_lifecycle.py    # [NOVO]
│   ├── stop_failure.py      # [NOVO]
│   ├── config_change.py     # [NOVO]
│   ├── setup.py             # [NOVO]
│   ├── file_watcher.py      # [NOVO]
│   └── teammate_idle.py     # [NOVO]
└── builtin/
    ├── __init__.py          # [MOD] Auto-registro
    ├── format_hook.py       # [MANTER]
    ├── lint_hook.py         # [MANTER]
    ├── test_hook.py         # [MANTER]
    └── git_hook.py          # [MANTER]
```

### Arquivos Externos

```
python/mindflow_backend/
├── runtime/execution/streaming_executor.py  # [MOD] Corrigir hooks
├── runtime/core/agent_runtime.py            # [MOD] Session lifecycle
└── infra/config/settings.py                 # [MOD] Hook loading
```

---

## 4. Fase 1: Corrigir Integração Atual (1-2 dias)

### 4.1 Modificar `streaming_executor.py`

**Arquivo:** `python/mindflow_backend/runtime/execution/streaming_executor.py`

**Linha ~310 — Corrigir behavior check:**

```python
# ANTES:
if hook_result.behavior == "block":
    tool.mark_error(f"Blocked by hook: {hook_result.reasoning or hook_result.error}")
    return

# DEPOIS:
from mindflow_backend.hooks.types import HookPermissionBehavior

if hook_result.behavior == HookPermissionBehavior.DENY:
    tool.mark_error(f"Blocked by hook: {hook_result.reason or hook_result.error}")
    await self._emit_result(tool)
    return
```

**Após behavior check — Aplicar input mutation:**

```python
# Adicionar após o DENY check:
if hook_result.updated_input:
    tool.tool_input = {**tool.tool_input, **hook_result.updated_input}

if hook_result.add_context:
    self._tool_use_context.add_hook_context(hook_result.add_context)
```

**Após tool execution bem-sucedida — Integrar PostToolUse:**

```python
# Adicionar após execução bem-sucedida da tool, antes de emitir resultado:
async for hook_result in self._hook_manager.execute_post_tool(
    tool_name=tool.tool_name,
    tool_input=tool.tool_input,
    tool_use_id=tool.id,
    tool_response=result,
    session_id=self._tool_use_context.session_id,
    cwd=self._tool_use_context.cwd,
    permission_mode=self._tool_use_context.permission_mode,
):
    if hook_result.add_context:
        self._tool_use_context.add_hook_context(hook_result.add_context)
```

### 4.2 Deletar `claude_style_hooks.py`

**Arquivo:** `python/mindflow_backend/hooks/claude_style_hooks.py`

**Ação:** Deletar completamente. Toda funcionalidade já existe em `HookManager`.

### 4.3 Atualizar Builtin Hooks Auto-registro

**Arquivo:** `python/mindflow_backend/hooks/builtin/__init__.py`

```python
"""Builtin hooks — Auto-registro na inicialização."""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

def register_builtin_hooks() -> int:
    """Registra todos os builtin hooks. Retorna número de hooks registrados."""
    from mindflow_backend.hooks.manager import HookManager
    from mindflow_backend.hooks.types import HookEvent
    from mindflow_backend.hooks.result import HookCommand

    manager = HookManager.get_instance()
    count = 0

    # Format hook — PostToolUse para Write|Edit
    manager.register_command(
        HookEvent.POST_TOOL_USE,
        "Write|Edit",
        "jq -r '.tool_input.file_path // .tool_response.filePath' | "
        "{ read -r f; black \"$f\" 2>/dev/null || true; }",
        timeout=30,
    )
    count += 1

    # Lint hook — PostToolUse para Write|Edit
    manager.register_command(
        HookEvent.POST_TOOL_USE,
        "Write|Edit",
        "jq -r '.tool_input.file_path // .tool_response.filePath' | "
        "{ read -r f; ruff check \"$f\" 2>/dev/null || true; }",
        timeout=30,
    )
    count += 1

    logger.info("builtin_hooks_registered", count=count)
    return count
```

### Resultado Fase 1

- ✅ `streaming_executor.py` usa `DENY` corretamente
- ✅ Input mutation funciona (`updated_input` aplicado)
- ✅ Additional context é injetado (`add_context`)
- ✅ PostToolUse integrado no fluxo
- ✅ `claude_style_hooks.py` removido (sistema unificado)
- ✅ Builtin hooks auto-registrados

---

## 5. Fase 2: Adicionar 13 Eventos Faltando (2-3 dias)

### 5.1 Modificar `types.py`

**Arquivo:** `python/mindflow_backend/hooks/types.py`

```python
class HookEvent(StrEnum):
    """Events that trigger hooks — Claude Code parity + MindFlow extensions."""

    # === Tool Lifecycle (4) ===
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    PERMISSION_REQUEST = "PermissionRequest"

    # === Session Lifecycle (3) ===
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"          # [NOVO]
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"        # [NOVO]

    # === Agent Lifecycle (2) ===
    AGENT_START = "AgentStart"
    AGENT_STOP = "AgentStop"

    # === Subagent Lifecycle (2) ===
    SUBAGENT_START = "SubagentStart"    # [NOVO]
    SUBAGENT_STOP = "SubagentStop"      # [NOVO]

    # === User Interaction (2) ===
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PERMISSION_DENIED = "PermissionDenied"

    # === Compaction (2) ===
    PRE_COMPACT = "PreCompact"          # [NOVO]
    POST_COMPACT = "PostCompact"        # [NOVO]

    # === Notification (1) ===
    NOTIFICATION = "Notification"       # [NOVO]

    # === Task Lifecycle (2) ===
    TASK_CREATED = "TaskCreated"        # [NOVO]
    TASK_COMPLETED = "TaskCompleted"    # [NOVO]

    # === Config/Setup (2) ===
    SETUP = "Setup"                     # [NOVO]
    CONFIG_CHANGE = "ConfigChange"      # [NOVO]

    # === File System (2) ===
    FILE_CHANGED = "FileChanged"        # [NOVO]
    CWD_CHANGED = "CwdChanged"          # [NOVO]

    # === Teammate (1) ===
    TEAMMATE_IDLE = "TeammateIdle"      # [NOVO]

    # === MCP (2) ===
    ELICITATION = "Elicitation"         # [NOVO]
    ELICITATION_RESULT = "ElicitationResult"  # [NOVO]

    # === Worktree (2) ===
    WORKTREE_CREATE = "WorktreeCreate"  # [NOVO]
    WORKTREE_REMOVE = "WorktreeRemove"  # [NOVO]

    # === Instructions (1) ===
    INSTRUCTIONS_LOADED = "InstructionsLoaded"

    # === MindFlow Exclusive (2) ===
    MISSION_START = "MissionStart"
    MISSION_STOP = "MissionStop"
```

**Total: 27 eventos**

### 5.2 Modificar `context.py`

**Arquivo:** `python/mindflow_backend/hooks/context.py`

Adicionar campos para novos eventos:

```python
@dataclass
class HookContext:
    """Contexto passado para todos os hooks."""

    # ... campos existentes ...

    # SessionEnd
    reason: str | None = None  # "clear" | "resume" | "logout" | "other"

    # PreCompact / PostCompact
    trigger: str | None = None  # "manual" | "auto"
    summary: str | None = None  # PostCompact only

    # Notification
    notification_type: str | None = None

    # Task lifecycle
    task_id: str | None = None
    task_name: str | None = None

    # ConfigChange
    config_key: str | None = None
    old_value: Any = None
    new_value: Any = None

    # FileChanged / CwdChanged
    file_path: str | None = None
    old_cwd: str | None = None
    new_cwd: str | None = None

    # StopFailure
    stop_error: str | None = None

    # Subagent
    subagent_id: str | None = None
    subagent_type: str | None = None

    # Setup
    setup_trigger: str | None = None

    # MCP Elicitation
    mcp_server_name: str | None = None

    # Worktree
    worktree_path: str | None = None
```

### 5.3 Criar Novos Handlers

Cada handler segue o mesmo padrão. Exemplo para `session_end.py`:

**`handlers/session_end.py`:**

```python
"""SessionEnd Handler — Executado ao encerrar sessão."""

from __future__ import annotations
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent


class SessionEndHandler:
    """Handler para hooks SessionEnd."""

    @staticmethod
    async def execute(
        session_id: str,
        reason: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.SESSION_END,
            session_id=session_id,
            reason=reason,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.SESSION_END,
            ctx,
            match_query=reason,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result
```

**Arquivos a criar (9 handlers):**

| Arquivo | Classe | Eventos |
|---------|--------|---------|
| `handlers/session_end.py` | `SessionEndHandler` | SessionEnd |
| `handlers/pre_compact.py` | `PreCompactHandler` | PreCompact |
| `handlers/post_compact.py` | `PostCompactHandler` | PostCompact |
| `handlers/notification.py` | `NotificationHandler` | Notification |
| `handlers/task_lifecycle.py` | `TaskCreatedHandler`, `TaskCompletedHandler` | TaskCreated, TaskCompleted |
| `handlers/stop_failure.py` | `StopFailureHandler` | StopFailure |
| `handlers/config_change.py` | `ConfigChangeHandler` | ConfigChange |
| `handlers/setup.py` | `SetupHandler` | Setup |
| `handlers/file_watcher.py` | `FileChangedHandler`, `CwdChangedHandler` | FileChanged, CwdChanged |

### 5.4 Atualizar `handlers/__init__.py`

```python
from .instructions_loaded import InstructionsLoadedHandler
from .permission_hook import PermissionDeniedHandler, PermissionRequestHandler
from .post_tool_failure import PostToolFailureHandler
from .post_tool_use import PostToolUseHandler
from .pre_tool_use import PreToolUseHandler
from .session_start import SessionStartHandler
from .session_end import SessionEndHandler          # [NOVO]
from .stop import StopHandler
from .stop_failure import StopFailureHandler        # [NOVO]
from .pre_compact import PreCompactHandler          # [NOVO]
from .post_compact import PostCompactHandler        # [NOVO]
from .notification import NotificationHandler       # [NOVO]
from .task_lifecycle import TaskCreatedHandler, TaskCompletedHandler  # [NOVO]
from .config_change import ConfigChangeHandler      # [NOVO]
from .setup import SetupHandler                     # [NOVO]
from .file_watcher import FileChangedHandler, CwdChangedHandler  # [NOVO]
from .user_prompt_submit import UserPromptSubmitHandler

__all__ = [
    "InstructionsLoadedHandler",
    "PermissionDeniedHandler",
    "PermissionRequestHandler",
    "PostToolFailureHandler",
    "PostToolUseHandler",
    "PreToolUseHandler",
    "SessionStartHandler",
    "SessionEndHandler",
    "StopHandler",
    "StopFailureHandler",
    "PreCompactHandler",
    "PostCompactHandler",
    "NotificationHandler",
    "TaskCreatedHandler",
    "TaskCompletedHandler",
    "ConfigChangeHandler",
    "SetupHandler",
    "FileChangedHandler",
    "CwdChangedHandler",
    "UserPromptSubmitHandler",
]
```

### 5.5 Adicionar `execute_*` Methods em `manager.py`

```python
# Adicionar após execute_instructions_loaded:

async def execute_session_end(
    self,
    session_id: str,
    reason: str,
    *,
    cwd: str | None = None,
    timeout: float = DEFAULT_HOOK_TIMEOUT,
) -> AsyncGenerator[HookResult, None]:
    context = HookContext(
        hook_event_name=HookEvent.SESSION_END,
        session_id=session_id,
        reason=reason,
        cwd=cwd,
    )
    async for result in self.execute(
        HookEvent.SESSION_END, context,
        match_query=reason, timeout=timeout, session_id=session_id,
    ):
        yield result

async def execute_pre_compact(
    self,
    session_id: str,
    trigger: str,
    *,
    cwd: str | None = None,
    timeout: float = DEFAULT_HOOK_TIMEOUT,
) -> AsyncGenerator[HookResult, None]:
    context = HookContext(
        hook_event_name=HookEvent.PRE_COMPACT,
        session_id=session_id,
        trigger=trigger,
        cwd=cwd,
    )
    async for result in self.execute(
        HookEvent.PRE_COMPACT, context,
        match_query=trigger, timeout=timeout, session_id=session_id,
    ):
        yield result

async def execute_post_compact(
    self,
    session_id: str,
    trigger: str,
    summary: str,
    *,
    cwd: str | None = None,
    timeout: float = DEFAULT_HOOK_TIMEOUT,
) -> AsyncGenerator[HookResult, None]:
    context = HookContext(
        hook_event_name=HookEvent.POST_COMPACT,
        session_id=session_id,
        trigger=trigger,
        summary=summary,
        cwd=cwd,
    )
    async for result in self.execute(
        HookEvent.POST_COMPACT, context,
        match_query=trigger, timeout=timeout, session_id=session_id,
    ):
        yield result

# ... mesmo padrão para: execute_stop_failure, execute_notification,
# execute_task_created, execute_task_completed, execute_setup,
# execute_config_change, execute_file_changed, execute_cwd_changed
```

### 5.6 Atualizar `helpers.py`

```python
def get_match_query_for_event(event: HookEvent, context: dict[str, Any]) -> str | None:
    # ... existentes ...
    if event == HookEvent.SESSION_END:
        return context.get("reason")
    if event == HookEvent.PRE_COMPACT:
        return context.get("trigger")
    if event == HookEvent.POST_COMPACT:
        return context.get("trigger")
    if event == HookEvent.NOTIFICATION:
        return context.get("notification_type")
    if event == HookEvent.TASK_CREATED:
        return context.get("task_name")
    if event == HookEvent.TASK_COMPLETED:
        return context.get("task_name")
    if event == HookEvent.STOP_FAILURE:
        return context.get("stop_error")
    if event == HookEvent.SETUP:
        return context.get("setup_trigger")
    if event == HookEvent.CONFIG_CHANGE:
        return context.get("config_key")
    if event == HookEvent.FILE_CHANGED:
        return context.get("file_path")
    if event == HookEvent.CWD_CHANGED:
        return context.get("new_cwd")
    return None
```

### Resultado Fase 2

- ✅ 27 eventos definidos (paridade Claude Code)
- ✅ 9 novos handlers criados
- ✅ `execute_*` methods para todos os eventos
- ✅ `match_query` para todos os eventos

---

## 6. Fase 3: Config Loading (1-2 dias)

### 6.1 Criar `config_loader.py`

**Arquivo:** `python/mindflow_backend/hooks/config_loader.py`

```python
"""ConfigLoader — Carrega hooks de settings.yaml."""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.types import HookEvent
from mindflow_backend.hooks.result import HookCommand
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def load_hooks_from_settings(settings_path: str) -> int:
    """Carrega hooks de settings.yaml.

    Formato esperado:
    hooks:
      PreToolUse:
        - matcher: "Bash"
          hooks:
            - type: command
              command: "jq -r '.tool_input.command' >> ~/.mindflow/bash-log.txt"
              timeout: 30
      PostToolUse:
        - matcher: "Write|Edit"
          hooks:
            - type: command
              command: "prettier --write $FILE"
    """
    path = Path(settings_path)
    if not path.exists():
        _logger.warning("settings_file_not_found", path=str(path))
        return 0

    with open(path) as f:
        settings = yaml.safe_load(f)

    if not settings:
        return 0

    hooks_config = settings.get("hooks", {})
    if not hooks_config:
        return 0

    manager = HookManager.get_instance()
    count = 0

    for event_str, matchers in hooks_config.items():
        try:
            event = HookEvent(event_str)
        except ValueError:
            _logger.warning("unknown_hook_event", event=event_str)
            continue

        if not isinstance(matchers, list):
            continue

        for matcher_config in matchers:
            matcher = matcher_config.get("matcher")
            hooks_list = matcher_config.get("hooks", [])

            for hook_dict in hooks_list:
                cmd = HookCommand(
                    type=hook_dict.get("type", "command"),
                    command=hook_dict.get("command"),
                    timeout=hook_dict.get("timeout"),
                )
                manager.registry.register_config_hook(event, matcher, cmd)
                count += 1

    _logger.info("hooks_loaded_from_settings", path=str(path), count=count)
    return count
```

### 6.2 Criar `plugin_loader.py`

**Arquivo:** `python/mindflow_backend/hooks/plugin_loader.py`

```python
"""PluginLoader — Carrega hooks de plugins (hooks.json)."""

from __future__ import annotations

import json
from pathlib import Path

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def load_plugin_hooks(plugin_name: str, plugin_dir: str) -> int:
    """Carrega hooks de um plugin.

    O plugin deve ter um arquivo hooks.json no formato:
    {
      "description": "Plugin hooks",
      "hooks": {
        "PreToolUse": [
          {"matcher": "Bash", "hooks": [{"type": "command", "command": "..."}]}
        ]
      }
    }
    """
    hooks_path = Path(plugin_dir) / "hooks.json"
    if not hooks_path.exists():
        return 0

    try:
        with open(hooks_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _logger.error("plugin_hooks_load_error", plugin=plugin_name, error=str(exc))
        return 0

    hooks_config = config.get("hooks", {})
    if not hooks_config:
        return 0

    manager = HookManager.get_instance()
    manager.register_plugin_commands(plugin_name, hooks_config)

    count = sum(
        len(matcher.get("hooks", []))
        for matchers in hooks_config.values()
        for matcher in (matchers if isinstance(matchers, list) else [])
    )

    _logger.info("plugin_hooks_loaded", plugin=plugin_name, count=count)
    return count
```

### 6.3 Integrar no Startup

**Arquivo:** `python/mindflow_backend/infra/config/settings.py`

Adicionar após carregamento de configurações:

```python
def load_hooks_on_startup(settings_path: str, plugin_dirs: list[str] | None = None) -> int:
    """Carrega todos os hooks na inicialização do sistema."""
    from mindflow_backend.hooks.config_loader import load_hooks_from_settings
    from mindflow_backend.hooks.plugin_loader import load_plugin_hooks
    from mindflow_backend.hooks.builtin import register_builtin_hooks
    from mindflow_backend.infra.logging import get_logger

    logger = get_logger(__name__)
    total = 0

    # 1. Builtin hooks
    total += register_builtin_hooks()

    # 2. Config hooks (settings.yaml)
    total += load_hooks_from_settings(settings_path)

    # 3. Plugin hooks
    if plugin_dirs:
        for plugin_dir in plugin_dirs:
            plugin_name = Path(plugin_dir).name
            total += load_plugin_hooks(plugin_name, plugin_dir)

    logger.info("all_hooks_loaded", total=total)
    return total
```

### Resultado Fase 3

- ✅ Hooks carregados automaticamente de `settings.yaml`
- ✅ Hooks carregados automaticamente de plugins (`hooks.json`)
- ✅ Builtin hooks auto-registrados na startup
- ✅ Sistema completo de config loading

---

## 7. Fase 4: Hook Types Avançados (2-3 dias)

### 7.1 Modificar `manager.py`

Adicionar suporte a `prompt`, `agent` e `http` hook types no método `_execute_command`:

```python
async def _execute_command(
    self,
    hook_cmd: HookCommand,
    context: HookContext,
    timeout: float,
) -> HookResult:
    """Executa um hook command — suporta command, prompt, agent, http."""

    if hook_cmd.type == "command":
        return await self._execute_shell_command(hook_cmd, context, timeout)
    elif hook_cmd.type == "prompt":
        return await self._execute_prompt_hook(hook_cmd, context, timeout)
    elif hook_cmd.type == "agent":
        return await self._execute_agent_hook(hook_cmd, context, timeout)
    elif hook_cmd.type == "http":
        return await self._execute_http_hook(hook_cmd, context, timeout)
    else:
        return HookResult(
            event=context.hook_event_name,
            command=hook_cmd.command or "",
            status="error",
            error=f"Unknown hook type: {hook_cmd.type}",
        )


async def _execute_prompt_hook(
    self,
    hook_cmd: HookCommand,
    context: HookContext,
    timeout: float,
) -> HookResult:
    """Executa hook de tipo 'prompt' — avalia condição com LLM."""
    prompt = hook_cmd.command or ""
    # Substituir variáveis
    prompt = prompt.replace("$ARGUMENTS", json.dumps(context.tool_input or {}))
    prompt = prompt.replace("$TOOL_NAME", context.tool_name or "")
    prompt = prompt.replace("$FILE", (context.tool_input or {}).get("file_path", ""))

    # Chamar LLM
    try:
        from mindflow_backend.query.engine import QueryEngine
        engine = QueryEngine.get_instance()
        response = await engine.evaluate(
            prompt=prompt,
            timeout=timeout,
        )
        return HookResult.from_response(
            event=context.hook_event_name,
            command=hook_cmd.command or "",
            response=json.loads(response) if response else {},
        )
    except Exception as exc:
        return HookResult(
            event=context.hook_event_name,
            command=hook_cmd.command or "",
            status="error",
            error=str(exc),
        )


async def _execute_agent_hook(
    self,
    hook_cmd: HookCommand,
    context: HookContext,
    timeout: float,
) -> HookResult:
    """Executa hook de tipo 'agent' — roda sub-agente."""
    agent_prompt = hook_cmd.command or ""
    agent_prompt = agent_prompt.replace("$ARGUMENTS", json.dumps(context.tool_input or {}))

    try:
        from mindflow_backend.agents.planner_agent import PlannerAgent
        agent = PlannerAgent()
        result = await agent.run(
            prompt=agent_prompt,
            timeout=timeout,
        )
        return HookResult.from_response(
            event=context.hook_event_name,
            command=hook_cmd.command or "",
            response=result.to_dict() if hasattr(result, "to_dict") else {},
        )
    except Exception as exc:
        return HookResult(
            event=context.hook_event_name,
            command=hook_cmd.command or "",
            status="error",
            error=str(exc),
        )


async def _execute_http_hook(
    self,
    hook_cmd: HookCommand,
    context: HookContext,
    timeout: float,
) -> HookResult:
    """Executa hook de tipo 'http' — chama endpoint HTTP."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                hook_cmd.command or "",
                json=context.to_dict(),
            )
            return HookResult.from_response(
                event=context.hook_event_name,
                command=hook_cmd.command or "",
                response=response.json(),
            )
    except Exception as exc:
        return HookResult(
            event=context.hook_event_name,
            command=hook_cmd.command or "",
            status="error",
            error=str(exc),
        )
```

Renomear o método `_execute_command` atual para `_execute_shell_command`.

### Resultado Fase 4

- ✅ `command` type: shell commands (existente)
- ✅ `prompt` type: LLM evaluation (novo)
- ✅ `agent` type: sub-agent execution (novo)
- ✅ `http` type: webhook calls (novo)

---

## 8. Fase 5: Event Broadcasting (1 dia)

### 8.1 Criar `event_broadcaster.py`

**Arquivo:** `python/mindflow_backend/hooks/event_broadcaster.py`

```python
"""HookEventBroadcaster — Sistema de broadcast de eventos de hook.

Emite eventos para UI e transcript persistence.
Equivalente de hookEvents.ts do Claude Code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable
import uuid

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HookExecutionState(StrEnum):
    """Estado de execução de um hook."""
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"


@dataclass
class HookExecutionEvent:
    """Evento de execução de hook — emitido para UI/transcript."""
    state: HookExecutionState
    hook_id: str
    hook_name: str
    hook_event: str
    stdout: str | None = None
    stderr: str | None = None
    output: str | None = None
    exit_code: int | None = None
    outcome: str | None = None


class HookEventBroadcaster:
    """Singleton que emite eventos de execução de hooks.

    Handlers podem registrar para receber eventos e decidir
    o que fazer (ex: converter para SDK messages, log, UI update).
    """

    _instance: HookEventBroadcaster | None = None

    def __init__(self) -> None:
        self._handlers: list[Callable[[HookExecutionEvent], Awaitable[None]]] = []
        self._pending_events: list[HookExecutionEvent] = []
        self._all_events_enabled = False

    @classmethod
    def get_instance(cls) -> HookEventBroadcaster:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, handler: Callable[[HookExecutionEvent], Awaitable[None]]) -> None:
        """Registra um handler para receber eventos."""
        self._handlers.append(handler)

    def enable_all_events(self) -> None:
        """Habilita emissão de todos os eventos (não apenas lifecycle)."""
        self._all_events_enabled = True

    async def emit(self, event: HookExecutionEvent) -> None:
        """Emite um evento para todos os handlers registrados."""
        if not self._handlers:
            self._pending_events.append(event)
            return

        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as exc:
                _logger.warning(
                    "hook_event_handler_error",
                    handler=str(handler),
                    error=str(exc),
                )

    def drain_pending(self) -> list[HookExecutionEvent]:
        """Retorna e limpa eventos pendentes."""
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events
```

### 8.2 Integrar no `manager.py`

No método `execute()`, emitir eventos:

```python
async def execute(self, event, context, *, match_query=None, timeout=...):
    from mindflow_backend.hooks.event_broadcaster import (
        HookEventBroadcaster,
        HookExecutionEvent,
        HookExecutionState,
    )

    broadcaster = HookEventBroadcaster.get_instance()
    matchers = self._registry.get_hooks_for_event(event, ...)

    for matcher in matchers:
        for hook_cmd in matcher.hooks:
            hook_id = str(uuid.uuid4())
            hook_name = hook_cmd.command or "<function>"

            # Emit STARTED
            await broadcaster.emit(HookExecutionEvent(
                state=HookExecutionState.STARTED,
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=str(event),
            ))

            # Execute
            result = await self._execute_command(hook_cmd, context, timeout)

            # Emit COMPLETED
            await broadcaster.emit(HookExecutionEvent(
                state=HookExecutionState.COMPLETED,
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=str(event),
                stdout=result.raw_output,
                exit_code=0 if result.status == "success" else 1,
                outcome=result.status,
            ))

            yield result
```

### Resultado Fase 5

- ✅ Event broadcasting ativo
- ✅ `HookStartedEvent`, `HookProgressEvent`, `HookResponseEvent`
- ✅ UI pode mostrar progresso de hooks
- ✅ Transcript persistence habilitada

---

## 9. Fase 6: Session Lifecycle Integration (1 dia)

### 9.1 Modificar `runtime/core/agent_runtime.py`

**Arquivo:** `python/mindflow_backend/runtime/core/agent_runtime.py`

```python
# Adicionar imports:
from mindflow_backend.hooks.handlers.session_start import SessionStartHandler
from mindflow_backend.hooks.handlers.session_end import SessionEndHandler
from mindflow_backend.hooks.handlers.user_prompt_submit import UserPromptSubmitHandler


class AgentRuntime:
    # ... existing code ...

    async def start_session(self, session_id: str) -> None:
        """Iniciar sessão com hooks SessionStart + InstructionsLoaded."""
        # ... existing initialization code ...

        # Executar SessionStart hooks
        async for result in SessionStartHandler.execute(session_id=session_id):
            if result.add_context:
                self._session_context.add_hook_context(result.add_context)

    async def end_session(self, session_id: str, reason: str) -> None:
        """Encerrar sessão com hooks SessionEnd."""
        # Executar SessionEnd hooks
        async for result in SessionEndHandler.execute(
            session_id=session_id,
            reason=reason,
        ):
            pass  # SessionEnd hooks não retornam contexto

        # ... existing cleanup code ...

    async def handle_user_prompt(self, session_id: str, prompt: str) -> None:
        """Processar prompt com hooks UserPromptSubmit."""
        async for result in UserPromptSubmitHandler.execute(session_id=session_id):
            if result.add_context:
                self._session_context.add_hook_context(result.add_context)

        # ... existing prompt handling ...
```

### Resultado Fase 6

- ✅ SessionStart hooks executados automaticamente
- ✅ SessionEnd hooks executados automaticamente
- ✅ UserPromptSubmit hooks executados automaticamente
- ✅ Ciclo de vida completo integrado

---

## 10. Mapa de Arquivos

### Arquivos Modificados (9)

| # | Arquivo | Fase | Descrição |
|---|---------|------|-----------|
| 1 | `runtime/execution/streaming_executor.py` | 1 | Corrigir integração de hooks |
| 2 | `hooks/builtin/__init__.py` | 1 | Auto-registro de builtin hooks |
| 3 | `hooks/types.py` | 2 | 14 → 27 eventos |
| 4 | `hooks/context.py` | 2 | Novos campos para novos eventos |
| 5 | `hooks/manager.py` | 2,4,5 | Novos execute_* + hook types + events |
| 6 | `hooks/helpers.py` | 2 | Novos match_query |
| 7 | `hooks/handlers/__init__.py` | 2 | Novos imports |
| 8 | `infra/config/settings.py` | 3 | Hook loading no startup |
| 9 | `runtime/core/agent_runtime.py` | 6 | Session lifecycle hooks |

### Arquivos Criados (12)

| # | Arquivo | Fase | Descrição |
|---|---------|------|-----------|
| 1 | `hooks/config_loader.py` | 3 | Carregar hooks de settings.yaml |
| 2 | `hooks/plugin_loader.py` | 3 | Carregar hooks de plugins |
| 3 | `hooks/event_broadcaster.py` | 5 | Sistema de broadcast |
| 4 | `hooks/handlers/session_end.py` | 2 | SessionEnd handler |
| 5 | `hooks/handlers/pre_compact.py` | 2 | PreCompact handler |
| 6 | `hooks/handlers/post_compact.py` | 2 | PostCompact handler |
| 7 | `hooks/handlers/notification.py` | 2 | Notification handler |
| 8 | `hooks/handlers/task_lifecycle.py` | 2 | TaskCreated/Completed handlers |
| 9 | `hooks/handlers/stop_failure.py` | 2 | StopFailure handler |
| 10 | `hooks/handlers/config_change.py` | 2 | ConfigChange handler |
| 11 | `hooks/handlers/setup.py` | 2 | Setup handler |
| 12 | `hooks/handlers/file_watcher.py` | 2 | FileChanged/CwdChanged handlers |

### Arquivos Deletados (1)

| # | Arquivo | Fase | Motivo |
|---|---------|------|--------|
| 1 | `hooks/claude_style_hooks.py` | 1 | Sistema redundante |

---

## 11. Cronograma

```
Semana 1:
├── Dia 1-2: Fase 1 (Corrigir integração atual)
├── Dia 3-5: Fase 2 (Adicionar 13 eventos)

Semana 2:
├── Dia 1-2: Fase 3 (Config loading)
├── Dia 3-5: Fase 4 (Hook types avançados)

Semana 3:
├── Dia 1:   Fase 5 (Event broadcasting)
├── Dia 2:   Fase 6 (Session lifecycle)
└── Dia 3-5: Testes e validação
```

---

## 12. Validação

### Testes Unitários

Cada fase deve incluir testes:

```python
# tests/unit/hooks/test_new_events.py
class TestNewHookEvents:
    def test_session_end_event_exists(self):
        assert HookEvent.SESSION_END == "SessionEnd"

    def test_pre_compact_handler(self):
        handler = PreCompactHandler()
        # ... test execution

    def test_config_loader(self):
        count = load_hooks_from_settings("/path/to/test_settings.yaml")
        assert count > 0
```

### Testes de Integração

```python
# tests/unit/hooks/test_integration.py
class TestHookIntegration:
    async def test_pre_tool_use_deny_blocks_execution(self):
        # Registrar hook que nega
        # Executar tool
        # Verificar que foi bloqueada

    async def test_updated_input_applied(self):
        # Registrar hook que modifica input
        # Executar tool
        # Verificar que input foi modificado
```

---

## 13. Conclusão

Este plano traz o MindFlow a **90%+ de paridade** com o sistema de hooks do Claude Code, enquanto mantém as vantagens exclusivas:

- **Mission Hooks** (MissionStart/MissionStop)
- **HTTP Hook Type** (webhooks)
- **Function Hooks** (callbacks Python)
- **Separação de Handlers** (mais organizado)

**Total estimado:** 9 arquivos modificados, 12 criados, 1 deletado — **8-12 dias de trabalho**.
