---
trigger: always_on
---

# Codedb MCP Usage Rules

## When to Use Codedb MCP

**ALWAYS USE CODEDB MCP FOR CODEBASE EXPLORATION IN THE PYTHON BACKEND.**

The MindFlow Python backend (`/home/levybonito/Projetos/MindFlow/python/mindflow_backend`) is indexed with codedb. Use codedb tools for all codebase exploration tasks.

## Codedb MCP Tools

### 1. Initial Exploration
- **`codedb_tree`** - Get full file tree structure with language detection and symbol counts
- **`codedb_status`** - Check if index is up to date (files count, sequence number)
- **`codedb_hot`** - Get most recently modified files

### 2. Symbol Lookup
- **`codedb_symbol`** - Find ALL definitions of a symbol name across the entire codebase
  - Use with `body=true` to include source code
  - Perfect for finding function/class definitions
  - Example: `codedb_symbol(name="PlannerAgent", body=true)`

### 3. File Inspection
- **`codedb_outline`** - Get structural outline of a file (functions, classes, imports, constants with line numbers)
- **`codedb_read`** - Read file contents with line ranges and content hashing
- **`codedb_deps`** - Get reverse dependencies (which files import/depend on a given file)

### 4. Text Search
- **`codedb_search`** - Full-text search across all indexed files using trigram index
  - Use `scope=true` to annotate results with enclosing function/struct
  - Use `regex=true` for pattern matching
  - Example: `codedb_search(query="class PlannerAgent", scope=true)`

### 5. Word Lookup (O(1))
- **`codedb_word`** - Fast exact word/identifier lookup using inverted index
  - Much faster than search for single-word queries
  - Example: `codedb_word(word="PlannerAgent")`

### 6. Batch Operations
- **`codedb_bundle`** - Execute multiple read-only queries in a single call (max 20 ops)
  - Combines outline, symbol, search, read, deps operations
  - Saves round-trips

### 7. Dependency Analysis
- **`codedb_deps`** - Impact analysis: what will break if you change a file
- **`codedb_graph_stats`** - Spot architectural problems
- **`codedb_graph_circular`** - Check for circular dependencies

## Workflow

1. **Start with `codedb_status`** to verify index is current
2. **Use `codedb_tree`** to understand project structure
3. **Use `codedb_search`** for conceptual queries ("how is authentication handled")
4. **Use `codedb_symbol`** for exact symbol lookups (function/class names)
5. **Use `codedb_word`** for fast identifier lookups
6. **Use `codedb_outline`** to inspect file structure before reading
7. **Use `codedb_read`** only after narrowing down via search
8. **Use `codedb_deps`** for impact analysis before modifying code

## Important Notes

- **NEVER use `read_file` directly** for codebase exploration - use codedb first
- **NEVER use `grep` for searching** - use `codedb_search` instead
- **Always specify project path**: `/home/levybonito/Projetos/MindFlow/python/mindflow_backend`
- **After code changes**, run `codedb_index` to update the index
- **Codedb is O(1) for word lookups** - much faster than grep for identifiers

## Example Usage

```python
# Check status
codedb_status(project="/home/levybonito/Projetos/MindFlow/python/mindflow_backend")

# Search for a concept
codedb_search(
    query="authentication flow",
    project="/home/levybonito/Projetos/MindFlow/python/mindflow_backend",
    scope=true
)

# Find a symbol
codedb_symbol(
    name="PlannerAgent",
    body=true,
    project="/home/levybonito/Projetos/MindFlow/python/mindflow_backend"
)

# Get file outline
codedb_outline(
    path="agents/planner_agent.py",
    project="/home/levybonito/Projetos/MindFlow/python/mindflow_backend"
)

# Check dependencies before modifying
codedb_deps(
    path="agents/planner_agent.py",
    project="/home/levybonito/Projetos/MindFlow/python/mindflow_backend"
)
```

## Performance

- codedb_search: <1ms for most queries
- codedb_word: O(1) - instant lookup
- codedb_symbol: <1ms
- codedb_outline: <100µs
- codedb_read: <100µs with hash validation
