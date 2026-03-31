# Guia de Transição Suave: MindFlow → Claude Code Patterns

**Objetivo:** Garantir zero downtime e zero breaking changes durante a refatoração

---

## 🎯 Princípios de Transição Suave

### 1. Strangler Fig Pattern
Envolver o sistema legado gradualmente, sem substituição abrupta.

```
┌─────────────────────────────────────────┐
│         Sistema Atual (MindFlow)        │
│  ┌───────────────────────────────────┐  │
│  │    Nova Camada (Claude Patterns)  │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │   Core Legado (Preservado)  │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 2. Feature Flags
Todas as novas funcionalidades são opcionais e podem ser desabilitadas.

### 3. Dual-Write Pattern
Durante transição, escrever em ambos os sistemas (legado + novo).

### 4. Backward Compatibility
APIs antigas continuam funcionando indefinidamente.

---

## 🔧 Estratégias de Implementação

### Estratégia 1: Adapter Pattern

**Problema:** Integrar novo PermissionManager sem quebrar código existente.

**Solução:** Criar adapter que funciona com ou sem permissions.

```python
# python/mindflow_backend/runtime/execution/executor.py

class RuntimeExecutor:
    def __init__(self):
        self._permission_manager = None
        
        # Feature flag - permissions são opcionais
        if get_settings().enable_permission_system:
            from mindflow_backend.permissions import get_permission_manager
            self._permission_manager = get_permission_manager()
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        agent_id: str | None = None,
    ) -> Any:
        """Execute tool with optional permission check."""
        
        # Se permission system está habilitado, verificar
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
        
        # Código legado continua funcionando
        return await self._execute_tool_legacy(tool_name, tool_input)
```

**Configuração:**
```bash
# .env - Permissions desabilitadas por default
ENABLE_PERMISSION_SYSTEM=false

# Habilitar quando pronto
ENABLE_PERMISSION_SYSTEM=true
```

### Estratégia 2: Decorator Pattern para Hooks

**Problema:** Adicionar hooks sem modificar código existente.

**Solução:** Decorators opcionais que podem ser habilitados/desabilitados.

```python
# python/mindflow_backend/hooks/decorators.py

from functools import wraps
from typing import Any, Callable

from mindflow_backend.config import get_settings


def with_hooks(tool_name: str):
    """Decorator to add hook support to tool execution."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Feature flag - hooks são opcionais
            if not get_settings().enable_hooks:
                return await func(*args, **kwargs)
            
            # Import lazy para evitar dependência circular
            from mindflow_backend.hooks import get_hook_manager
            
            hook_manager = get_hook_manager()
            
            # Pre-hooks
            await hook_manager.execute_pre_hooks(tool_name, kwargs)
            
            # Execute original function
            result = await func(*args, **kwargs)
            
            # Post-hooks
            await hook_manager.execute_post_hooks(tool_name, result)
            
            return result
        
        return wrapper
    
    return decorator


# Uso - adicionar gradualmente aos tools
@with_hooks("read_file")
async def read_file(path: str) -> str:
    # Código legado não muda
    with open(path) as f:
        return f.read()
```

### Estratégia 3: Facade Pattern para QueryEngine

**Problema:** Integrar QueryEngine sem quebrar agentes existentes.

**Solução:** Facade que funciona com ou sem QueryEngine.

```python
# python/mindflow_backend/context/facade.py

from typing import Any

from mindflow_backend.config import get_settings


class ContextFacade:
    """Facade for context building - works with or without QueryEngine."""
    
    def __init__(self):
        self._query_engine = None
        
        if get_settings().enable_query_engine:
            from mindflow_backend.context import QueryEngine
            self._query_engine = QueryEngine()
    
    async def build_context(
        self,
        query: str,
        session_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Build context using QueryEngine if available, fallback to legacy."""
        
        if self._query_engine:
            # Novo caminho - QueryEngine
            from mindflow_backend.context import QueryContext
            
            query_ctx = QueryContext(
                query=query,
                session_id=session_id,
                **kwargs,
            )
            
            return await self._query_engine.build_context(query_ctx)
        
        # Fallback - método legado
        return await self._build_context_legacy(query, session_id)
    
    async def _build_context_legacy(
        self,
        query: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Legacy context building - preservado para compatibilidade."""
        # Código antigo continua funcionando
        return {"query": query, "session_id": session_id}


# Singleton global
_context_facade = None


def get_context_facade() -> ContextFacade:
    """Get global context facade."""
    global _context_facade
    if _context_facade is None:
        _context_facade = ContextFacade()
    return _context_facade
```

### Estratégia 4: Dual-Write para Task Management

**Problema:** Migrar de RabbitMQ direto para Task abstraction.

**Solução:** Escrever em ambos durante transição.

```python
# python/mindflow_backend/tasks/manager.py

class TaskManager:
    """Task manager with dual-write support."""
    
    def __init__(self):
        self._rabbitmq_publisher = RabbitMQPublisher()
        self._enable_new_tasks = get_settings().enable_new_task_system
    
    async def spawn_task(
        self,
        task_type: TaskType,
        description: str,
        **kwargs,
    ) -> Task:
        """Spawn task with dual-write support."""
        
        # SEMPRE escrever no sistema legado (RabbitMQ)
        await self._rabbitmq_publisher.publish({
            "type": task_type.value,
            "description": description,
            **kwargs,
        })
        
        # Se novo sistema está habilitado, também criar Task
        if self._enable_new_tasks:
            task = await self._create_new_task(
                task_type=task_type,
                description=description,
                **kwargs,
            )
            return task
        
        # Retornar task "fake" para compatibilidade
        return LegacyTaskAdapter(description=description)
```

---

## 🚦 Feature Flags

### Configuração Centralizada

**Arquivo:** `python/mindflow_backend/config/features.py`

```python
"""Feature flags for gradual rollout."""

from pydantic_settings import BaseSettings


class FeatureFlags(BaseSettings):
    """Feature flags configuration."""
    
    # FASE 1
    enable_permission_system: bool = False
    enable_query_engine: bool = False
    
    # FASE 2
    enable_hooks: bool = False
    enable_new_task_system: bool = False
    
    # FASE 3
    enable_command_system: bool = False
    enable_agent_tool: bool = False
    
    # FASE 4
    enable_scheduling: bool = False
    
    class Config:
        env_prefix = "FEATURE_"


def get_feature_flags() -> FeatureFlags:
    """Get feature flags."""
    return FeatureFlags()
```

### Uso em Código

```python
from mindflow_backend.config.features import get_feature_flags

features = get_feature_flags()

if features.enable_permission_system:
    # Usar novo sistema
    pass
else:
    # Usar sistema legado
    pass
```

### Configuração por Ambiente

```bash
# .env.development - Tudo habilitado para testes
FEATURE_ENABLE_PERMISSION_SYSTEM=true
FEATURE_ENABLE_QUERY_ENGINE=true
FEATURE_ENABLE_HOOKS=true

# .env.staging - Rollout gradual
FEATURE_ENABLE_PERMISSION_SYSTEM=true
FEATURE_ENABLE_QUERY_ENGINE=false

# .env.production - Conservador
FEATURE_ENABLE_PERMISSION_SYSTEM=false
FEATURE_ENABLE_QUERY_ENGINE=false
```

---

## 📊 Plano de Rollout por Fase

### FASE 1: Permission System & QueryEngine

#### Semana 1-2: Desenvolvimento
- Implementar com feature flags desabilitadas
- Testes em ambiente local
- Code review

#### Semana 3: Staging
```bash
# Habilitar apenas em staging
FEATURE_ENABLE_PERMISSION_SYSTEM=true
FEATURE_ENABLE_QUERY_ENGINE=true
```
- Monitorar métricas
- Testes de carga
- Validar backward compatibility

#### Semana 4: Canary Deployment
```bash
# Habilitar para 10% do tráfego em produção
FEATURE_ENABLE_PERMISSION_SYSTEM=true  # 10% dos requests
```
- Monitorar erros
- Comparar performance
- Coletar feedback

#### Semana 5: Full Rollout
```bash
# Habilitar para 100% do tráfego
FEATURE_ENABLE_PERMISSION_SYSTEM=true
FEATURE_ENABLE_QUERY_ENGINE=true
```

### FASE 2-4: Mesmo Padrão
Repetir processo de rollout para cada fase.

---

## 🔍 Monitoramento Durante Transição

### Métricas Críticas

```python
# python/mindflow_backend/monitoring/transition_metrics.py

from prometheus_client import Counter, Histogram

# Contadores de uso
permission_checks_total = Counter(
    "permission_checks_total",
    "Total permission checks",
    ["decision", "tool_name"],
)

legacy_path_total = Counter(
    "legacy_path_total",
    "Requests using legacy path",
    ["component"],
)

new_path_total = Counter(
    "new_path_total",
    "Requests using new path",
    ["component"],
)

# Latência
permission_check_duration = Histogram(
    "permission_check_duration_seconds",
    "Permission check duration",
)

query_engine_duration = Histogram(
    "query_engine_duration_seconds",
    "QueryEngine context building duration",
)
```

### Dashboard de Transição

```yaml
# grafana/transition-dashboard.json
{
  "title": "MindFlow Transition Dashboard",
  "panels": [
    {
      "title": "Legacy vs New Path Usage",
      "targets": [
        "rate(legacy_path_total[5m])",
        "rate(new_path_total[5m])"
      ]
    },
    {
      "title": "Permission Check Performance",
      "targets": [
        "histogram_quantile(0.95, permission_check_duration_seconds)"
      ]
    },
    {
      "title": "Error Rate Comparison",
      "targets": [
        "rate(errors_total{path='legacy'}[5m])",
        "rate(errors_total{path='new'}[5m])"
      ]
    }
  ]
}
```

### Alertas

```yaml
# prometheus/alerts.yml
groups:
  - name: transition
    rules:
      - alert: NewPathErrorRateHigh
        expr: rate(errors_total{path="new"}[5m]) > rate(errors_total{path="legacy"}[5m]) * 1.5
        for: 5m
        annotations:
          summary: "New path error rate is 50% higher than legacy"
          
      - alert: PermissionCheckSlow
        expr: histogram_quantile(0.95, permission_check_duration_seconds) > 0.1
        for: 5m
        annotations:
          summary: "Permission checks taking >100ms at p95"
```

---

## 🧪 Testes de Compatibilidade

### Test Suite de Regressão

```python
# tests/integration/test_backward_compatibility.py

import pytest


@pytest.mark.integration
@pytest.mark.backward_compat
async def test_legacy_api_still_works():
    """Verify legacy API endpoints work unchanged."""
    
    # Test legacy endpoint
    response = await client.post("/api/v1/agents/execute", json={
        "agent_id": "test_agent",
        "query": "test query",
    })
    
    assert response.status_code == 200
    assert "result" in response.json()


@pytest.mark.integration
@pytest.mark.backward_compat
async def test_tool_execution_without_permissions():
    """Verify tools work when permissions are disabled."""
    
    # Disable permissions
    with feature_flag_override(enable_permission_system=False):
        result = await execute_tool("read_file", {"path": "/test.py"})
        assert result is not None


@pytest.mark.integration
@pytest.mark.backward_compat
async def test_context_building_fallback():
    """Verify context building falls back to legacy when QueryEngine disabled."""
    
    with feature_flag_override(enable_query_engine=False):
        context = await build_context("test query", "session1")
        assert "query" in context
        assert context["query"] == "test query"
```

### Smoke Tests em Produção

```python
# tests/smoke/test_production_health.py

@pytest.mark.smoke
async def test_critical_paths_work():
    """Smoke test for critical user paths."""
    
    # Test 1: Agent execution
    result = await execute_agent_query("test query")
    assert result is not None
    
    # Test 2: Memory retrieval
    memories = await retrieve_memories("test query", "session1")
    assert isinstance(memories, list)
    
    # Test 3: Tool execution
    tool_result = await execute_tool("read_file", {"path": "/test.py"})
    assert tool_result is not None
```

---

## 🔄 Rollback Plan

### Rollback Rápido (< 5 minutos)

```bash
# 1. Desabilitar feature flags via environment
kubectl set env deployment/mindflow-api \
  FEATURE_ENABLE_PERMISSION_SYSTEM=false \
  FEATURE_ENABLE_QUERY_ENGINE=false

# 2. Restart pods
kubectl rollout restart deployment/mindflow-api

# 3. Verificar health
kubectl get pods -l app=mindflow-api
```

### Rollback Completo (< 30 minutos)

```bash
# 1. Revert para versão anterior
git revert <commit-hash>

# 2. Build nova imagem
docker build -t mindflow:rollback .

# 3. Deploy
kubectl set image deployment/mindflow-api \
  mindflow=mindflow:rollback

# 4. Verificar
kubectl rollout status deployment/mindflow-api
```

### Rollback de Dados (se necessário)

```sql
-- Se houve migração de schema, reverter
-- Exemplo: remover coluna adicionada
ALTER TABLE permissions DROP COLUMN IF EXISTS new_column;

-- Restaurar backup se necessário
-- (Deve ser raro - evitar mudanças de schema durante transição)
```

---

## 📋 Checklist de Transição Suave

### Antes de Cada Deploy

- [ ] Feature flags configuradas corretamente
- [ ] Testes de regressão passando
- [ ] Smoke tests passando
- [ ] Métricas baseline coletadas
- [ ] Alertas configurados
- [ ] Rollback plan testado
- [ ] Documentação atualizada
- [ ] Equipe notificada

### Durante Deploy

- [ ] Monitorar dashboard em tempo real
- [ ] Verificar logs de erro
- [ ] Comparar métricas com baseline
- [ ] Testar smoke tests em produção
- [ ] Comunicar status para stakeholders

### Após Deploy

- [ ] Validar métricas por 24h
- [ ] Coletar feedback da equipe
- [ ] Documentar issues encontrados
- [ ] Ajustar alertas se necessário
- [ ] Planejar próximo rollout

---

## 🎯 Critérios de Sucesso para Transição Suave

### Métricas Quantitativas

| Métrica | Threshold | Ação se Falhar |
|---------|-----------|----------------|
| Error rate increase | < 5% | Rollback imediato |
| Latency p95 increase | < 10% | Investigar, rollback se > 20% |
| Memory usage increase | < 15% | Monitorar, otimizar |
| CPU usage increase | < 10% | Monitorar, otimizar |
| Backward compat tests | 100% pass | Rollback imediato |

### Métricas Qualitativas

- [ ] Zero breaking changes reportados
- [ ] Zero downtime durante deploy
- [ ] Equipe confiante com mudanças
- [ ] Documentação clara e completa
- [ ] Rollback testado e funcional

---

## 🚨 Plano de Contingência

### Cenário 1: Performance Degradation

**Sintoma:** Latência aumenta > 20%

**Ação:**
1. Desabilitar feature flag imediatamente
2. Investigar bottleneck (profiling)
3. Otimizar código
4. Re-testar em staging
5. Rollout novamente

### Cenário 2: Breaking Changes Descobertos

**Sintoma:** API antiga quebra

**Ação:**
1. Rollback imediato
2. Adicionar teste de regressão
3. Corrigir código
4. Validar backward compatibility
5. Rollout novamente

### Cenário 3: Data Corruption

**Sintoma:** Dados inconsistentes

**Ação:**
1. Rollback imediato
2. Parar writes no novo sistema
3. Restaurar backup se necessário
4. Investigar root cause
5. Adicionar validação de dados
6. Re-testar extensivamente

---

## 📚 Recursos para a Equipe

### Treinamento

- [ ] Workshop: Feature Flags Best Practices
- [ ] Workshop: Strangler Fig Pattern
- [ ] Workshop: Monitoring & Alerting
- [ ] Workshop: Rollback Procedures

### Documentação

- [ ] Runbook: Como fazer rollback
- [ ] Runbook: Como habilitar feature flags
- [ ] Runbook: Como monitorar transição
- [ ] FAQ: Perguntas comuns sobre transição

---

**Próximo:** Iniciar [Fase 1](./PHASE-1-IMPLEMENTATION-GUIDE.md) com confiança!
