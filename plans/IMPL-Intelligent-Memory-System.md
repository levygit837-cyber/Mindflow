# Implementation Plan: Intelligent Memory System

**Ref:** PRD-Memory-Observer-Session · ADR-007  
**Timeline:** 8 semanas (4 phases)  
**Status:** Ready to Start  

---

## Dependency Graph

```
                    ┌──────────────────┐
                    │  SessionFact     │
                    │  model+migration │
                    └───────┬──────────┘
                            │
              ┌─────────────┼──────────────────┐
              │             │                  │
              ▼             ▼                  ▼
    ┌─────────────┐  ┌────────────┐  ┌──────────────────┐
    │ DirectoryMap │  │FactExtract │  │ RecallRequest    │
    │ (path→cat)  │  │ (LLM)      │  │ extend w/ facts  │
    └──────┬──────┘  └─────┬──────┘  └────────┬─────────┘
           │               │                  │
           ▼               ▼                  ▼
    ┌─────────────┐  ┌────────────┐  ┌──────────────────┐
    │ Observer     │  │ SmartComp  │  │ Auto-Inject      │
    │ Enhanced     │  │ (LLM stub  │  │ in simple_flow   │
    │ (Hierarch.)  │  │  → real)   │  │                  │
    └──────┬──────┘  └─────┬──────┘  └──────────────────┘
           │               │
           ▼               ▼
    ┌─────────────┐  ┌────────────┐
    │ Facade:     │  │ Worker:    │
    │ save_hier.  │  │ real       │
    │ annotation  │  │ handlers   │
    └─────────────┘  └────────────┘
```

---

## Phase 1: Foundation (Semanas 1-2)

**Outcome:** Toda alteração de código é documentada hierarquicamente e um novo model de fatos de sessão está pronto.

### Task 1.1 — SessionFact Model + Migration
**Prioridade:** P0 (sem dependências, desbloqueia Phase 2)  
**Esforço:** 0.5 dia  
**Arquivo:** `memory/storage/models.py`  

```python
class SessionFact(Base):
    """Consolidated fact extracted from a session by LLM analysis.

    Unlike AgentMemoryFact (extractive, regex-based, window-scoped),
    SessionFact is a semantically rich, LLM-generated consolidation
    of an entire session's key outcomes.
    """
    __tablename__ = "session_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # fact_type: "action" | "decision" | "discovery" | "error" | "state"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    importance: Mapped[float] = mapped_column(Float, default=0.5, index=True)
    related_files: Mapped[list[str]] = mapped_column(JSON, default=list)
    embedding_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("session_embeddings.id", ondelete="SET NULL"), nullable=True
    )
    source_window_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_memory_windows.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

**Sub-tasks:**
- [ ] Adicionar `SessionFact` em `memory/storage/models.py`
- [ ] Criar migration Alembic: `20260403_0018_session_facts.py`
- [ ] Exportar em `memory/storage/__init__.py` e `memory/session_memory/models.py`
- [ ] Test: `test_session_fact_model.py` — CRUD básico

---

### Task 1.2 — Directory-to-Category Mapper
**Prioridade:** P0 (sem dependências, desbloqueia Task 1.3)  
**Esforço:** 1 dia  
**Arquivo novo:** `memory/classification/directory_mapper.py`  

```python
class DirectoryMapper:
    """Maps file paths to MemoryCategory/MemorySubCategory.

    Uses glob patterns for zero-cost classification.
    Auto-creates categories when first seen.
    """

    DEFAULT_PATTERNS: dict[str, list[str]] = {
        "api": ["**/api/**", "**/routes/**", "**/endpoints/**", "**/controllers/**"],
        "services": ["**/services/**", "**/service/**"],
        "models": ["**/models/**", "**/schemas/**", "**/entities/**"],
        "tests": ["**/tests/**", "**/test_*", "**/*_test.*"],
        "config": ["**/config/**", "**/.env*", "**/settings.*"],
        "frontend": ["**/components/**", "**/pages/**", "**/views/**"],
        "infrastructure": ["**/infra/**", "**/docker*", "**/deploy/**"],
        "memory": ["**/memory/**"],
        "docs": ["**/docs/**", "**/*.md"],
    }

    def classify(self, file_path: str) -> tuple[str, str | None]:
        """Return (category_name, subcategory_name) for a file path."""
        ...

    def _match_pattern(self, path: str, patterns: list[str]) -> bool:
        ...

    def _infer_subcategory(self, path: str, category: str) -> str | None:
        """Infer subcategory from path segments after the category match.

        Example: api/middleware/auth.py → category="api", subcategory="middleware"
        """
        ...

    async def get_or_create_ids(
        self, db, *, project_id: int, file_path: str
    ) -> tuple[int | None, int | None]:
        """Return (category_id, subcategory_id), creating records if needed."""
        ...
```

**Sub-tasks:**
- [ ] Criar `memory/classification/__init__.py`
- [ ] Criar `memory/classification/directory_mapper.py`
- [ ] Implementar `classify()` com fnmatch/glob
- [ ] Implementar `_infer_subcategory()` — extrai segmento de path entre category match e filename
- [ ] Implementar `get_or_create_ids()` — upsert em `MemoryCategory`/`MemorySubCategory`
- [ ] Test: `test_directory_mapper.py` — 15+ paths cobrindo todos os patterns
- [ ] Test: edge cases — paths fora de patterns → category "other"

---

### Task 1.3 — Observer Enhanced: HierarchicalAnnotation
**Prioridade:** P0 (depende de 1.2)  
**Esforço:** 2 dias  
**Arquivo:** `execution/observers/memory_observer.py`  

**Mudanças em `_process_event()`:**
1. Extrair `file_path` de `event.data.get("file")` ou `event.data.get("result", {}).get("file_path")`
2. Se `file_path` presente: usar `DirectoryMapper.classify()` para obter category/subcategory
3. Extrair `lines_modified` de `event.data.get("result", {}).get("lines")`
4. Gerar `content` rico (sem limite de 500 chars) usando `_summarize_event_rich()`

**Mudanças em `_save_annotation()`:**
1. Se evento tem `file_path`: salvar como `HierarchicalAnnotation` via `MemoryFacade.save_hierarchical_annotation()`
2. Se evento não tem `file_path`: continuar salvando como `MemoryAnnotation` (backward compat)

```python
async def _process_event(self, event: dict[str, Any]) -> None:
    # ... rate limiting e importance scoring existentes ...

    file_path = self._extract_file_path(event)
    if file_path:
        content = self._summarize_event_rich(event)
        category, subcategory = self._mapper.classify(file_path)
        lines = self._extract_lines_modified(event)
        await self._save_hierarchical_annotation(
            event, content, file_path, lines, category, subcategory
        )
    else:
        # Fallback: comportamento atual
        content = self._summarize_event(event)
        annotation = MemoryAnnotation(...)
        await self._save_annotation(annotation)

def _summarize_event_rich(self, event: dict[str, Any]) -> str:
    """Rich NL summary — no char limit."""
    agent_id = event.get("agent_id", "unknown")
    event_type = event.get("type", "event")
    message = event.get("message", "")
    data = event.get("data", {})
    file_path = data.get("file", "")
    result = data.get("result", "")

    parts = [f"{agent_id} [{event_type}]"]
    if file_path:
        parts.append(f"em {file_path}")
    if message:
        parts.append(f": {message}")
    if isinstance(result, str) and result:
        parts.append(f" — Resultado: {result[:2000]}")
    elif isinstance(result, dict):
        relevant = {k: v for k, v in result.items()
                    if k in ("file_path","lines","error","output","content")}
        if relevant:
            parts.append(f" | {relevant}")

    return " ".join(parts)
```

**Sub-tasks:**
- [ ] Adicionar `DirectoryMapper` como dependência do `MemoryObserver.__init__()`
- [ ] Implementar `_extract_file_path(event)` — checar múltiplos campos possíveis
- [ ] Implementar `_extract_lines_modified(event)` → `{"start": int, "end": int, "count": int}`
- [ ] Implementar `_summarize_event_rich(event)` — sem limite de chars
- [ ] Implementar `_save_hierarchical_annotation()` — cria `HierarchicalAnnotation`
- [ ] Manter fallback para `_save_annotation()` quando não tem file_path
- [ ] Test: `test_observer_hierarchical.py` — evento com file → HierarchicalAnnotation
- [ ] Test: evento sem file → MemoryAnnotation (backward compat)
- [ ] Test: rate limiting continua funcionando

---

### Task 1.4 — MemoryFacade: save_hierarchical_annotation()
**Prioridade:** P0 (depende de 1.3)  
**Esforço:** 1 dia  
**Arquivo:** `memory/facade.py`  

```python
async def save_hierarchical_annotation(
    self,
    annotation: HierarchicalAnnotation,
    *,
    project_id: int,
    category_id: int | None = None,
    subcategory_id: int | None = None,
) -> None:
    """Persist a hierarchical annotation with embedding."""
    try:
        from mindflow_backend.infra.database.connection import get_async_db_session
        async with get_async_db_session() as db:
            annotation.project_id = project_id
            annotation.category_id = category_id
            annotation.subcategory_id = subcategory_id
            db.add(annotation)

            # Gerar embedding para semantic retrieval
            embedding_outcome = await self._generate_embedding(annotation.content)
            if embedding_outcome.vector:
                session_embedding = SessionEmbedding(
                    session_id=annotation.session_id,
                    agent_id=annotation.source_agent_id,
                    content=annotation.content[:1500],
                    vector=embedding_outcome.vector,
                    source_message_id=None,
                    source_type="hierarchical_annotation",
                    metadata={
                        "annotation_type": annotation.annotation_type,
                        "file_path": annotation.file_path,
                        "category_id": category_id,
                        "importance": annotation.importance,
                    },
                )
                db.add(session_embedding)

            await db.commit()
    except Exception as exc:
        _logger.warning("hierarchical_annotation_save_failed", error=str(exc))
```

**Sub-tasks:**
- [ ] Adicionar método `save_hierarchical_annotation()` no `MemoryFacade`
- [ ] Gerar embedding do content para retrieval
- [ ] Definir `source_type="hierarchical_annotation"` em `SessionEmbedding.metadata`
- [ ] Test: `test_facade_hierarchical.py` — annotation salva + embedding gerado
- [ ] Test: fallback quando embedding falha (graceful degradation)

---

## Phase 2: Continuity (Semanas 3-4)

**Outcome:** Compactação preserva fatos e agentes recuperam contexto de sessões anteriores automaticamente.

### Task 2.1 — Session Fact Extractor (LLM-based)
**Prioridade:** P1 (depende de 1.1)  
**Esforço:** 2 dias  
**Arquivo novo:** `memory/session/fact_extractor.py`  

```python
class SessionFactExtractor:
    """Extract structured facts from a session using LLM."""

    EXTRACTION_PROMPT = '''Analyze this conversation session and extract key facts.
For each fact, provide:
- type: "action" | "decision" | "discovery" | "error" | "state"
- content: clear natural language description
- category: project area affected (e.g., "api", "auth", "database")
- importance: 0.0-1.0 score
- related_files: list of file paths mentioned

Return JSON array of facts. Maximum 15 facts.
Focus on:
1. What was DONE (code changes, file modifications)
2. What was DECIDED (architecture choices, approach selections)
3. What was DISCOVERED (bugs found, patterns identified)
4. What ERRORS occurred and how they were resolved
5. What STATE was the work in when the session ended

Session messages:
{messages}
'''

    async def extract(
        self,
        messages: list[dict[str, Any]],
        session_id: str,
        agent_id: str,
    ) -> list[SessionFact]:
        """Extract facts from session messages using LLM."""
        ...

    async def _call_llm(self, prompt: str) -> str:
        """Call configured LLM provider for fact extraction."""
        ...

    def _parse_facts(self, llm_response: str, session_id: str, agent_id: str) -> list[SessionFact]:
        """Parse LLM JSON response into SessionFact instances."""
        ...

    async def persist_facts(self, db, facts: list[SessionFact]) -> int:
        """Persist facts with embeddings. Returns count persisted."""
        ...
```

**Sub-tasks:**
- [ ] Criar `memory/session/__init__.py`
- [ ] Criar `memory/session/fact_extractor.py`
- [ ] Implementar prompt de extração
- [ ] Implementar `_call_llm()` — reutilizar provider configurado
- [ ] Implementar `_parse_facts()` — JSON parsing com validação robusta
- [ ] Implementar `persist_facts()` — batch insert + embeddings
- [ ] Test: mock LLM → facts extraídos corretamente
- [ ] Test: LLM retorna JSON malformado → graceful degradation
- [ ] Test: sessão vazia → zero facts (sem erro)

---

### Task 2.2 — Smart Compaction (substituir stub)
**Prioridade:** P1 (depende de 2.1)  
**Esforço:** 2 dias  
**Arquivo:** `query/budget/auto_compact.py`  

**Substituir `_summary_compact_stub()` por:**

```python
async def _summary_compact(
    self,
    messages: list[dict[str, Any]],
    current_tokens: int,
    llm_summarize_fn: Callable[[str], Awaitable[str]],
) -> CompactResult:
    """LLM-based compaction with fact preservation.

    Pipeline:
    1. Extract SessionFacts via FactExtractor (preserve for future sessions)
    2. Generate consolidated summary via LLM
    3. Build compacted message list: system + summary + recent messages
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conversation_msgs = [m for m in messages if m.get("role") != "system"]

    if len(conversation_msgs) <= 3:
        return CompactResult(success=False, error="Not enough messages")

    # Step 1: Extract facts (persisted separately)
    fact_extractor = SessionFactExtractor()
    session_id = self._extract_session_id(messages)
    facts = await fact_extractor.extract(conversation_msgs, session_id, "compaction")

    # Step 2: Generate summary
    conversation_text = self._format_messages_for_summary(conversation_msgs)
    summary = await llm_summarize_fn(conversation_text)

    if not summary:
        return self._snip_compact(messages, current_tokens)  # fallback

    # Step 3: Build compacted messages
    recent_count = min(5, len(conversation_msgs))
    recent_msgs = conversation_msgs[-recent_count:]

    summary_msg = {
        "role": "system",
        "content": (
            f"[Session compacted. {len(conversation_msgs)} messages → summary + "
            f"{recent_count} recent. {len(facts)} facts preserved for future sessions.]\n\n"
            f"{summary}"
        ),
    }

    final = system_msgs + [summary_msg] + recent_msgs
    compacted_tokens = estimate_token_count(
        " ".join(m.get("content", "") for m in final)
    )

    return CompactResult(
        original_tokens=current_tokens,
        compacted_tokens=compacted_tokens,
        tokens_saved=current_tokens - compacted_tokens,
        messages_removed=len(conversation_msgs) - recent_count,
        messages_compacted=len(final),
        compacted_messages=final,
        strategy_used=CompactStrategy.SUMMARY,
        success=True,
    )
```

**Sub-tasks:**
- [ ] Renomear `_summary_compact_stub` → `_summary_compact_legacy` (keep as fallback)
- [ ] Implementar `_summary_compact()` async com fact extraction + LLM
- [ ] Atualizar `compact()` para chamar `_summary_compact()` quando `llm_summarize_fn` disponível
- [ ] Implementar `_extract_session_id(messages)` — extrair session_id do contexto
- [ ] Adicionar keep-alive durante compactação (mecanismo já existe)
- [ ] Test: compactação com mock LLM → facts extraídos + summary gerado
- [ ] Test: LLM falha → fallback para snip
- [ ] Test: circuit breaker continua funcionando

---

### Task 2.3 — Extend MemoryRecallRequest para SessionFacts
**Prioridade:** P1 (depende de 1.1)  
**Esforço:** 1 dia  
**Arquivo:** `schemas/memory/contracts.py`  

```python
# Adicionar ao MemoryRecallRequest:
include_session_facts: bool = Field(
    default=True,
    description="Whether to include SessionFact hits in recall results"
)
top_k_facts: int = Field(
    default=5,
    ge=0,
    description="Maximum SessionFact hits to return"
)
```

**Arquivo:** `orchestrator/memory_integration.py`

Estender `MemoryIntegration.recall()` para buscar `SessionFact`s:

```python
async def _recall_session_facts(
    self,
    *,
    session_id: str,
    query: str,
    top_k: int,
    min_score: float,
    exclude_session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve SessionFacts via semantic search."""
    ...
```

**Sub-tasks:**
- [ ] Adicionar `include_session_facts` e `top_k_facts` ao `MemoryRecallRequest`
- [ ] Adicionar `MemorySourceType.SESSION_FACT` ao enum
- [ ] Implementar `_recall_session_facts()` em `MemoryIntegration`
- [ ] Integrar no `recall()` — merge facts com message_hits e block_hits
- [ ] Test: recall com facts → facts aparecem nos hits
- [ ] Test: `include_session_facts=False` → sem facts nos hits

---

### Task 2.4 — Auto-Inject em simple_flow
**Prioridade:** P1 (depende de 2.3)  
**Esforço:** 0.5 dia  
**Arquivo:** `graphs/implementations/orchestrator/simple_flow.py`  

A mudança é mínima — `_retrieve_memory_context()` já usa `MemoryRecallRequest`. Basta garantir que `include_session_facts=True` (que é o default). Pode-se adicionar formatação específica para facts:

```python
# Na formatação do context, separar facts dos outros hits:
fact_hits = [h for h in response.hits if h.source_type == "session_fact"]
if fact_hits:
    context_parts.append("## Context from Previous Sessions")
    for hit in fact_hits:
        context_parts.append(f"- [{hit.category}] {hit.content_excerpt}")
```

**Sub-tasks:**
- [ ] Verificar que `MemoryRecallRequest` default inclui facts
- [ ] Adicionar formatação de facts no `format_context()` do `MemoryIntegration`
- [ ] Test: nova sessão recebe facts da sessão anterior no contexto

---

## Phase 3: Intelligence (Semanas 5-6)

**Outcome:** SessionReviewWorker analisa sessões com LLM e o Observer gera contexto NL rico.

### Task 3.1 — SessionReviewWorker: Implementar Handlers
**Prioridade:** P2 (depende de 2.1, 2.2)  
**Esforço:** 3 dias  
**Arquivo:** `workers/system/session_review_worker.py`  

**Handler: `_handle_context_summarization()`**
```python
async def _handle_context_summarization(self, message_data: dict) -> WorkerResult:
    session_id = message_data["session_id"]
    # 1. Buscar mensagens da sessão
    # 2. Chamar FactExtractor.extract()
    # 3. Gerar summary via LLM
    # 4. Persistir facts + summary
    # 5. Retornar resultado
```

**Handler: `_handle_memory_consolidation()`**
```python
async def _handle_memory_consolidation(self, message_data: dict) -> WorkerResult:
    session_id = message_data["session_id"]
    # 1. Buscar HierarchicalAnnotations da sessão
    # 2. Consolidar por category/subcategory
    # 3. Gerar summary por categoria via LLM
    # 4. Atualizar ProjectMemory com consolidated view
```

**Handler: `_handle_window_review()`**
```python
async def _handle_window_review(self, message_data: dict) -> WorkerResult:
    session_id = message_data["session_id"]
    window_index = message_data["window_index"]
    # 1. Buscar window events
    # 2. Extrair key facts
    # 3. Score importance de cada fact
    # 4. Persistir como SessionFacts
```

**Sub-tasks:**
- [ ] Implementar `_handle_context_summarization()` com `SessionFactExtractor`
- [ ] Implementar `_handle_memory_consolidation()` — consolidação por categoria
- [ ] Implementar `_handle_window_review()` — extração de fatos por window
- [ ] Implementar `_handle_token_management()` — trigger smart compaction
- [ ] Remover todos os `await asyncio.sleep()` stubs
- [ ] Test: worker processa task de summarization end-to-end
- [ ] Test: worker processa consolidation com multiple categories
- [ ] Test: worker falha gracefully quando LLM unavailable

---

### Task 3.2 — Observer: Rich NL Context + Cross-Agent Bridge
**Prioridade:** P2 (depende de 1.3)  
**Esforço:** 1 dia  
**Arquivo:** `execution/observers/memory_observer.py`  

- Implementar `_summarize_event_rich()` completamente
- Garantir que `HierarchicalAnnotation` tags incluem `session_id` e `source_agent_id` para cross-agent queries
- Adicionar `diff_summary` quando evento contém informação de diff

**Sub-tasks:**
- [ ] Enriquecer `_summarize_event_rich()` com mais contexto dos event data
- [ ] Extrair `diff_summary` de tool_result events que incluem diffs
- [ ] Adicionar tags de cross-agent: `["agent:{source_agent_id}", "session:{session_id}"]`
- [ ] Test: cross-agent recall — Agente B recupera anotação do Agente A

---

## Phase 4: Polish (Semanas 7-8)

**Outcome:** Sistema robusto, monitorado, documentado.

### Task 4.1 — Performance Tuning
**Esforço:** 2 dias  

- [ ] Batch saves para `HierarchicalAnnotation` (acumular N e salvar em batch)
- [ ] Ajustar rate limit do Observer: 10/min → configurável por tipo de evento
- [ ] Otimizar queries de recall com facts (composite index em `session_facts`)
- [ ] Benchmark: recall latency com 10k, 50k, 100k embeddings
- [ ] Benchmark: compactação LLM latency com sessões de 50k, 100k, 200k tokens

### Task 4.2 — Monitoring e Alertas
**Esforço:** 1 dia  

- [ ] Métricas: `observer_annotations_total` (counter, labels: type, category)
- [ ] Métricas: `session_facts_extracted_total` (counter, labels: fact_type)
- [ ] Métricas: `compaction_duration_seconds` (histogram)
- [ ] Métricas: `recall_facts_hit_rate` (gauge — % de recalls que incluem facts)
- [ ] Alerta: compaction failure rate > 20% em 5min
- [ ] Alerta: observer queue > 400 events (80% capacity)

### Task 4.3 — Integration Tests E2E
**Esforço:** 2 dias  

- [ ] Test E2E: Sessão A (Coder edita api/auth.py) → Observer documenta → Session compacta → Sessão B (Coder pergunta sobre auth) → Recall retorna facts + annotations
- [ ] Test E2E: Multi-agent — Analyst observa → Coder executa → Observer documenta → Bridge funciona
- [ ] Test E2E: Compactação com fallback — LLM falha → snip + extractive facts preservados
- [ ] Test E2E: Project hierarchy — categoria auto-criada, subcategoria inferida, annotations linkadas

### Task 4.4 — Documentation
**Esforço:** 1 dia  

- [ ] Atualizar `docs/14-contexthub/01-ARCHITECTURE/memory-system.md`
- [ ] Documentar `SessionFact` schema em docs de API
- [ ] Atualizar SPADE Phase 3B plan com status completed
- [ ] README da feature para onboarding de devs
- [ ] Runbook: como investigar quando compactação falha

---

## Summary: Effort Estimation

| Phase | Semanas | Tasks | Esforço Total | Arquivos Novos | Arquivos Modificados |
|---|---|---|---|---|---|
| **Phase 1** | 1-2 | 4 tasks | ~4.5 dias | 2 | 3 |
| **Phase 2** | 3-4 | 4 tasks | ~5.5 dias | 1 | 3 |
| **Phase 3** | 5-6 | 2 tasks | ~4 dias | 0 | 2 |
| **Phase 4** | 7-8 | 4 tasks | ~6 dias | 0 | 4+ |
| **Total** |  | **14 tasks** | **~20 dias** | **3** | **12+** |

## Arquivos — Inventário Completo

### Novos (3)
| Arquivo | Phase |
|---|---|
| `memory/classification/directory_mapper.py` | 1 |
| `memory/session/fact_extractor.py` | 2 |
| migration `session_facts` | 1 |

### Modificados (12)
| Arquivo | Phase | Tipo de Mudança |
|---|---|---|
| `memory/storage/models.py` | 1 | ADD `SessionFact` |
| `execution/observers/memory_observer.py` | 1, 3 | MODIFY observer para HierarchicalAnnotation |
| `memory/facade.py` | 1 | ADD `save_hierarchical_annotation()` |
| `query/budget/auto_compact.py` | 2 | MODIFY stub → LLM real |
| `schemas/memory/contracts.py` | 2 | ADD fields no `MemoryRecallRequest` |
| `orchestrator/memory_integration.py` | 2 | ADD `_recall_session_facts()` |
| `graphs/.../simple_flow.py` | 2 | MINOR formatação de facts |
| `workers/system/session_review_worker.py` | 3 | MODIFY stubs → handlers reais |
| `memory/storage/__init__.py` | 1 | ADD export |
| `memory/session_memory/models.py` | 1 | ADD re-export |
| `docs/.../memory-system.md` | 4 | UPDATE docs |
| `plans/SPADE-Phase-3B-Memory-Observer.md` | 4 | UPDATE status |

---

## Definition of Done

- [ ] Todos os testes unitários passam (coverage >80% nos novos arquivos)
- [ ] Testes de integração E2E passam
- [ ] Observer documenta alterações de código com file/lines/category
- [ ] Compactação extrai e persiste SessionFacts antes de compactar
- [ ] Nova sessão recebe facts da sessão anterior via auto-inject
- [ ] SessionReviewWorker handlers implementados (zero stubs)
- [ ] Performance: recall <100ms p95, compaction <15s p95
- [ ] Monitoring dashboards configurados
- [ ] Documentação atualizada

---

## Risk Register

| # | Risco | Prob | Impact | Mitigação | Owner |
|---|---|---|---|---|---|
| R1 | LLM call timeout durante compactação | Média | Alto | Keep-alive + fallback para snip | AI Engineer |
| R2 | Fact extraction gera fatos irrelevantes | Média | Médio | Prompt engineering iterativo + importance scoring | AI Engineer |
| R3 | Migration `session_facts` conflita com outras | Baixa | Médio | Coordenar com branches ativos | Tech Lead |
| R4 | Observer Enhanced degrada performance | Baixa | Alto | Non-blocking (já é) + batch saves | Tech Lead |
| R5 | pgvector slow com muitos embeddings | Baixa | Médio | Indexes + partitioning se necessário | Tech Lead |
| R6 | Path patterns não cobrem projeto do usuário | Média | Baixo | Fallback "other" + UI para custom patterns futuro | PM |
