# Context+ Integration Plan — MindFlow

## Status: Phase 1 Complete ✅

### Implemented (7 tools)

#### Core Engine

- [x] `core/walker.py` — Gitignore-aware directory traversal
- [x] `core/parser.py` — Multi-language symbol extraction (regex-based)
- [x] `core/embeddings.py` — Multi-provider embedding engine (Ollama/OpenAI)
- [x] `core/memory_graph.py` — In-memory property graph with JSON persistence

#### Discovery Tools

- [x] `context_tree` — Token-aware structural AST tree with symbol ranges
- [x] `file_skeleton` — Function signature extractor without full body reading
- [x] `semantic_search` — Hybrid semantic + keyword search over codebase

#### Analysis Tools

- [x] `blast_radius` — Symbol usage tracer across entire codebase

#### Memory Tools

- [x] `upsert_memory_node` — Create/update memory nodes with auto-embeddings
- [x] `create_relation` — Create typed edges between memory nodes
- [x] `search_memory_graph` — Search graph by meaning with traversal

#### Integration

- [x] `integration/registry.py` — ToolRegistry auto-registration

### Pending (10 tools)

#### Discovery

- [ ] `semantic_navigate` — Spectral clustering navigator (needs scikit-learn)

#### Analysis

- [ ] `static_analysis` — Native linter runner (tsc, eslint, py_compile, cargo, go vet)

#### Code Ops

- [ ] `propose_commit` — Code gatekeeper with header/validation rules
- [ ] `feature_hub` — Obsidian-style feature hub navigator

#### Version Control

- [ ] `list_restore_points` — Shadow restore points
- [ ] `undo_change` — Restore to previous state

#### Memory

- [ ] `prune_stale_links` — Remove decayed edges automatically
- [ ] `add_interlinked_context` — Bulk node insertion with auto-linking
- [ ] `retrieve_with_traversal` — Graph traversal from a start node

### Dependencies to Add

```python
# python/pyproject.toml
"scikit-learn>=1.3.0",  # For spectral clustering (semantic_navigate)
"ollama>=0.3.0",        # For local embeddings (optional, already via langchain-ollama)
```

### Configuration

Add to `.env`:

```bash
# Context+ Configuration
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_HOST=http://localhost:11434
```

### Integration Points

1. **ToolRegistry** — All tools auto-register via `register_contextplus_tools()`
2. **Memory System** — Memory graph can bridge with PostgreSQL/pgvector via `MemoryGraphBridge`
3. **Agent Runtime** — Tools available to all agents via standard tool invocation

### Architecture Decisions

1. **Regex-based parsing** instead of tree-sitter — Simpler, no WASM dependencies
2. **JSON-based memory graph** — Lightweight, no external DB required
3. **Hybrid scoring** — 72% semantic + 28% keyword for balanced search
4. **Hash fallback embeddings** — Works without Ollama/OpenAI for testing
5. **AsyncToolInterface** — Consistent with existing MindFlow tool patterns
