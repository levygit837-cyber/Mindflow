# FASE 1: Guia de Implementação - Permission System & Context Management

**Status:** READY TO START  
**Prioridade:** CRÍTICA  
**Duração Estimada:** 2-3 semanas  
**Owner:** TBD

---

## 🎯 Objetivos da Fase 1

1. Implementar sistema de permissões granular inspirado no Claude Code
2. Criar QueryEngine para gerenciamento de contexto
3. Estabelecer fundação de segurança para todas as tools
4. Manter 100% backward compatibility

---

## 📋 Parte 1.1: Permission System

### Arquitetura Proposta

```
python/mindflow_backend/permissions/
├── __init__.py                 # Public API
├── types.py                    # Enums, dataclasses
├── manager.py                  # PermissionManager (core)
├── context.py                  # PermissionContext
├── handlers/
│   ├── __init__.py
│   ├── base.py                 # BasePermissionHandler (Protocol)
│   ├── tool_handler.py         # Generic tool permissions
│   ├── file_handler.py         # File access permissions
│   ├── bash_handler.py         # Command execution permissions
│   ├── agent_handler.py        # Agent spawning permissions
│   └── mcp_handler.py          # MCP tool permissions
├── policies/
│   ├── __init__.py
│   ├── default.py              # Default policies
│   ├── allowlist.py            # Path allowlists
│   └── denylist.py             # Blocked operations
└── storage/
    ├── __init__.py
    └── permission_store.py     # Persist permission decisions
```

### Implementação Passo a Passo

#### Step 1: Criar Types (Day 1)

**Arquivo:** `python/mindflow_backend/permissions/types.py`

```python
"""Permission system types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PermissionMode(str, Enum):
    """Permission modes for tool execution."""
    
    AUTO = "auto"           # Auto-approve all
    PROMPT = "prompt"       # Ask user for each tool
    DENY = "deny"           # Deny all by default
    POLICY = "policy"       # Use policy-based decisions


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


@dataclass(frozen=True)
class PermissionPolicy:
    """Permission policy definition."""
    
    name: str
    tool_pattern: str  # Regex pattern for tool names
    decision: PermissionDecision
    conditions: dict[str, Any] | None = None
```

**Testes:** `tests/unit/permissions/test_types.py`

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
        ctx.tool_name = "write_file"  # Should fail - frozen dataclass
```

#### Step 2: Criar Base Handler Protocol (Day 1)

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
        """Check if operation is permitted.
        
        Args:
            context: Permission context with tool info
            
        Returns:
            PermissionResult with decision
        """
        ...
    
    def matches(self, tool_name: str) -> bool:
        """Check if this handler applies to the tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if handler should process this tool
        """
        ...
```

#### Step 3: Implementar File Handler (Day 2)

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
        """Initialize file permission handler.
        
        Args:
            allowed_paths: List of allowed path patterns
            denied_paths: List of denied path patterns
        """
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
                extra={
                    "path": file_path,
                    "tool": context.tool_name,
                    "reason": "denied_path",
                },
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
            return True  # No restrictions if no allowed paths
        
        path_obj = Path(path).expanduser().resolve()
        
        for pattern in self._allowed_paths:
            if path_obj.match(pattern):
                return True
        
        return False
```

**Testes:** `tests/unit/permissions/handlers/test_file_handler.py`

```python
import pytest
from mindflow_backend.permissions.handlers.file_handler import FilePermissionHandler
from mindflow_backend.permissions.types import (
    PermissionContext,
    PermissionDecision,
)


@pytest.mark.unit
async def test_file_handler_allows_normal_file():
    handler = FilePermissionHandler()
    
    context = PermissionContext(
        tool_name="read_file",
        tool_input={"path": "/home/user/project/test.py"},
    )
    
    result = await handler.check(context)
    assert result.decision == PermissionDecision.ALLOW


@pytest.mark.unit
async def test_file_handler_denies_sensitive_file():
    handler = FilePermissionHandler()
    
    context = PermissionContext(
        tool_name="read_file",
        tool_input={"path": "/etc/passwd"},
    )
    
    result = await handler.check(context)
    assert result.decision == PermissionDecision.DENY
    assert "denied by policy" in result.reason


@pytest.mark.unit
async def test_file_handler_prompts_for_unlisted_path():
    handler = FilePermissionHandler(
        allowed_paths=["/home/user/project/*"]
    )
    
    context = PermissionContext(
        tool_name="write_file",
        tool_input={"path": "/tmp/output.txt"},
    )
    
    result = await handler.check(context)
    assert result.decision == PermissionDecision.PROMPT
```

#### Step 4: Implementar PermissionManager (Day 3-4)

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
        """Initialize permission manager.
        
        Args:
            mode: Default permission mode
            handlers: List of permission handlers
        """
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
        """Check if tool execution is permitted.
        
        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            agent_id: Optional agent ID
            session_id: Optional session ID
            
        Returns:
            PermissionResult with decision
        """
        context = PermissionContext(
            tool_name=tool_name,
            tool_input=tool_input,
            agent_id=agent_id,
            session_id=session_id,
        )
        
        # Check cache first
        cache_key = self._make_cache_key(context)
        if cache_key in self._cache:
            logger.debug("permission_cache_hit", extra={"tool": tool_name})
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
            # Fail closed - deny on error
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason=f"Permission check failed: {exc}",
            )
    
    async def _do_check(self, context: PermissionContext) -> PermissionResult:
        """Perform actual permission check."""
        # AUTO mode - allow everything
        if self._mode == PermissionMode.AUTO:
            return PermissionResult(decision=PermissionDecision.ALLOW)
        
        # DENY mode - deny everything
        if self._mode == PermissionMode.DENY:
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason="Permission mode is DENY",
            )
        
        # Find matching handler
        handler = self._find_handler(context.tool_name)
        
        if handler:
            result = await handler.check(context)
            logger.info(
                "permission_checked",
                extra={
                    "tool": context.tool_name,
                    "decision": result.decision.value,
                    "handler": type(handler).__name__,
                },
            )
            return result
        
        # No handler found - default to PROMPT in PROMPT mode
        if self._mode == PermissionMode.PROMPT:
            return PermissionResult(
                decision=PermissionDecision.PROMPT,
                reason="No handler found, prompting user",
            )
        
        # Default to ALLOW if no handler and not in PROMPT mode
        return PermissionResult(decision=PermissionDecision.ALLOW)
    
    def _find_handler(self, tool_name: str) -> PermissionHandler | None:
        """Find handler for tool."""
        for handler in self._handlers:
            if handler.matches(tool_name):
                return handler
        return None
    
    def _make_cache_key(self, context: PermissionContext) -> str:
        """Create cache key from context."""
        # Simple cache key - can be improved
        return f"{context.tool_name}:{context.agent_id}:{context.session_id}"
    
    def clear_cache(self) -> None:
        """Clear permission cache."""
        self._cache.clear()
        logger.info("permission_cache_cleared")
```

**Testes:** `tests/unit/permissions/test_manager.py`

```python
import pytest
from mindflow_backend.permissions.handlers.file_handler import FilePermissionHandler
from mindflow_backend.permissions.manager import PermissionManager
from mindflow_backend.permissions.types import (
    PermissionDecision,
    PermissionMode,
)


@pytest.mark.unit
async def test_permission_manager_auto_mode():
    manager = PermissionManager(mode=PermissionMode.AUTO)
    
    result = await manager.check_permission(
        tool_name="read_file",
        tool_input={"path": "/test.py"},
    )
    
    assert result.decision == PermissionDecision.ALLOW


@pytest.mark.unit
async def test_permission_manager_deny_mode():
    manager = PermissionManager(mode=PermissionMode.DENY)
    
    result = await manager.check_permission(
        tool_name="read_file",
        tool_input={"path": "/test.py"},
    )
    
    assert result.decision == PermissionDecision.DENY


@pytest.mark.unit
async def test_permission_manager_with_handler():
    handler = FilePermissionHandler()
    manager = PermissionManager(
        mode=PermissionMode.POLICY,
        handlers=[handler],
    )
    
    # Should deny sensitive file
    result = await manager.check_permission(
        tool_name="read_file",
        tool_input={"path": "/etc/passwd"},
    )
    
    assert result.decision == PermissionDecision.DENY


@pytest.mark.unit
async def test_permission_manager_caching():
    manager = PermissionManager(mode=PermissionMode.AUTO)
    
    # First call
    result1 = await manager.check_permission(
        tool_name="read_file",
        tool_input={"path": "/test.py"},
        session_id="session1",
    )
    
    # Second call - should hit cache
    result2 = await manager.check_permission(
        tool_name="read_file",
        tool_input={"path": "/test.py"},
        session_id="session1",
    )
    
    assert result1.decision == result2.decision
```

#### Step 5: Integração com Runtime (Day 5-6)

**Modificar:** `python/mindflow_backend/runtime/execution/executor.py`

```python
# Adicionar no início do arquivo
from mindflow_backend.permissions import PermissionManager, get_permission_manager

class RuntimeExecutor:
    def __init__(self):
        # ... código existente ...
        self._permission_manager = get_permission_manager()
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        agent_id: str | None = None,
    ) -> Any:
        """Execute tool with permission check."""
        
        # Check permission first
        permission_result = await self._permission_manager.check_permission(
            tool_name=tool_name,
            tool_input=tool_input,
            agent_id=agent_id,
        )
        
        if not permission_result.allowed:
            raise PermissionError(
                f"Tool execution denied: {permission_result.reason}"
            )
        
        # Execute tool
        # ... código existente de execução ...
```

#### Step 6: API Endpoints (Day 7)

**Criar:** `python/mindflow_backend/api/v1/permissions.py`

```python
"""Permission management API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mindflow_backend.permissions import get_permission_manager
from mindflow_backend.permissions.types import PermissionMode

router = APIRouter(prefix="/permissions", tags=["permissions"])


class PermissionCheckRequest(BaseModel):
    tool_name: str
    tool_input: dict
    agent_id: str | None = None
    session_id: str | None = None


class PermissionCheckResponse(BaseModel):
    allowed: bool
    decision: str
    reason: str | None = None


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(request: PermissionCheckRequest):
    """Check if tool execution is permitted."""
    manager = get_permission_manager()
    
    result = await manager.check_permission(
        tool_name=request.tool_name,
        tool_input=request.tool_input,
        agent_id=request.agent_id,
        session_id=request.session_id,
    )
    
    return PermissionCheckResponse(
        allowed=result.allowed,
        decision=result.decision.value,
        reason=result.reason,
    )


@router.post("/cache/clear")
async def clear_permission_cache():
    """Clear permission cache."""
    manager = get_permission_manager()
    manager.clear_cache()
    return {"status": "ok", "message": "Cache cleared"}
```

---

## 📋 Parte 1.2: Context Management (QueryEngine)

### Implementação Simplificada (Semana 2)

**Arquivo:** `python/mindflow_backend/context/query_engine.py`

```python
"""QueryEngine - Gerenciamento de contexto para queries."""

from dataclasses import dataclass
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory import get_memory_service

logger = get_logger(__name__)


@dataclass
class QueryContext:
    """Context for a query."""
    
    query: str
    session_id: str
    agent_id: str | None = None
    max_tokens: int = 200_000
    include_memory: bool = True
    include_git: bool = True


class QueryEngine:
    """Manage context for agent queries."""
    
    def __init__(self):
        self._memory_service = get_memory_service()
    
    async def build_context(self, query_ctx: QueryContext) -> dict[str, Any]:
        """Build context for query.
        
        Args:
            query_ctx: Query context configuration
            
        Returns:
            Dictionary with context data
        """
        context = {
            "query": query_ctx.query,
            "session_id": query_ctx.session_id,
        }
        
        # Add memory if requested
        if query_ctx.include_memory and self._memory_service:
            memories = await self._memory_service.retrieve_relevant(
                query=query_ctx.query,
                session_id=query_ctx.session_id,
                limit=10,
            )
            context["memories"] = memories
        
        # Add git context if requested
        if query_ctx.include_git:
            # TODO: Implement git context provider
            context["git"] = {}
        
        return context
```

---

## ✅ Checklist de Conclusão da Fase 1

### Parte 1.1: Permission System
- [ ] Types implementados e testados
- [ ] Base handler protocol criado
- [ ] FilePermissionHandler implementado
- [ ] BashPermissionHandler implementado
- [ ] PermissionManager implementado
- [ ] Integração com Runtime
- [ ] API endpoints criados
- [ ] Testes unitários (85%+ coverage)
- [ ] Testes de integração
- [ ] Documentação API

### Parte 1.2: Context Management
- [ ] QueryEngine básico implementado
- [ ] Memory provider integrado
- [ ] Git provider implementado
- [ ] Token counting implementado
- [ ] Testes unitários (80%+ coverage)
- [ ] Documentação

### Geral
- [ ] Code review completo
- [ ] Performance benchmarks
- [ ] Backward compatibility verificada
- [ ] Documentação de migração
- [ ] Deploy em staging
- [ ] Aprovação para Fase 2

---

## 📊 Métricas de Sucesso

- **Test Coverage:** 85%+ para permission system, 80%+ para context
- **Performance:** <100ms overhead por permission check
- **Reliability:** Zero breaking changes em APIs existentes
- **Documentation:** 100% de public APIs documentadas

---

**Próximo:** [FASE 2 - Hooks & Task Management](./PHASE-2-IMPLEMENTATION-GUIDE.md)
