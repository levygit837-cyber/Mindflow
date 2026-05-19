# Codebase Exploration — Implementação do Agent Analyst

## Visão Geral

Este documento descreve a implementação do **Agent Analyst em modo Codebase Exploration** — um workflow exaustivo que usa ferramentas Context+ para mapear completamente um codebase.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                   ANALYST CODEBASE MODE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                SystemPrompt Dinâmico                  │   │
│  │  codebase_exploration.py                              │   │
│  │  - Instruções de ferramentas                          │   │
│  │  - Workflow obrigatório                               │   │
│  │  - Tratamento de falhas                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Orquestrador de Fases                    │   │
│  │  Phase 1: Discovery → Phase 2: Skeleton              │   │
│  │  Phase 3: Deep Analysis → Phase 4: Validation        │   │
│  └──────────────────────────────────────────────────────┘   │
│                    │              │                          │
│         ┌──────────┘              └──────────┐              │
│         ▼                                    ▼              │
│  ┌─────────────────┐              ┌─────────────────────┐  │
│  │  Fallback Engine │              │  Coverage Validator  │  │
│  │  contextplus_    │              │  contextplus_        │  │
│  │  fallback.py     │              │  validator.py        │  │
│  │  - Circuit Break │              │  - File tracking     │  │
│  │  - Retry logic   │              │  - Metrics           │  │
│  │  - Param adapt   │              │  - Thresholds        │  │
│  └─────────────────┘              └─────────────────────┘  │
│                    │                          │              │
│                    ▼                          ▼              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Memory Persistence                   │   │
│  │  search_memory_graph → upsert_memory_node             │   │
│  │  create_relation → retrieve_with_traversal            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Arquivos Criados

### 1. Fallback Engine

**Caminho:** `python/mindflow_backend/agents/tools/contextplus_fallback.py`

**Responsabilidades:**

- Circuit breaker para prevenir falhas em cascata
- Retry logic com exponential backoff
- Fallback automático quando ferramentas semânticas falham
- Métricas de uso e health reporting

**Fallback Chains:**

```python
FALLBACK_CHAINS = {
    "semantic_code_search": ["get_context_tree", "get_file_skeleton"],
    "semantic_identifier_search": ["get_context_tree", "get_file_skeleton"],
    "get_blast_radius": ["search_memory_graph"],
}
```

**Circuit Breaker:**

- 3 falhas consecutivas → circuito abre
- 60 segundos de recovery timeout
- 2 chamadas de teste no half-open

### 2. SystemPrompt Dinâmico

**Caminho:** `python/mindflow_backend/agents/prompts/specialized/codebase_exploration.py`

**Responsabilidades:**

- Prompt completo para modo Codebase Exploration
- Instruções detalhadas de cada ferramenta
- Workflow obrigatório em 4 fases
- Tratamento de falhas com fallbacks
- Formato de saída padronizado
- Relatório final estruturado

**Funções:**

```python
def build_codebase_exploration_prompt(
    scope: str = "full",        # "full", "module", "feature"
    target_path: str = ".",
    min_coverage: float = 95.0,
) -> str
```

### 3. Coverage Validator

**Caminho:** `python/mindflow_backend/agents/tools/contextplus_validator.py`

**Responsabilidades:**

- Tracking de arquivos descobertos vs. analisados
- Métricas de cobertura (funções, classes, métodos)
- Validação contra thresholds configuráveis
- Geração de relatório em Markdown

**Thresholds Padrão:**

```python
min_coverage_percentage = 95.0    # % de arquivos analisados
min_function_coverage = 90.0      # % de funções documentadas
min_class_coverage = 95.0         # % de classes documentadas
max_timeout_rate = 5.0            # % máximo de timeouts
```

## Workflow de Execução

### Phase 1: Discovery (Top-Down)

```
1. search_memory_graph(query="contexto do projeto")
2. get_context_tree(path=".", depth_limit=2)
   → Identificar diretórios principais
3. Para CADA diretório:
   get_context_tree(path=dir, depth_limit=3, include_symbols=true)
4. upsert_memory_node para cada módulo descoberto
5. validator.register_discovered_files([...])
```

### Phase 2: Skeleton Extraction

```
Para CADA arquivo .py/.ts:
1. validator.mark_file_analyzing(path)
2. get_file_skeleton(file_path)
3. Classificar: module|class|function|service
4. upsert_memory_node(type="file", ...)
5. create_relation para imports
6. validator.mark_file_analyzed(path, ...)
   (A cada 5 arquivos: persistir progresso)
```

### Phase 3: Deep Analysis

```
Para arquivos CRÍTICOS:
1. fallback_engine.execute_with_fallback(
       "semantic_identifier_search",
       {"query": concept}
   )
2. get_blast_radius(symbol)
3. Análise de padrões
4. create_relation para conexões
```

### Phase 4: Validation

```
1. run_static_analysis()
2. passed, report = validator.validate()
3. if not passed:
   - get_missing_files()
   - Repeat Phase 2 for missing
4. Gerar relatório final (report.to_markdown())
```

## Tratamento de Falhas

### Timeout em Ferramenta Semântica

```python
# O Fallback Engine cuida automaticamente:
result = await fallback_engine.execute_with_fallback(
    tool_name="semantic_code_search",
    params={"query": "authentication"},
    tool_executor=my_executor,
)

# Se timeout:
# 1. Tenta get_context_tree (fallback 1)
# 2. Tenta get_file_skeleton (fallback 2)
# 3. Retorna resultado com fallback_used=True
```

### Circuit Breaker Aberto

```python
# Após 3 falhas consecutivas em uma ferramenta:
# - Circuito abre por 60 segundos
# - Chamadas são rejeitadas imediatamente
# - Após 60s, 2 chamadas de teste são permitidas
# - Se sucesso, circuito fecha novamente
```

### Cobertura Insuficiente

```python
passed, report = validator.validate()

if not passed:
    missing = validator.get_missing_files()
    failed = validator.get_failed_files()
    
    # Re-processar arquivos faltantes
    for file_path in missing:
        get_file_skeleton(file_path)
        validator.mark_file_analyzed(file_path, ...)
```

## Integração com Sistema Existente

### Modificações Necessárias

#### 1. `agents/prompts/specialized/__init__.py`

Adicionar import:

```python
from .codebase_exploration import (
    CODEBASE_EXPLORATION_SYSTEM_PROMPT,
    build_codebase_exploration_prompt,
    EXPLORATION_MODE_DETECTION,
)
```

#### 2. `agents/tools/__init__.py`

Adicionar no registry:

```python
from .contextplus_fallback import ContextPlusFallbackEngine
from .contextplus_validator import ContextPlusValidator

# No _DefaultRegistry, adicionar método:
def _get_contextplus_analysis_tools(self) -> list:
    return [
        ContextPlusFallbackEngine,
        ContextPlusValidator,
    ]
```

#### 3. `agents/specialists/selector.py`

Adicionar detecção de modo exploration:

```python
def detect_exploration_mode(user_message: str) -> bool:
    """Detect if user wants codebase exploration."""
    keywords = [
        "analise o codebase",
        "mapeie o projeto",
        "explorar a estrutura",
        "documentar o sistema",
        "como funciona o código",
    ]
    return any(kw in user_message.lower() for kw in keywords)
```

## Métricas e Monitoramento

### Métricas Coletadas

- **Cobertura de arquivos:** % de arquivos analisados vs. descobertos
- **Cobertura de funções:** % de funções com assinatura extraída
- **Cobertura de classes:** % de classes documentadas
- **Timeout rate:** % de chamadas que resultaram em timeout
- **Fallback usage:** Quantidade de vezes que fallback foi utilizado
- **Padrões identificados:** Contagem de padrões arquiteturais encontrados

### Health Report

```python
# Do Fallback Engine:
health = fallback_engine.get_health_report()

# Do Validator:
progress = validator.get_progress_summary()
```

## Configuração

### Variáveis de Ambiente

```bash
# Timeout para ferramentas Context+ (segundos)
CONTEXTPLUS_TIMEOUT=30

# Cobertura mínima exigida (%)
CONTEXTPLUS_MIN_COVERAGE=95

# Máximo de retries por ferramenta
CONTEXTPLUS_MAX_RETRIES=2

# Habilitar circuit breaker
CONTEXTPLUS_CIRCUIT_BREAKER=true
```

### Validação de Configuração

```python
from agents.tools.contextplus_validator import ValidationConfig

config = ValidationConfig(
    min_coverage_percentage=95.0,
    min_function_coverage=90.0,
    min_class_coverage=95.0,
    max_timeout_rate=5.0,
    min_confidence_score=0.7,
)
```

## Possibilidades com GitNexus

### Integração Futura

O GitNexus pode adicionar **dimensão temporal** à análise:

1. **Co-change Analysis**
   - Identificar arquivos modificados juntos
   - Detectar acoplamento implícito

2. **Hotspot Detection**
   - Arquivos com alta frequência de mudanças
   - Áreas que precisam de mais testes

3. **Blame Semântico**
   - Associar mudanças a features/bugs
   - Histórico de decisões arquiteturais

4. **Refactoring Impact**
   - Antes de mudar: ver quem mexeu recentemente
   - Prever impacto de refatorações

5. **Code Churn Analysis**
   - Código instável vs. estável
   - Priorizar documentação de código estável

## Próximos Passos

- [ ] Integrar imports nos `__init__.py`
- [ ] Adicionar detecção de modo no specialist selector
- [ ] Testar com codebase real do MindFlow
- [ ] Adicionar variáveis de ambiente no `.env`
- [ ] Criar dashboard de métricas
- [ ] Integrar GitNexus para análise temporal
