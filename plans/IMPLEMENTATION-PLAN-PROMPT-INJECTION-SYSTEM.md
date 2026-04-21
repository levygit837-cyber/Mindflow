# Plano de Implementação: Sistema de Injeção e Montagem de Prompts (MindFlow)

**Data:** 2026-01-04
**Baseado em:** `plans/ANALISE-SISTEMA-PROMPTS-CLAUDE-VS-MINDFLOW.md`
**Objetivo:** Implementar sistema de injeção e montagem de prompts multi-camada inspirado no Claude Code, compatível com a estrutura existente do MindFlow.

---

## Análise do Estado Atual

### Componentes JÁ EXISTENTES no MindFlow (aproveitar)

| Componente | Arquivo | Status |
|---|---|---|
| `QueryEngine` com `TokenBudget` | `query/engine.py` | ✅ Completo |
| `ContextProvider` protocol + `GitProvider`, `FileProvider`, `MemoryProvider` | `query/providers/` | ✅ Implementado |
| `ToolPromptInjector` (formato XML) | `agents/tools/tool_injection.py` | ✅ Implementado |
| `DynamicPromptBuilder` com `PromptContext` | `agents/specialists/dynamic_prompts.py` | ✅ Implementado |
| `AgentRuntimePolicy._inject_tool_descriptions()` | `agents/specialists/runtime_policy.py` | ✅ Parcial |
| `build_system_prompt()` (Preamble+Personality+Persistence) | `agents/prompts/base.py` | ✅ Básico |
| `compose_orchestrator_prompt()` (segmentos nomeados) | `agents/prompts/core/orchestrator.py` | ✅ Funcional |
| `TokenBudget` com tiktoken + trim por prioridade | `query/budget/token_counter.py` | ✅ Completo |
| `CLAUDE.md` memory loading | Hooks `session_start` | ✅ Parcial |

### Lacunas a Implementar

| Gap | Impacto | Fase |
|---|---|---|
| **PromptAssembler** unificado (pipeline multi-camada) | ALTO | Fase 1 |
| **Context Injection** (datetime, OS, shell, CWD) | ALTO | Fase 1 |
| **Git Status Injection** integrado ao prompt | MÉDIO | Fase 2 |
| **Integração ToolPromptInjector** no pipeline | ALTO | Fase 1 |
| **Sistema de Prioridades** | MÉDIO | Fase 2 |
| **Prompt Caching** em blocos | ALTO | Fase 3 |
| **Cache Invalidation** por contexto | MÉDIO | Fase 3 |
| **MCP Context Injection** | BAIXO | Fase 4 |

---

## Mapeamento: Claude Code → MindFlow

| Conceito Claude Code | Equivalente MindFlow | Arquivo |
|---|---|---|
| `getSystemPrompt()` | `BasePromptLayer` + `ToolDescriptionLayer` | `agents/prompts/layers/` |
| `getUserContext()` | `EnvironmentLayer` | `agents/prompts/layers/environment.py` |
| `getSystemContext()` | `GitContextLayer` | `agents/prompts/layers/git.py` |
| `buildEffectiveSystemPrompt()` | `PromptAssembler.assemble()` | `agents/prompts/assembler.py` |
| `buildSystemPromptBlocks()` | `PromptCacheManager.build_blocks()` | `agents/prompts/cache.py` |
| `ToolPromptInjector` (já existe) | Usado pela `ToolDescriptionLayer` | `agents/tools/tool_injection.py` |
| `QueryEngine` (já existe) | Mantido | `query/engine.py` |
| `TokenBudget` (já existe) | Mantido | `query/budget/token_counter.py` |
| `ContextProvider` (já existe) | Mantido | `query/providers/` |
| `clearSessionCaches()` | `CacheInvalidator` | `agents/prompts/cache.py` |

---

## Fase 1: PromptAssembler + Context Injection + Tool Integration

**Duração estimada:** 1 semana
**Objetivo:** Criar pipeline central que substitui concatenações lineares por montagem multi-camada, integrando context injection e tool injection.

### 1.1 Criar `PromptAssembler` (novo módulo)

**Arquivo:** `python/mindflow_backend/agents/prompts/assembler.py`

Equivalente ao `buildEffectiveSystemPrompt()` do Claude Code.

```python
"""PromptAssembler — pipeline multi-camada de montagem de system prompt.

Inspired by Claude Code's buildEffectiveSystemPrompt():
- Camada 1: Base (Preamble + Personality + Persistence)
- Camada 2: Tool Descriptions (via ToolPromptInjector)
- Camada 3: Environment Context (datetime, OS, shell, CWD)
- Camada 4: Git Context (branch, staged files)
- Camada 5: Memory/MCP Context
- Camada 6: Additional Instructions
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mindflow_backend.agents._base import BaseAgent


@runtime_checkable
class PromptLayer(Protocol):
    """Protocol for prompt layers."""
    name: str
    priority: int

    async def render(self, context: "AssemblyContext") -> str | None: ...


@dataclass
class AssemblyContext:
    """Context passed to all layers during assembly."""
    agent: "BaseAgent | None" = None
    working_directory: str | None = None
    query: str | None = None
    mcp_clients: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class PromptAssembler:
    """Pipeline multi-camada de montagem de system prompt."""

    def __init__(self) -> None:
        self._layers: list[PromptLayer] = []

    def add_layer(self, layer: PromptLayer) -> "PromptAssembler":
        """Adiciona camada ao pipeline (builder pattern)."""
        self._layers.append(layer)
        self._layers.sort(key=lambda l: -l.priority)
        return self

    async def assemble(self, context: AssemblyContext | None = None) -> str:
        """Monta o prompt final com todas as camadas."""
        ctx = context or AssemblyContext()
        parts: list[str] = []

        for layer in self._layers:
            try:
                result = await layer.render(ctx)
                if result:
                    parts.append(result)
            except Exception:
                # Log but don't fail the entire assembly
                import logging
                logging.getLogger(__name__).warning(
                    f"Layer '{layer.name}' failed during assembly"
                )

        return "\n\n".join(parts)

    def assemble_sync(self, context: AssemblyContext | None = None) -> str:
        """Versão síncrona para backward compatibility."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.assemble(context))
        # If already in an event loop, use a task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                lambda: asyncio.run(self.assemble(context))
            ).result()
```

### 1.2 Criar estrutura de layers

**Arquivo:** `python/mindflow_backend/agents/prompts/layers/__init__.py`

```python
"""Prompt layers for the multi-camada assembly system."""

from mindflow_backend.agents.prompts.layers.base import BasePromptLayer
from mindflow_backend.agents.prompts.layers.environment import EnvironmentLayer
from mindflow_backend.agents.prompts.layers.tools import ToolDescriptionLayer
from mindflow_backend.agents.prompts.layers.git import GitContextLayer
from mindflow_backend.agents.prompts.layers.memory import MemoryFileLayer

__all__ = [
    "BasePromptLayer",
    "EnvironmentLayer",
    "ToolDescriptionLayer",
    "GitContextLayer",
    "MemoryFileLayer",
]
```

### 1.3 Criar `BasePromptLayer`

**Arquivo:** `python/mindflow_backend/agents/prompts/layers/base.py`

```python
"""Base prompt layer — Preamble + Personality + Persistence."""

from __future__ import annotations

from mindflow_backend.agents.prompts.base import (
    MINDFLOW_PREAMBLE,
    PERSISTENCE_DIRECTIVE,
    build_system_prompt,
)


class BasePromptLayer:
    """Camada base do prompt (Preamble + Personality + Persistence)."""
    name = "base"
    priority = 100  # Máxima prioridade

    def __init__(self, personality: str = "") -> None:
        self._personality = personality

    async def render(self, context: "AssemblyContext") -> str:
        if self._personality:
            return build_system_prompt(self._personality)
        return f"{MINDFLOW_PREAMBLE}\n\n{PERSISTENCE_DIRECTIVE}"
```

### 1.4 Criar `EnvironmentLayer` (Context Injection)

**Arquivo:** `python/mindflow_backend/agents/prompts/layers/environment.py`

Equivalente ao `getUserContext()` do Claude Code.

```python
"""Environment context layer — injects OS, shell, datetime, CWD.

Equivalent to Claude Code's getUserContext() in context.ts.
Returns: datetime, OS, shell, CWD, timezone.
"""

from __future__ import annotations

import os
import platform
from datetime import datetime, timezone


class EnvironmentLayer:
    """Injeta contexto do ambiente no system prompt."""
    name = "environment"
    priority = 80  # Alta prioridade

    async def render(self, context: "AssemblyContext") -> str:
        now = datetime.now(timezone.utc)
        working_dir = context.working_directory or os.getcwd()
        shell = os.environ.get("SHELL", "unknown")

        return (
            f"## Environment Details\n\n"
            f"Current Date: {now.strftime('%Y-%m-%d')}\n"
            f"Current Time: {now.strftime('%H:%M:%S')} UTC\n"
            f"Operating System: {platform.system()} {platform.release()}\n"
            f"Shell: {shell}\n"
            f"Working Directory: {working_dir}\n"
            f"Platform: {platform.platform()}"
        )
```

### 1.5 Criar `ToolDescriptionLayer`

**Arquivo:** `python/mindflow_backend/agents/prompts/layers/tools.py`

Integra o `ToolPromptInjector` existente no pipeline.

```python
"""Tool description layer — wraps existing ToolPromptInjector."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mindflow_backend.agents.tools.tool_injection import ToolPromptInjector


class ToolDescriptionLayer:
    """Camada de descrição de ferramentas (XML format)."""
    name = "tools"
    priority = 90  # Alta prioridade

    def __init__(self, injector: "ToolPromptInjector | None" = None) -> None:
        self._injector = injector

    async def render(self, context: "AssemblyContext") -> str | None:
        if context.agent is None or self._injector is None:
            return None

        descriptions = self._injector.generate_tool_descriptions(context.agent)
        usage = self._injector.generate_usage_instructions(context.agent)

        parts = []
        if descriptions:
            parts.append(descriptions)
        if usage:
            parts.append(usage)

        return "\n\n".join(parts) if parts else None
```

### 1.6 Criar `GitContextLayer`

**Arquivo:** `python/mindflow_backend/agents/prompts/layers/git.py`

```python
"""Git context layer — injects git status into system prompt.

Uses existing GitProvider to fetch git info.
"""

from __future__ import annotations


class GitContextLayer:
    """Injeta status do git no system prompt."""
    name = "git"
    priority = 70  # Prioridade média-alta

    async def render(self, context: "AssemblyContext") -> str | None:
        working_dir = context.working_directory
        if not working_dir:
            return None

        try:
            from mindflow_backend.query.providers.git_provider import GitProvider
            provider = GitProvider()
            git_info = await provider.fetch("", max_tokens=500)
            if not git_info:
                return None
            return f"## Git Status\n\n{git_info}"
        except Exception:
            return None
```

### 1.7 Criar `MemoryFileLayer`

**Arquivo:** `python/mindflow_backend/agents/prompts/layers/memory.py`

```python
"""Memory file layer — loads CLAUDE.md / MINDFLOW.md files.

Equivalent to Claude Code's memory file loading.
"""

from __future__ import annotations

import os
from pathlib import Path


class MemoryFileLayer:
    """Carrega arquivos de memória do projeto e do usuário."""
    name = "memory"
    priority = 85  # Alta prioridade

    async def render(self, context: "AssemblyContext") -> str | None:
        working_dir = context.working_directory or os.getcwd()
        content_parts: list[str] = []

        # Project memory: .mindflow/CLAUDE.md or CLAUDE.md
        project_memory = self._find_project_memory(working_dir)
        if project_memory:
            content_parts.append(project_memory)

        # User global memory: ~/.mindflow/CLAUDE.md
        user_memory = self._find_user_memory()
        if user_memory:
            content_parts.append(user_memory)

        if not content_parts:
            return None

        return "## Project Memory\n\n" + "\n\n".join(content_parts)

    def _find_project_memory(self, working_dir: str) -> str | None:
        """Find project-level memory files."""
        candidates = [
            Path(working_dir) / ".mindflow" / "CLAUDE.md",
            Path(working_dir) / "CLAUDE.md",
            Path(working_dir) / ".claude" / "CLAUDE.md",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except Exception:
                    continue
        return None

    def _find_user_memory(self) -> str | None:
        """Find user-level memory files."""
        home = Path.home()
        candidates = [
            home / ".mindflow" / "CLAUDE.md",
            home / ".claude" / "CLAUDE.md",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except Exception:
                    continue
        return None
```

### 1.8 Refatorar `build_system_prompt()` em `base.py`

**Modificação:** `python/mindflow_backend/agents/prompts/base.py`

Adicionar `build_assembled_prompt()` mantendo backward compatibility:

```python
async def build_assembled_prompt(
    personality_prompt: str = "",
    agent: "BaseAgent | None" = None,
    working_directory: str | None = None,
    include_tools: bool = True,
    include_environment: bool = True,
    include_git: bool = False,
    include_memory: bool = True,
    tool_injector: "ToolPromptInjector | None" = None,
) -> str:
    """NOVO: Monta prompt usando PromptAssembler multi-camada."""
    from mindflow_backend.agents.prompts.assembler import (
        AssemblyContext,
        PromptAssembler,
    )
    from mindflow_backend.agents.prompts.layers.base import BasePromptLayer
    from mindflow_backend.agents.prompts.layers.environment import EnvironmentLayer
    from mindflow_backend.agents.prompts.layers.git import GitContextLayer
    from mindflow_backend.agents.prompts.layers.memory import MemoryFileLayer
    from mindflow_backend.agents.prompts.layers.tools import ToolDescriptionLayer

    assembler = PromptAssembler()
    assembler.add_layer(BasePromptLayer(personality_prompt))

    if include_tools:
        assembler.add_layer(ToolDescriptionLayer(tool_injector))

    if include_environment:
        assembler.add_layer(EnvironmentLayer())

    if include_git:
        assembler.add_layer(GitContextLayer())

    if include_memory:
        assembler.add_layer(MemoryFileLayer())

    context = AssemblyContext(
        agent=agent,
        working_directory=working_directory,
    )
    return await assembler.assemble(context)
```

### 1.9 Integrar no `AgentRuntimePolicy.build_agent()`

**Modificação:** `python/mindflow_backend/agents/specialists/runtime_policy.py`

Atualizar `build_agent()` para usar o pipeline unificado quando possível:

```python
def build_agent(self) -> BaseAgent:
    """Create the concrete runtime agent from the policy."""
    # LEGACY: Injeta tool descriptions diretamente
    enhanced_prompt = self._inject_tool_descriptions(self.system_prompt)
    return BaseAgent(
        agent_role=self.agent_role,
        specialist=self.specialist,
        system_prompt=enhanced_prompt,
        tools=self.tools,
        sandbox=self.sandbox,
        thinking_level=self.thinking_level,
        keep_context=self.keep_context,
        max_iterations=self.max_iterations,
    )

async def build_agent_assembled(self) -> BaseAgent:
    """NOVO: Cria agente usando PromptAssembler multi-camada."""
    from mindflow_backend.agents.prompts.base import build_assembled_prompt
    from mindflow_backend.agents.tools import create_default_registry

    registry = create_default_registry(sandbox_mode=self.sandbox)
    from mindflow_backend.agents.tools.tool_injection import ToolPromptInjector
    injector = ToolPromptInjector(registry)

    assembled_prompt = await build_assembled_prompt(
        personality_prompt=self.system_prompt,
        include_tools=True,
        include_environment=True,
        include_git=True,
        include_memory=True,
        tool_injector=injector,
    )

    return BaseAgent(
        agent_role=self.agent_role,
        specialist=self.specialist,
        system_prompt=assembled_prompt,
        tools=self.tools,
        sandbox=self.sandbox,
        thinking_level=self.thinking_level,
        keep_context=self.keep_context,
        max_iterations=self.max_iterations,
    )
```

### 1.10 Arquivos da Fase 1

| Ação | Arquivo |
|---|---|
| CRIAR | `agents/prompts/assembler.py` |
| CRIAR | `agents/prompts/layers/__init__.py` |
| CRIAR | `agents/prompts/layers/base.py` |
| CRIAR | `agents/prompts/layers/environment.py` |
| CRIAR | `agents/prompts/layers/tools.py` |
| CRIAR | `agents/prompts/layers/git.py` |
| CRIAR | `agents/prompts/layers/memory.py` |
| MODIFICAR | `agents/prompts/base.py` — adicionar `build_assembled_prompt()` |
| MODIFICAR | `agents/prompts/__init__.py` — exportar novos símbolos |
| MODIFICAR | `agents/specialists/runtime_policy.py` — adicionar `build_agent_assembled()` |
| CRIAR | `tests/unit/agents/prompts/test_assembler.py` |

---

## Fase 2: Git Status Injection + Priority System

**Duração estimada:** 1 semana
**Objetivo:** Injetar status do git no prompt e implementar sistema de prioridades para overrides.

### 2.1 Melhorar `GitContextLayer`

O `GitContextLayer` básico já é criado na Fase 1. Na Fase 2, melhorar com:

- Formatação mais rica (branch, staged, unstaged, remotes)
- Cache por working directory
- Detecção de mudanças

### 2.2 Implementar Priority System

**Modificação:** `agents/prompts/assembler.py`

Adicionar suporte a overrides e append:

```python
class PromptPriority:
    """Sistema de prioridades para montagem de prompt."""
    OVERRIDE = 0       # Substitui TODO o prompt
    COORDINATOR = 1    # Modo coordenador
    AGENT_DEFINITION = 2  # Agent definition
    CUSTOM = 3         # Custom system prompt
    DEFAULT = 4        # Default system prompt
    APPEND = 5         # Sempre adicionado no final
```

### 2.3 Integrar com `compose_orchestrator_prompt()`

**Modificação:** `agents/prompts/core/orchestrator.py`

Adaptar para usar o `PromptAssembler` internamente mantendo API de segmentos.

### 2.4 Arquivos da Fase 2

| Ação | Arquivo |
|---|---|
| MODIFICAR | `agents/prompts/layers/git.py` — melhorar formatação e cache |
| MODIFICAR | `agents/prompts/assembler.py` — adicionar Priority System |
| MODIFICAR | `agents/prompts/core/orchestrator.py` — integrar com assembler |
| MODIFICAR | `runtime/execution/executor.py` — passar working_directory |
| CRIAR | `tests/unit/agents/prompts/test_priority.py` |

---

## Fase 3: Prompt Caching + Cache Invalidation

**Duração estimada:** 1 semana
**Objetivo:** Implementar cache de blocos de prompt para reduzir tokens de input.

### 3.1 Prompt Block System

**Arquivo:** `python/mindflow_backend/agents/prompts/blocks.py`

```python
@dataclass
class PromptBlock:
    """Bloco de prompt para caching."""
    content: str
    cache_key: str
    cache_control: str | None = None  # "ephemeral" para caching
    token_count: int = 0
```

### 3.2 Prompt Cache Manager

**Arquivo:** `python/mindflow_backend/agents/prompts/cache.py`

Divide prompt em blocos cacheáveis:

- Global Block: Preamble + Personality (raramente muda)
- Tools Block: Descrições de ferramentas (muda com escopo)
- Context Block: Git, Environment (muda a cada chamada)
- Memory Block: CLAUDE.md (muda quando arquivo muda)

### 3.3 Cache Invalidation

```python
class CacheInvalidator:
    """Gerencia invalidação de cache de prompt."""
    
    def invalidate_on_context_change(self, session_id: str, change_type: str):
        """Invalida caches quando contexto muda.
        
        change_types:
        - 'git_status' → invalida git block
        - 'tool_scope' → invalida tools block
        - 'memory_file' → invalida memory block
        - 'clear_session' → invalida TUDO
        """
        ...
```

### 3.4 Arquivos da Fase 3

| Ação | Arquivo |
|---|---|
| CRIAR | `agents/prompts/blocks.py` |
| CRIAR | `agents/prompts/cache.py` |
| MODIFICAR | `agents/prompts/assembler.py` — integrar cache manager |
| CRIAR | `tests/unit/agents/prompts/test_cache.py` |

---

## Fase 4: MCP Context + Session Tracking + Memory File Loading

**Duração estimada:** 1 semana
**Objetivo:** Completar sistema com MCP context, tracking de sessão e memory loading avançado.

### 4.1 MCPLayer

```python
class MCPLayer(PromptLayer):
    """Injeta contexto de servidores MCP conectados."""
    name = "mcp"
    priority = 60
```

### 4.2 SessionTracker

```python
class SessionTracker:
    """Rastreia estado da sessão para cache e contexto."""
    
    def has_context_changed(self, new_context: dict) -> bool:
        """Verifica se contexto mudou desde última montagem."""
        ...
```

### 4.3 Arquivos da Fase 4

| Ação | Arquivo |
|---|---|
| CRIAR | `agents/prompts/layers/mcp.py` |
| CRIAR | `agents/prompts/session_tracker.py` |
| MODIFICAR | `agents/prompts/assembler.py` — integrar novas camadas |
| CRIAR | `tests/unit/agents/prompts/test_session_tracker.py` |

---

## Fluxo Final do Pipeline

```
Usuario envia mensagem
        │
        ▼
PromptAssembler.assemble()
├── BasePromptLayer (Preamble + Personality + Persistence)
│   └── Usa build_system_prompt() existente
├── ToolDescriptionLayer (XML format)
│   └── Usa ToolPromptInjector existente
├── EnvironmentLayer (datetime, OS, shell, CWD)
│   └── NOVO
├── GitContextLayer (branch, staged files)
│   └── Usa GitProvider existente
├── MemoryFileLayer (CLAUDE.md / MINDFLOW.md)
│   └── NOVO
├── MCPLayer (servidores MCP)
│   └── NOVO (Fase 4)
└── AdditionalInstructionsLayer
    └── Instruções dinâmicas
        │
        ▼
PromptCacheManager.build_blocks() (Fase 3)
├── [Global Block] ← cache_control: ephemeral
├── [Tools Block] ← cache_control: ephemeral
├── [Context Block] ← SEM cache (dinâmico)
└── [Memory Block] ← cache_control: ephemeral
        │
        ▼
