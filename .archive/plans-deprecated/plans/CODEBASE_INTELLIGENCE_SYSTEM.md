# Codebase Intelligence System — Visão Unificada

## Arquitetura Completa

O **Codebase Intelligence System** combina duas camadas:

1. **CodebaseAnalysisGraph** — LangGraph com loops iterativos para exploração exaustiva
2. **Project Memory** — Índice persistente de código com busca exata e semântica

```
┌─────────────────────────────────────────────────────────────────┐
│              CODEBASE INTELLIGENCE SYSTEM                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │           CodebaseAnalysisGraph (LangGraph)            │     │
│  │                                                        │     │
│  │  Discovery ──▶ Skeleton ──▶ DeepAnalysis               │     │
│  │      │              │              │                   │     │
│  │      │         (loop?)        (loop?)                  │     │
│  │      │              │              │                   │     │
│  │      └──────────────┴──────────────┘                   │     │
│  │                       │                                │     │
│  │                       ▼                                │     │
│  │              ┌─────────────────┐                       │     │
│  │              │ INDEX TO MEMORY │ ◀── Node que salva    │     │
│  │              └────────┬────────┘     no Project Memory │     │
│  │                       │                                │     │
│  │                       ▼                                │     │
│  │              Validation ──▶ Loop (se < 95%)            │     │
│  │                       │                                │     │
│  │                       ▼                                │     │
│  │                    Report                               │     │
│  └────────────────────────────────────────────────────────┘     │
│                           │                                      │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              Project Memory (Persistent Index)         │     │
│  │                                                        │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │     │
│  │  │PostgreSQL│  │ KuzuDB   │  │  Cache   │            │     │
│  │  │ pgvector │  │  Graph   │  │   LRU    │            │     │
│  │  └──────────┘  └──────────┘  └──────────┘            │     │
│  │                                                        │     │
│  │  Indexer ──▶ Search (Exact + Semantic) ──▶ Reader     │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Fluxo Completo de Execução

### Fase 1: Análise Iterativa (Graph)

```
Iteration 1:
  Discovery → Skeleton (50 arquivos) → DeepAnalysis → Validation (60%) → LOOP

Iteration 2:
  Skeleton (40 faltantes) → DeepAnalysis → Validation (85%) → LOOP

Iteration 3:
  Skeleton (10 faltantes) → DeepAnalysis → Validation (97%) → REPORT
```

### Fase 2: Indexação (Project Memory)

```
A cada iteração do graph:
  1. Node "index_to_memory" recebe arquivos analisados
  2. Para cada arquivo:
     - Parser extrai funções/classes/métodos
     - Gera embedding semântico
     - Salva no PostgreSQL (dados + pgvector)
     - Salva no KuzuDB (grafo de dependências)
  3. Após última iteração: índice completo

Resultado:
  - 500+ funções indexadas
  - 50+ classes indexadas
  - 200+ métodos indexados
  - Todos com código-fonte completo
```

### Fase 3: Consulta (Search + Read)

```
Usuário: "Encontre a função que valida email"

1. Busca Semântica:
   search.find_similar("validação de email")
   → [
       (validate_email_format, 0.92),
       (is_valid_email, 0.87),
     ]

2. Usuário seleciona: validate_email_format

3. Leitura Completa:
   search.get_full_source(element.id)
   → def validate_email_format(email: str) -> bool:
         import re
         pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
         return bool(re.match(pattern, email))
```

## Componentes Criados

### Arquivos de Implementação

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `agents/tools/contextplus_fallback.py` | ✅ Criado | Fallback Engine com Circuit Breaker |
| `agents/prompts/specialized/codebase_exploration.py` | ✅ Criado | SystemPrompt dinâmico |
| `agents/tools/contextplus_validator.py` | ✅ Criado | Coverage Validator |
| `agents/prompts/specialized/__init__.py` | ✅ Modificado | Imports adicionados |
| `agents/tools/__init__.py` | ✅ Modificado | Registry atualizado |

### Arquivos de Planejamento

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `plans/CODEBASE_EXPLORATION_IMPLEMENTATION.md` | ✅ Criado | Documentação das ferramentas |
| `plans/PROJECT_MEMORY_ARCHITECTURE.md` | ✅ Criado | Arquitetura da memória de código |
| `plans/CODEBASE_INTELLIGENCE_SYSTEM.md` | ✅ Criado | Visão unificada (este arquivo) |

### Arquivos a Criar (Próxima Fase)

| Arquivo | Descrição |
|---------|-----------|
| `graphs/implementations/analysis/codebase_analysis.py` | LangGraph principal |
| `graphs/implementations/analysis/state.py` | Estado do graph |
| `graphs/implementations/analysis/nodes/*.py` | Nodes individuais |
| `graphs/implementations/analysis/routing.py` | Conditional edges |
| `memory/project_memory/models.py` | CodeElement, ProjectMemory |
| `memory/project_memory/storage.py` | Persistência multi-backend |
| `memory/project_memory/indexer.py` | Indexador de código |
| `memory/project_memory/search.py` | API de busca |

## Resumo Técnico

### CodebaseAnalysisGraph

```python
# Criação do graph
graph = create_codebase_analysis_graph()

# Execução
result = await graph.ainvoke(CodebaseAnalysisState(
    target_path="python/mindflow_backend",
    scope="full",
    min_coverage=95.0,
))

# Resultado
print(result.report_markdown)       # Relatório
print(result.coverage_percentage)   # 97.5%
print(len(result.analyzed_files))   # 245 arquivos
```

### Project Memory Search

```python
# Inicialização
search = ProjectMemorySearch(storage)

# Busca exata
func = await search.find_exact("authenticate_user")

# Busca semântica
similar = await search.find_similar("validação de email", top_k=5)

# Leitura completa
source = await search.get_full_source(func[0].id)
```

## Próximos Passos

1. **Implementar o LangGraph** — Criar os nodes e o graph compilado
2. **Implementar Project Memory** — Criar models, storage, indexer, search
3. **Criar migration SQL** — Tabela `project_code_elements`
4. **Integrar com embedding service** — Usar Ollama/OpenAI para embeddings
5. **Testar end-to-end** — Executar análise completa no MindFlow
6. **Criar dashboard** — Visualizar métricas de indexação
