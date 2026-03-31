# Context+ Integration for MindFlow

## Overview

Native Python port of [Context+ MCP](https://github.com/ForLoopCodes/contextplus) — semantic codebase intelligence tools integrated directly into the MindFlow agent infrastructure.

## Architecture

```
contextplus/
├── core/                    # Core engines
│   ├── embeddings.py        # Multi-provider embedding engine (Ollama/OpenAI)
│   ├── parser.py            # Multi-language symbol extraction (regex-based)
│   ├── walker.py            # Gitignore-aware directory traversal
│   └── memory_graph.py      # In-memory property graph with JSON persistence
├── tools/
│   ├── discovery/           # Codebase exploration tools
│   │   ├── context_tree.py  # Token-aware structural AST tree
│   │   ├── file_skeleton.py # Function signature extractor
│   │   └── semantic_search.py # Hybrid semantic + keyword search
│   ├── analysis/            # Code analysis tools
│   │   └── blast_radius.py  # Symbol usage tracer
│   └── memory/              # Memory graph tools
│       └── __init__.py      # upsert_node, create_relation, search_graph
└── integration/
    └── registry.py          # ToolRegistry auto-registration
```

## Registered Tools (7 prioritized)

| Tool | Category | Description |
|------|----------|-------------|
| `context_tree` | discovery | Structural tree with file headers, symbols, and line ranges |
| `file_skeleton` | discovery | Function signatures without reading full bodies |
| `semantic_search` | discovery | Semantic + keyword search over codebase |
| `blast_radius` | analysis | Trace symbol usage across entire codebase |
| `upsert_memory_node` | memory | Create/update memory nodes with auto-embeddings |
| `create_relation` | memory | Create typed edges between memory nodes |
| `search_memory_graph` | memory | Search graph by meaning with traversal |

## Usage

### Automatic Registration

Tools are automatically registered when the module is imported:

```python
from mindflow_backend.contextplus.integration.registry import register_contextplus_tools

registered = register_contextplus_tools()
```

### Direct Tool Usage

```python
from mindflow_backend.contextplus.tools.discovery.context_tree import ContextTreeTool

tool = ContextTreeTool()
tool.root_dir = "/path/to/project"
result = await tool.execute(depth_limit=2, include_symbols=True)
```

### Memory Graph

```python
from mindflow_backend.contextplus.core.memory_graph import upsert_node, create_relation
from mindflow_backend.contextplus.core.embeddings import fetch_embedding

# Create a node
embedding = await fetch_embedding("authentication module handles JWT tokens")
node = await upsert_node(
    root_dir="/path/to/project",
    node_type="concept",
    label="auth-module",
    content="Handles user authentication with JWT tokens",
    embedding=embedding,
)

# Create a relation
edge = await create_relation(
    root_dir="/path/to/project",
    source_id=node.id,
    target_id="other-node-id",
    relation="depends_on",
    weight=0.8,
)
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_API_KEY` | (empty) | Ollama API key |
| `CONTEXTPLUS_OPENAI_API_KEY` | (empty) | OpenAI API key |
| `CONTEXTPLUS_OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI base URL |
| `CONTEXTPLUS_OPENAI_EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |

## Dependencies

- `numpy` (already in MindFlow)
- `ollama` (optional, for local embeddings)
- `httpx` (already in MindFlow, for OpenAI embeddings)

## Pending Tools (to be implemented)

- `semantic_navigate` — Spectral clustering navigator
- `static_analysis` — Native linter runner
- `propose_commit` — Code gatekeeper with validation
- `feature_hub` — Obsidian-style feature hub navigator
- `list_restore_points` — Shadow restore points
- `undo_change` — Restore to previous state
- `prune_stale_links` — Remove decayed edges
- `add_interlinked_context` — Bulk node insertion with auto-linking
- `retrieve_with_traversal` — Graph traversal from a start node
