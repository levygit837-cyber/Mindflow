# Planning Trigger System - Complete Guide

## Overview

The Planning Trigger System uses LLM-based semantic analysis to intelligently determine when a user request requires decomposition into a structured TODO-list, replacing keyword-based matching with contextual understanding.

## Architecture

```
User Request
    ↓
should_trigger_planning_hybrid()
    ↓
┌─────────────────────────────────────┐
│ Feature Flag Check                  │
│ ENABLE_LLM_PLANNING_TRIGGER         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Cache Check (1ms)                   │
│ Hash message → lookup               │
└─────────────────────────────────────┘
    ↓ (miss)
┌─────────────────────────────────────┐
│ LLM Analysis (800ms)                │
│ Semantic understanding              │
│ Confidence scoring                  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Cache Decision (TTL: 1h)            │
│ Track Metrics (PostgreSQL)          │
└─────────────────────────────────────┘
    ↓
Planning Decision
```

## Quick Start

### 1. Enable LLM Trigger

```bash
export ENABLE_LLM_PLANNING_TRIGGER=true
```

### 2. Apply Database Migration

```bash
psql -U postgres -d mindflow_v1 -f python/mindflow_backend/orchestrator/planning/migrations/001_create_metrics_table.sql
```

### 3. Restart Backend

```bash
cd python
uv run mindflow-api
```

## Features

### Semantic Analysis

**Before (Keywords)**:
- "Implementar sistema" → ✅ Triggers (keyword match)
- "Preciso de uma solução robusta para gerenciar usuários" → ❌ Doesn't trigger

**After (LLM)**:
- "Implementar sistema" → ✅ Triggers (semantic understanding)
- "Preciso de uma solução robusta para gerenciar usuários" → ✅ Triggers (understands intent)

### Caching

- **First call**: ~800ms (LLM)
- **Subsequent calls**: ~1ms (cache hit)
- **TTL**: 1 hour (configurable)

### Metrics

Track:
- Trigger decisions
- User confirmations
- Execution completions
- Latency
- Method used (llm/fallback/legacy)

## API Endpoints

### Get Metrics Summary

```bash
GET /api/v1/planning/metrics/summary?hours=24
```

Response:
```json
{
  "time_window_hours": 24,
  "total_triggers": 15,
  "total_decisions": 20,
  "confirmation_rate": 0.8,
  "completion_rate": 0.75,
  "avg_latency_ms": 850.5,
  "avg_confidence": 0.82,
  "method_distribution": {
    "llm": 12,
    "fallback": 3
  }
}
```

### Cache Stats

```bash
GET /api/v1/planning/metrics/cache/stats
```

Response:
```json
{
  "cache_size": 42,
  "ttl_hours": 1.0
}
```

### Clear Cache

```bash
POST /api/v1/planning/metrics/cache/clear
```

## Configuration

### Environment Variables

```bash
# Enable LLM trigger (default: false)
ENABLE_LLM_PLANNING_TRIGGER=true

# LLM provider (default: google)
DEFAULT_PROVIDER=google

# LLM model (default: gemini-3.1-flash-lite-preview)
DEFAULT_MODEL=gemini-3.1-flash-lite-preview
```

### Cache TTL

```python
from mindflow_backend.orchestrator.planning.cache import PlanningDecisionCache
from datetime import timedelta

# Custom TTL
cache = PlanningDecisionCache(ttl=timedelta(hours=2))
```

## Monitoring

### Key Metrics

1. **Confirmation Rate**: % of triggered plans confirmed by users
   - Target: > 80%
   - Low rate indicates false positives

2. **Completion Rate**: % of confirmed plans completed
   - Target: > 70%
   - Low rate indicates planning quality issues

3. **Avg Latency**: Average decision time
   - Target: < 1000ms
   - High latency impacts UX

4. **Cache Hit Rate**: % of decisions from cache
   - Target: > 30%
   - Low rate indicates diverse requests

### Alerts

Set up alerts for:
- Confirmation rate < 70%
- Avg latency > 2000ms
- Fallback rate > 20%

## Troubleshooting

### High Latency

**Symptom**: Avg latency > 2000ms

**Solutions**:
1. Check LLM provider status
2. Increase cache TTL
3. Use faster model (e.g., gemini-flash)

### Low Confirmation Rate

**Symptom**: Confirmation rate < 70%

**Solutions**:
1. Review false positives in logs
2. Adjust system prompt
3. Increase confidence threshold

### Cache Not Working

**Symptom**: Cache size = 0

**Solutions**:
1. Check cache is enabled
2. Verify messages are normalized
3. Check TTL not too short

## Development

### Run Tests

```bash
cd python
uv run pytest tests/orchestrator/planning/ -v
```

### Add New Test

```python
@pytest.mark.asyncio
async def test_my_scenario(analyzer):
    request = PlanningAnalysisRequest(
        message="My test message"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is True
    assert decision.confidence >= 0.7
```

### Debug Decisions

```python
from mindflow_backend.orchestrator.planning.analyzer import get_planning_analyzer

analyzer = get_planning_analyzer()
decision = await analyzer.should_trigger_planning(request)

print(f"Decision: {decision.requires_planning}")
print(f"Confidence: {decision.confidence}")
print(f"Reasoning: {decision.reasoning}")
print(f"Factors: {decision.complexity_factors}")
```

## Migration from Legacy

### Phase 1: A/B Testing (Current)

```bash
# Enable LLM trigger
ENABLE_LLM_PLANNING_TRIGGER=true

# Both methods run, comparison logged
# Metrics tracked separately
```

### Phase 2: LLM Only (Recommended)

```bash
# Keep flag enabled
ENABLE_LLM_PLANNING_TRIGGER=true

# Monitor metrics for 1 week
# Validate confirmation rate > 80%
```

### Phase 3: Remove Legacy Code

```python
# Delete should_trigger_planning() (keyword-based)
# Keep only should_trigger_planning_v2()
# Remove feature flag
```

## Performance

### Benchmarks

| Scenario | Latency | Cost |
|---|---|---|
| Cache hit | ~1ms | $0 |
| LLM call | ~800ms | $0.0001 |
| Fallback | ~5ms | $0 |

### Optimization Tips

1. **Increase cache TTL** for stable workloads
2. **Use faster model** if latency critical
3. **Batch requests** if possible
4. **Monitor cache hit rate** and adjust

## Security

### API Keys

- Never commit API keys
- Use environment variables
- Rotate keys regularly

### Data Privacy

- Messages are hashed for cache keys
- Metrics don't store message content
- PostgreSQL data encrypted at rest

## Support

### Logs

```bash
# View planning decisions
grep "planning_decision" logs/app.log

# View cache hits
grep "cache_hit" logs/app.log

# View metrics
grep "planning_trigger_tracked" logs/app.log
```

### Common Issues

1. **"LLM unavailable"**: Check API keys and provider status
2. **"Cache expired"**: Normal, TTL reached
3. **"Fallback mode"**: LLM failed, using heuristics

## Changelog

### v1.0.0 (2026-03-18)

- ✅ LLM-based semantic analysis
- ✅ Decision caching (800x faster)
- ✅ PostgreSQL persistence
- ✅ Metrics tracking
- ✅ API endpoints
- ✅ Feature flag support
