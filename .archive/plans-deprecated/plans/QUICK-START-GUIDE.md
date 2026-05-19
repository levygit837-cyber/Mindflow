# Quick Start: Iniciando a Refatoração (Fase 1)

**Objetivo:** Guia prático para começar a implementação HOJE

---

## 🚀 Setup Inicial (30 minutos)

### 1. Criar Estrutura de Diretórios

```bash
cd python/mindflow_backend

# Criar estrutura para Fase 1
mkdir -p permissions/{handlers,policies,storage}
mkdir -p context/{providers,budget}
mkdir -p config

# Criar __init__.py files
touch permissions/__init__.py
touch permissions/handlers/__init__.py
touch permissions/policies/__init__.py
touch permissions/storage/__init__.py
touch context/__init__.py
touch context/providers/__init__.py
touch context/budget/__init__.py
```

### 2. Criar Feature Flags

**Arquivo:** `python/mindflow_backend/config/features.py`

```python
"""Feature flags for gradual rollout."""

from pydantic_settings import BaseSettings


class FeatureFlags(BaseSettings):
    """Feature flags configuration."""
    
    # FASE 1
    enable_permission_system: bool = False
    enable_query_engine: bool = False
    
    # FASE 2 (para o futuro)
    enable_hooks: bool = False
    enable_new_task_system: bool = False
    
    class Config:
        env_prefix = "FEATURE_"


_feature_flags = None


def get_feature_flags() -> FeatureFlags:
    """Get feature flags singleton."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags
```

### 3. Atualizar .env

```bash
# Adicionar ao .env
echo "# Feature Flags - Fase 1" >> .env
echo "FEATURE_ENABLE_PERMISSION_SYSTEM=false" >> .env
echo "FEATURE_ENABLE_QUERY_ENGINE=false" >> .env
```

### 4. Criar Branch de Feature

```bash
# Criar branch para Fase 1
git checkout -b feature/phase-1-permissions-context

# Criar branches para sub-features
git checkout -b feature/phase-1-permissions
git checkout -b feature/phase-1-query-engine
```

---

## 📝 Dia 1: Implementar Types (2-3 horas)

### Tarefa 1.1: Criar Permission Types

**Arquivo:** `python/mindflow_backend/permissions/types.py`

```python
"""Permission system types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PermissionMode(str, Enum):
    """Permission modes for tool execution."""
    
    AUTO = "auto"
    PROMPT = "prompt"
    DENY = "deny"
    POLICY = "policy"


class PermissionDecision(str, Enum):
    """Permission decision outcomes."""
    
    ALLOW = "allow"
    DENY = "deny"
    PROMPT = "prompt"


@dataclass(frozen=True)
class PermissionContext:
    """Context for permission checks."""
    
    tool_name: str
    tool_input: dict[str, Any]
    agent_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class PermissionResult:
    """Result of a permission check."""
    
    decision: PermissionDecision
    reason: str | None = None
    metadata: dict[str, Any] | None = None
    
    @property
    def allowed(self) -> bool:
        """Check if permission was granted."""
        return self.decision == PermissionDecision.ALLOW
```

### Tarefa 1.2: Criar Testes

**Arquivo:** `python/tests/unit/permissions/test_types.py`

```python
import pytest
from mindflow_backend.permissions.types import (
    PermissionContext,
    PermissionDecision,
    PermissionResult,
)


@pytest.mark.unit
def test_permission_result_allowed():
    result = PermissionResult(decision=PermissionDecision.ALLOW)
    assert result.allowed is True


@pytest.mark.unit
def test_permission_result_denied():
    result = PermissionResult(decision=PermissionDecision.DENY)
    assert result.allowed is False


@pytest.mark.unit
def test_permission_context_immutable():
    ctx = PermissionContext(
        tool_name="read_file",
        tool_input={"path": "/test.py"},
    )
    
    with pytest.raises(AttributeError):
        ctx.tool_name = "write_file"
```

### Tarefa 1.3: Rodar Testes

```bash
# Rodar testes
uv run pytest tests/unit/permissions/test_types.py -v

# Verificar coverage
uv run pytest tests/unit/permissions/test_types.py --cov=mindflow_backend.permissions.types
```

### ✅ Checklist Dia 1

- [ ] Estrutura de diretórios criada
- [ ] Feature flags implementadas
- [ ] Permission types implementados
- [ ] Testes unitários criados
- [ ] Testes passando
- [ ] Coverage > 90%
- [ ] Code review solicitado

---

## 📝 Dia 2: Base Handler Protocol (2-3 horas)

### Tarefa 2.1: Criar Base Handler

**Arquivo:** `python/mindflow_backend/permissions/handlers/base.py`

```python
"""Base permission handler protocol."""

from typing import Protocol

from mindflow_backend.permissions.types import (
    PermissionContext,
    PermissionResult,
)


class PermissionHandler(Protocol):
    """Protocol for permission handlers."""
    
    async def check(self, context: PermissionContext) -> PermissionResult:
        """Check if operation is permitted."""
        ...
    
    def matches(self, tool_name: str) -> bool:
        """Check if this handler applies to the tool."""
        ...
```

### Tarefa 2.2: Criar File Handler

**Arquivo:** `python/mindflow_backend/permissions/handlers/file_handler.py`

```python
"""File access permission handler."""

import re
from pathlib import Path

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.permissions.types import (
    PermissionContext,
    PermissionDecision,
    PermissionResult,
)

logger = get_logger(__name__)


class FilePermissionHandler:
    """Handle file access permissions."""
    
    TOOL_PATTERN = re.compile(r"^(read_file|write_file|edit_file|glob|grep)$")
    
    def __init__(
        self,
        allowed_paths: list[str] | None = None,
        denied_paths: list[str] | None = None,
    ):
        self._allowed_paths = allowed_paths or []
        self._denied_paths = denied_paths or [
            "/etc/passwd",
            "/etc/shadow",
            "~/.ssh/*",
            "*.key",
            "*.pem",
        ]
    
    def matches(self, tool_name: str) -> bool:
        """Check if this handler applies to the tool."""
        return bool(self.TOOL_PATTERN.match(tool_name))
    
    async def check(self, context: PermissionContext) -> PermissionResult:
        """Check file access permission."""
        file_path = context.tool_input.get("path") or context.tool_input.get("file_path")
        
        if not file_path:
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason="No file path provided",
            )
        
        # Check denied paths first
        if self._is_denied_path(file_path):
            logger.warning(
                "file_access_denied",
                extra={"path": file_path, "tool": context.tool_name},
            )
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason=f"Access to {file_path} is denied by policy",
            )
        
        # Check allowed paths
        if self._allowed_paths and not self._is_allowed_path(file_path):
            return PermissionResult(
                decision=PermissionDecision.PROMPT,
                reason=f"Path {file_path} not in allowed list",
            )
        
        return PermissionResult(
            decision=PermissionDecision.ALLOW,
            metadata={"path": file_path},
        )
    
    def _is_denied_path(self, path: str) -> bool:
        """Check if path matches denied patterns."""
        path_obj = Path(path).expanduser().resolve()
        
        for pattern in self._denied_paths:
            if path_obj.match(pattern):
                return True
        
        return False
    
    def _is_allowed_path(self, path: str) -> bool:
        """Check if path matches allowed patterns."""
        if not self._allowed_paths:
            return True
        
        path_obj = Path(path).expanduser().resolve()
        
        for pattern in self._allowed_paths:
            if path_obj.match(pattern):
                return True
        
        return False
```

### ✅ Checklist Dia 2

- [ ] Base handler protocol criado
- [ ] FilePermissionHandler implementado
- [ ] Testes unitários criados
- [ ] Testes passando
- [ ] Coverage > 85%
- [ ] Code review solicitado

---

## 📝 Dia 3-4: Permission Manager (4-6 horas)

### Tarefa 3.1: Implementar PermissionManager

**Arquivo:** `python/mindflow_backend/permissions/manager.py`

```python
"""Permission manager - core permission system."""

from __future__ import annotations

import asyncio
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.resilience.circuit_breaker import CircuitBreaker
from mindflow_backend.permissions.handlers.base import PermissionHandler
from mindflow_backend.permissions.types import (
    PermissionContext,
    PermissionDecision,
    PermissionMode,
    PermissionResult,
)

logger = get_logger(__name__)


class PermissionManager:
    """Manage tool execution permissions."""
    
    def __init__(
        self,
        mode: PermissionMode = PermissionMode.PROMPT,
        handlers: list[PermissionHandler] | None = None,
    ):
        self._mode = mode
        self._handlers = handlers or []
        self._circuit_breaker = CircuitBreaker(
            name="permission_manager",
            failure_threshold=5,
            recovery_timeout=30.0,
        )
        self._cache: dict[str, PermissionResult] = {}
        self._lock = asyncio.Lock()
    
    def register_handler(self, handler: PermissionHandler) -> None:
        """Register a permission handler."""
        self._handlers.append(handler)
        logger.info(
            "permission_handler_registered",
            extra={"handler": type(handler).__name__},
        )
    
    async def check_permission(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> PermissionResult:
        """Check if tool execution is permitted."""
        context = PermissionContext(
            tool_name=tool_name,
            tool_input=tool_input,
            agent_id=agent_id,
            session_id=session_id,
        )
        
        # Check cache
        cache_key = self._make_cache_key(context)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Execute check with circuit breaker
        try:
            result = await self._circuit_breaker.execute(
                lambda: self._do_check(context)
            )
            
            # Cache result
            async with self._lock:
                self._cache[cache_key] = result
            
            return result
            
        except Exception as exc:
            logger.error(
                "permission_check_failed",
                extra={"tool": tool_name, "error": str(exc)},
                exc_info=True,
            )
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason=f"Permission check failed: {exc}",
            )
    
    async def _do_check(self, context: PermissionContext) -> PermissionResult:
        """Perform actual permission check."""
        if self._mode == PermissionMode.AUTO:
            return PermissionResult(decision=PermissionDecision.ALLOW)
        
        if self._mode == PermissionMode.DENY:
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason="Permission mode is DENY",
            )
        
        handler = self._find_handler(context.tool_name)
        
        if handler:
            return await handler.check(context)
        
        if self._mode == PermissionMode.PROMPT:
            return PermissionResult(
                decision=PermissionDecision.PROMPT,
                reason="No handler found, prompting user",
            )
        
        return PermissionResult(decision=PermissionDecision.ALLOW)
    
    def _find_handler(self, tool_name: str) -> PermissionHandler | None:
        """Find handler for tool."""
        for handler in self._handlers:
            if handler.matches(tool_name):
                return handler
        return None
    
    def _make_cache_key(self, context: PermissionContext) -> str:
        """Create cache key from context."""
        return f"{context.tool_name}:{context.agent_id}:{context.session_id}"
    
    def clear_cache(self) -> None:
        """Clear permission cache."""
        self._cache.clear()


# Singleton
_permission_manager = None


def get_permission_manager() -> PermissionManager:
    """Get global permission manager."""
    global _permission_manager
    if _permission_manager is None:
        from mindflow_backend.permissions.handlers.file_handler import FilePermissionHandler
        
        _permission_manager = PermissionManager(
            mode=PermissionMode.AUTO,  # Default to AUTO for now
            handlers=[FilePermissionHandler()],
        )
    return _permission_manager
```

### Tarefa 3.2: Criar __init__.py

**Arquivo:** `python/mindflow_backend/permissions/__init__.py`

```python
"""Permission system for MindFlow."""

from .manager import PermissionManager, get_permission_manager
from .types import (
    PermissionContext,
    PermissionDecision,
    PermissionMode,
    PermissionResult,
)

__all__ = [
    "PermissionManager",
    "get_permission_manager",
    "PermissionContext",
    "PermissionDecision",
    "PermissionMode",
    "PermissionResult",
]
```

### ✅ Checklist Dia 3-4

- [ ] PermissionManager implementado
- [ ] Singleton pattern implementado
- [ ] Circuit breaker integrado
- [ ] Cache implementado
- [ ] Testes unitários criados
- [ ] Testes de integração criados
- [ ] Coverage > 85%
- [ ] Code review solicitado

---

## 📝 Dia 5: Integração com Runtime (3-4 horas)

### Tarefa 5.1: Modificar RuntimeExecutor

**Arquivo:** `python/mindflow_backend/runtime/execution/executor.py`

```python
# Adicionar no início
from mindflow_backend.config.features import get_feature_flags
from mindflow_backend.permissions import get_permission_manager

class RuntimeExecutor:
    def __init__(self):
        # ... código existente ...
        
        # Adicionar permission manager (opcional via feature flag)
        self._permission_manager = None
        if get_feature_flags().enable_permission_system:
            self._permission_manager = get_permission_manager()
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        agent_id: str | None = None,
    ) -> Any:
        """Execute tool with optional permission check."""
        
        # Check permission if enabled
        if self._permission_manager:
            permission_result = await self._permission_manager.check_permission(
                tool_name=tool_name,
                tool_input=tool_input,
                agent_id=agent_id,
            )
            
            if not permission_result.allowed:
                raise PermissionError(
                    f"Tool execution denied: {permission_result.reason}"
                )
        
        # Execute tool (código existente)
        return await self._execute_tool_impl(tool_name, tool_input)
```

### Tarefa 5.2: Testes de Integração

**Arquivo:** `python/tests/integration/test_permission_integration.py`

```python
import pytest
from mindflow_backend.config.features import get_feature_flags
from mindflow_backend.runtime.execution.executor import RuntimeExecutor


@pytest.mark.integration
async def test_executor_with_permissions_disabled():
    """Test executor works when permissions are disabled."""
    # Permissions disabled by default
    executor = RuntimeExecutor()
    
    # Should work without permission check
    result = await executor.execute_tool(
        tool_name="read_file",
        tool_input={"path": "/test.py"},
    )
    
    assert result is not None


@pytest.mark.integration
async def test_executor_with_permissions_enabled(monkeypatch):
    """Test executor checks permissions when enabled."""
    # Enable permissions
    monkeypatch.setenv("FEATURE_ENABLE_PERMISSION_SYSTEM", "true")
    
    executor = RuntimeExecutor()
    
    # Should check permissions
    # (This test needs more setup - just a skeleton)
    pass
```

### ✅ Checklist Dia 5

- [ ] RuntimeExecutor modificado
- [ ] Feature flag integrado
- [ ] Backward compatibility mantida
- [ ] Testes de integração criados
- [ ] Testes passando
- [ ] Code review solicitado

---

## 📊 Métricas de Progresso

### Acompanhar Diariamente

```bash
# Test coverage
uv run pytest --cov=mindflow_backend.permissions --cov-report=term-missing

# Code quality
uv run ruff check python/mindflow_backend/permissions/

# Type checking
uv run mypy python/mindflow_backend/permissions/
```

### Targets

- **Test Coverage:** 85%+
- **Ruff Score:** 10/10
- **Mypy:** 0 errors

---

## 🎯 Próximos Passos (Semana 2)

Após completar Dia 1-5:

1. **Dia 6-7:** Implementar BashPermissionHandler
2. **Dia 8-9:** Implementar AgentPermissionHandler
3. **Dia 10:** Criar API endpoints
4. **Dia 11-12:** QueryEngine básico
5. **Dia 13-14:** Integração final e testes
6. **Dia 15:** Code review e ajustes

---

## 🚨 Troubleshooting

### Problema: Testes não passam

```bash
# Verificar imports
uv run python -c "from mindflow_backend.permissions import get_permission_manager"

# Verificar pytest
uv run pytest --collect-only

# Rodar com verbose
uv run pytest -vv
```

### Problema: Feature flags não funcionam

```bash
# Verificar .env
cat .env | grep FEATURE_

# Verificar se está sendo lido
uv run python -c "from mindflow_backend.config.features import get_feature_flags; print(get_feature_flags())"
```

### Problema: Import errors

```bash
# Verificar __init__.py files
find python/mindflow_backend/permissions -name "__init__.py"

# Adicionar se faltando
touch python/mindflow_backend/permissions/__init__.py
```

---

## ✅ Checklist Final da Semana 1

- [ ] Todos os dias 1-5 completados
- [ ] Todos os testes passando
- [ ] Coverage > 85%
- [ ] Code review aprovado
- [ ] Feature flags funcionando
- [ ] Backward compatibility verificada
- [ ] Documentação atualizada
- [ ] Demo para a equipe

---

**Próximo:** [Semana 2 - Completar Fase 1](./PHASE-1-IMPLEMENTATION-GUIDE.md)
