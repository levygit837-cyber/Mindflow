# Plano de Integração: Error Recovery, Autocomplete e Feature Flags

## Visão Geral

Baseado na análise da codebase do Claude Code e do MindFlow, este plano detalha a integração de três sistemas essenciais que ainda não existem no MindFlow.

---

## 📁 Estrutura de Diretórios

```
python/mindflow_backend/
│
├── infra/
│   ├── error_handling/
│   │   ├── __init__.py              # ✅ EXISTS
│   │   ├── classifier.py            # ✅ EXISTS
│   │   ├── retry_manager.py         # ✅ EXISTS
│   │   ├── persistent_retry.py      # ✅ EXISTS
│   │   ├── watchdog.py              # ✅ EXISTS
│   │   ├── model_fallback.py        # 🆕 NEW
│   │   └── graceful_degradation.py  # 🆕 NEW
│   │
│   └── resilience/
│       ├── __init__.py              # ✅ EXISTS
│       ├── retry_fallback.py        # ✅ EXISTS
│       ├── circuit_breaker/         # ✅ EXISTS
│       └── remote_config.py         # ✅ EXISTS
│
├── runtime/
│   ├── feature_flags.py             # ✅ EXISTS (needs enhancement)
│   ├── feature_flags_v2.py          # 🆕 NEW
│   ├── autocomplete/                # 🆕 NEW DIRECTORY
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── command_provider.py
│   │   │   ├── file_provider.py
│   │   │   ├── tool_provider.py
│   │   │   └── history_provider.py
│   │   ├── matchers/
│   │   │   ├── __init__.py
│   │   │   ├── fuzzy_matcher.py
│   │   │   └── prefix_matcher.py
│   │   └── cache/
│   │       ├── __init__.py
│   │       └── suggestion_cache.py
│   │
│   └── models/
│       └── model_registry.py        # 🆕 NEW
│
├── api/
│   └── v1/
│       ├── resilience.py            # ✅ EXISTS
│       ├── autocomplete.py          # 🆕 NEW
│       └── feature_flags.py         # 🆕 NEW
│
└── tests/
    └── unit/
        ├── infra/
        │   ├── test_model_fallback.py      # 🆕 NEW
        │   └── test_graceful_degradation.py # 🆕 NEW
        ├── runtime/
        │   ├── test_feature_flags_v2.py    # 🆕 NEW
        │   └── test_autocomplete.py        # 🆕 NEW
        └── api/
            └── test_autocomplete_api.py    # 🆕 NEW
```

---

## 🔄 Fase 1: Error Recovery System (Semanas 1-2)

### 1.1 Model Fallback System

**Responsável por**: `infra/error_handling/model_fallback.py`

#### Como Funciona o Retry com Backoff

```python
def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> float:
    """
    Cálculo do backoff exponencial com jitter:
    
    attempt=0: delay = 1.0 * 2^0 = 1.0s (±25% jitter)
    attempt=1: delay = 1.0 * 2^1 = 2.0s (±25% jitter)
    attempt=2: delay = 1.0 * 2^2 = 4.0s (±25% jitter)
    attempt=3: delay = 1.0 * 2^3 = 8.0s (±25% jitter)
    ...
    Max: 60s
    """
    delay = base_delay * (exponential_base ** attempt)
    delay = min(delay, max_delay)
    
    if jitter:
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)
```

#### Quando Retentar

```python
# Retry em:
- HTTP 429 (Rate Limit)
- HTTP 500 (Internal Server Error)
- HTTP 502 (Bad Gateway)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)
- ConnectionError
- TimeoutError

# NÃO retry em:
- HTTP 400 (Bad Request)
- HTTP 401 (Unauthorized)
- HTTP 403 (Forbidden)
- HTTP 404 (Not Found)
```

#### Model Fallback Chain

```python
# Exemplo de cadeia de fallback:
Primary: "gpt-4"
    ↓ (falha)
Fallback 1: "gpt-3.5-turbo"
    ↓ (falha)
Fallback 2: "claude-3-sonnet"
    ↓ (falha)
Fallback 3: "claude-3-haiku" (último recurso)
```

#### Health Tracking

```python
@dataclass
class ModelHealth:
    model_name: str
    status: ModelStatus  # HEALTHY, DEGRADED, UNAVAILABLE
    failure_count: int
    consecutive_failures: int
    last_failure: float
    last_success: float
    
    # Recovery detection
    recovery_check_interval: float = 300.0  # 5 minutos
    failure_threshold: int = 3  # Após 3 falhas → UNAVAILABLE
```

### 1.2 Graceful Degradation

**Responsável por**: `infra/error_handling/graceful_degradation.py`

#### Níveis de Degradação

```python
class DegradationLevel(Enum):
    FULL = "full"           # Todas features disponíveis
    REDUCED = "reduced"     # Algumas features desabilitadas
    MINIMAL = "minimal"     # Apenas features core
    OFFLINE = "offline"     # Modo cache/offline
```

#### Exemplo de Política

```python
# Semantic Search degrada graciosamente:
policy = DegradationPolicy(
    feature_name="semantic_search",
    degradation_level=DegradationLevel.REDUCED,
    fallback_value=[],  # Retorna lista vazia
    cache_ttl=300.0,    # Cache por 5 minutos
    notify_user=False,  # Sem notificação
    auto_recover=True   # Tenta recuperar automaticamente
)
```

#### Fluxo de Execução

```python
async def execute_with_degradation(feature_name, primary_func, *args):
    # 1. Verifica se feature está degradada
    if feature_name in self._degraded_features:
        return await self._get_fallback(feature_name, policy)
    
    try:
        # 2. Tenta executar função primária
        result = await primary_func(*args)
        
        # 3. Cache resultado bem-sucedido
        self._cache[feature_name] = (result, time.time())
        
        return result
    except Exception as e:
        # 4. Em falha, marca como degradada
        self._degraded_features.add(feature_name)
        
        # 5. Retorna fallback
        return await self._get_fallback(feature_name, policy)
```

### 1.3 Integração com Circuit Breaker

O sistema de Error Recovery será integrado com o Circuit Breaker existente:

```python
# Ordem de execução:
1. Circuit Breaker (verifica se circuito está aberto)
2. Retry com Backoff (tenta novamente)
3. Model Fallback (troca de modelo se necessário)
4. Graceful Degradation (degrada se tudo falhar)
```

---

## 📝 Fase 2: Autocomplete System (Semanas 3-4)

### 2.1 Arquitetura do Autocomplete

```
User Input → Autocomplete Engine → Providers → Suggestions
                                      ↓
                              ┌───────┴───────┐
                              ↓       ↓       ↓
                           Command  File   Tool
                           Provider Provider Provider
```

### 2.2 Providers de Sugestão

#### Command Provider

- Sugere comandos slash (`/help`, `/config`, etc.)
- Match por prefixo
- Score mais alto para match exato

#### File Provider

- Sugere caminhos de arquivo após `@` ou `/`
- Suporte a navegação de diretórios
- Indica se é arquivo ou diretório

#### Tool Provider

- Sugere nomes de ferramentas disponíveis
- Match por similaridade
- Inclui descrição da ferramenta

#### History Provider

- Sugere comandos do histórico
- Ordenado por recência
- Deduplicação automática

### 2.3 Matchers

#### Fuzzy Matcher

```python
def fuzzy_match(query: str, candidate: str) -> float:
    """
    Match fuzzy que permite caracteres fora de ordem.
    
    Exemplo:
    - query: "redfil"
    - candidate: "read_file"
    - score: 0.85 (match forte)
    """
```

#### Prefix Matcher

```python
def prefix_match(query: str, candidate: str) -> float:
    """
    Match por prefixo exato.
    
    Exemplo:
    - query: "/hel"
    - candidate: "/help"
    - score: 0.75
    """
```

### 2.4 Cache de Sugestões

```python
class SuggestionCache:
    """
    Cache LRU para sugestões de autocomplete.
    
    - TTL: 60 segundos
    - Max entries: 1000
    - Invalidação: automática após TTL
    """
```

### 2.5 API Endpoint

```python
@router.post("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(request: AutocompleteRequest):
    """
    POST /api/v1/autocomplete
    
    Request:
    {
        "input_text": "/hel",
        "cursor_position": 4,
        "session_id": "abc123",
        "mode": "chat"
    }
    
    Response:
    {
        "suggestions": [
            {
                "text": "/help",
                "display_text": "/help",
                "description": "Show help information",
                "category": "command",
                "score": 1.0
            }
        ],
        "latency_ms": 12
    }
    """
```

---

## 🚩 Fase 3: Feature Flags System (Semanas 5-6)

### 3.1 Melhorias no Sistema Existente

O sistema atual (`runtime/feature_flags.py`) será expandido para suportar:

1. **Rollout Percentage**: Ativar feature para X% dos usuários
2. **User Targeting**: Ativar para usuários específicos
3. **Session Consistency**: Mesmo usuário sempre vê mesma versão
4. **A/B Testing**: Suporte a experimentos
5. **Dependencies**: Flags podem depender de outras flags

### 3.2 Como Funciona o Rollout Percentage

```python
def is_enabled_with_rollout(flag_name: str, session_id: str, percentage: float) -> bool:
    """
    Determina se flag está baseada em rollout percentage.
    
    Usa hash consistente para garantir que mesmo
    usuário sempre veja mesma versão.
    
    Exemplo:
    - flag_name: "ENABLE_NEW_UI"
    - session_id: "user-123"
    - percentage: 50.0
    
    hash_input = "ENABLE_NEW_UI:user-123"
    hash_value = md5(hash_input) % 100
    
    return hash_value < percentage
    """
    hash_input = f"{flag_name}:{session_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    bucket = (hash_value % 100) + 1
    return bucket <= percentage
```

### 3.3 Feature Dependencies

```python
@dataclass
class FeatureFlag:
    name: str
    dependencies: list[str]  # Flags que devem estar ativas
    
# Exemplo:
flag = FeatureFlag(
    name="ENABLE_ADVANCED_ANALYTICS",
    dependencies=["ENABLE_BASIC_ANALYTICS", "ENABLE_TELEMETRY"]
)

# ENABLE_ADVANCED_ANALYTICS só será True se:
# - ENABLE_BASIC_ANALYTICS == True
# - ENABLE_TELEMETRY == True
# - ENABLE_ADVANCED_ANALYTICS.rollout_percentage atingido
```

### 3.4 A/B Testing

```python
# Configuração de experimento:
experiment = {
    "name": "new_search_algorithm",
    "variants": {
        "control": {"weight": 50, "config": {"algorithm": "old"}},
        "treatment": {"weight": 50, "config": {"algorithm": "new"}}
    }
}

# Seleção consistente de variante:
variant = select_variant(experiment, session_id)
# Usuário sempre verá mesma variante
```

### 3.5 API para Gerenciamento

```python
@router.get("/features")
async def list_features():
    """Lista todas as feature flags."""
    
@router.post("/features/{flag_name}/override")
async def override_feature(flag_name: str, enabled: bool):
    """Override local de uma feature flag."""
    
@router.get("/features/{flag_name}/status")
async def feature_status(flag_name: str):
    """Status detalhado de uma feature flag."""
```

---

## 📅 Cronograma de Implementação

| Semana | Fase | Entregáveis |
|--------|------|-------------|
| 1 | Error Recovery | Model Fallback Manager |
| 2 | Error Recovery | Graceful Degradation + Testes |
| 3 | Autocomplete | Engine + Command/File Providers |
| 4 | Autocomplete | Tool/History Providers + API |
| 5 | Feature Flags | Feature Flag V2 + Rollout |
| 6 | Feature Flags | A/B Testing + API |
| 7 | Integração | Testes E2E + Documentação |

---

## 🎯 Métricas de Sucesso

### Error Recovery

- 99.5% de sucesso em retries
- < 5% de falhas visíveis ao usuário
- Recuperação automática em < 5 minutos

### Autocomplete

- < 50ms latency para sugestões
- > 80% de precisão em matches
- > 90% de satisfação do usuário

### Feature Flags

- 100% de cobertura de features novas
- Rollout sem downtime
- A/B testing com significância estatística

---

## 🔧 Configuração

### Environment Variables

```bash
# Error Recovery
MINDFLOW_MAX_RETRIES=3
MINDFLOW_RETRY_BASE_DELAY=1.0
MINDFLOW_RETRY_MAX_DELAY=60.0

# Autocomplete
MINDFLOW_AUTOCOMPLETE_ENABLED=true
MINDFLOW_AUTOCOMPLETE_CACHE_TTL=60
MINDFLOW_AUTOCOMPLETE_MAX_RESULTS=10

# Feature Flags
MINDFLOW_FEATURE_FLAGS_ENABLED=true
MINDFLOW_FEATURE_OVERRIDES='{"FLAG_NAME": true}'
```

### Config File

```yaml
# config/resilience.yaml
error_recovery:
  retry:
    max_retries: 3
    base_delay: 1.0
    max_delay: 60.0
    exponential_base: 2.0
    jitter: true
  
  model_fallback:
    chains:
      primary: ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"]
      fast: ["gpt-3.5-turbo", "claude-3-haiku"]
  
  graceful_degradation:
    features:
      - name: "semantic_search"
        level: "reduced"
        fallback_value: []
```

---

## 📚 Referências

- Claude Code: `services/api/withRetry.ts` - Sistema de retry
- Claude Code: `services/api/errors.ts` - Classificação de erros
- Claude Code: `services/analytics/growthbook.ts` - Feature flags
- Claude Code: `hooks/useTypeahead.tsx` - Autocomplete
- MindFlow: `infra/resilience/` - Circuit breaker existente
- MindFlow: `infra/error_handling/` - Error classifier existente
- MindFlow: `runtime/feature_flags.py` - Feature flags básico

---

**Data**: 03/04/2026
**Status**: PLANEJAMENTO APROVADO
**Próxima Fase**: Implementação do Error Recovery System
