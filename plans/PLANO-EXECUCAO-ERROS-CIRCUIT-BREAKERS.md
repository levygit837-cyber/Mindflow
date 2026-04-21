# Plano de Execução: Erros e Circuit Breakers MindFlow

**Data:** 2 de Abril de 2026 | **Duração:** 6 semanas | **Equipe:** 1-2 devs

## Estrutura de Arquivos

```
python/mindflow_backend/
├── infra/error_handling/classifier.py ← MODIFICAR
├── infra/resilience/
│   ├── __init__.py ← MODIFICAR
│   ├── retry_fallback.py ← NOVO
│   ├── remote_config.py ← NOVO
│   └── circuit_breaker/
│       ├── core.py ← MANTER
│       ├── enhanced.py ← MODIFICAR
│       └── metrics.py ← MODIFICAR
├── exceptions/base/core_new.py ← MODIFICAR
├── api/v1/resilience_dashboard.py ← NOVO
└── tests/
    ├── unit/infra/test_error_classifier.py ← NOVO
    └── integration/test_resilience_patterns.py ← NOVO
```

## FASE 1: Fundação (Semanas 1-2)

### 1.1 Classificador de Erros Expandido

**Arquivo:** `infra/error_handling/classifier.py`

Adicionar categorias: CAPACITY, AUTH_TRANSIENT, TOOL_ERROR, MEMORY_ERROR, CONTEXT_OVERFLOW
Adicionar severidade: WARNING, ERROR, CRITICAL

### 1.2 Métricas de Performance

**Arquivo:** `infra/resilience/circuit_breaker/metrics.py`

Implementar: P95/P99 latency, error rate por janela, throughput, distribuição de erros

### 1.3 Testes Unitários

**Arquivo:** `tests/unit/infra/test_error_classifier.py`

## FASE 2: Integração (Semanas 3-4)

### 2.1 Feature Flags

**Arquivo NOVO:** `infra/resilience/remote_config.py`
Integração com GrowthBook/LaunchDarkly

### 2.2 Retry com Fallback

**Arquivo NOVO:** `infra/resilience/retry_fallback.py`
with_retry_and_fallback() com exponential backoff + jitter

### 2.3 Exceção RetryableError

**Arquivo:** `exceptions/base/core_new.py`
Adicionar retry_count, max_retries, next_retry_delay, fallback_available

## FASE 3: Monitoramento (Semanas 5-6)

### 3.1 Dashboard de Resiliência

**Arquivo NOVO:** `api/v1/resilience_dashboard.py`
Endpoint /resilience/dashboard/overview

### 3.2 Adaptive Thresholds

**Arquivo:** `infra/resilience/circuit_breaker/enhanced.py`
Ajuste automático de limites

## Checklist

### Fase 1

- [ ] ErrorCategory expandido
- [ ] ErrorSeverity implementado
- [ ] ErrorClassification dataclass
- [ ] classify_error() atualizado
- [ ] PerformanceMetrics
- [ ] Testes unitários

### Fase 2

- [ ] RemoteCircuitBreakerConfig
- [ ] with_retry_and_fallback()
