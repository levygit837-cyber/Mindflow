# Research Phase 3: Tool Registry & Decomposition Thinking (DT)

## 1. Tool Registry & DeepAgents Integration

### 1.1 DeepAgents Tools Analysis
`deepagents` provides several backends in `deepagents.backends`:
- `FilesystemBackend`: Standard file operations (ls, read, write, edit, grep, glob).
- `LocalShellBackend`: Extends `FilesystemBackend` with `execute()`. **Warning:** No isolation.
- `BaseSandbox`: A protocol and base class for implementing sandboxed backends by only defining `execute()`.

### 1.2 Proposed ToolRegistry Structure
Location: `omnimind_backend/agents/tools/__init__.py`

```python
class ToolRegistry:
    def __init__(self, backend: BackendProtocol):
        self.backend = backend
        self._tools = {}

    def register_tool(self, name: str, func: Callable, scope: list[AgentType]):
        ...

    def get_tools_for_agent(self, agent_type: AgentType) -> list[Callable]:
        ...
```

### 1.3 Normalization Strategy
- **Input Normalization:** All tools should accept keyword arguments to remain provider-agnostic.
- **Output Normalization:** Use Pydantic models (from `deepagents.backends.protocol`) to wrap all tool outputs, ensuring consistent SSE events.
- **DeepAgents vs Custom:** 
    - Use `FilesystemBackend` methods directly as tools.
    - Wrap `execute()` for shell commands with a mandatory sandbox (e.g., via a specialized `OmniMindSandbox` that could use Docker or a restricted sub-process).

### 1.4 Sandbox for Shell
- The `ARCHITECTURE_PLAN.md` requires a "mandatory background sandbox".
- We will implement `OmniMindSandbox(BaseSandbox)` which delegates `execute()` to a safe environment.
- For local dev, this could be a restricted `subprocess` with resource limits and restricted paths, or a Docker container.

## 2. Decomposition Thinking (DT) Pipeline

### 2.1 Complexity Scorer (`orchestrator/complexity.py`)
- **Heuristics:** Number of files mentioned, keywords like "refactor", "create new project", "fix bug in multiple files".
- **LLM-based:** A small, fast model (e.g., Gemini Flash) to evaluate if the task needs decomposition.
- **Threshold:** 0.65 (default).

### 2.2 Pipeline Components (`orchestrator/decomposition/`)
- **Decomposer:** LLM prompt that outputs a JSON DAG: `[{"id": "task1", "description": "...", "dependencies": []}, ...]`.
- **Scheduler:** Topological sort of the DAG.
- **Resolver:** Iterates through scheduled tasks, selecting the best agent personality for each.
- **Synthesizer:** Final LLM pass to merge results from all sub-tasks into a coherent answer.

### 2.3 Persistence
- Need new tables for `dt_sessions` and `dt_tasks`.
- State must include `input`, `dag`, `current_task_id`, `results`, `status`.

## 3. Dependency & Security
- **Circular Imports:** `agents` defines personalities. `orchestrator` uses agents. `runtime` executes agents. 
    - `agents` must NOT import from `orchestrator`.
    - `ToolRegistry` belongs in `agents` (foundational).
- **Security:** Sanitize all tool inputs using `infra/sanitizer.py`.

## 4. Proposed Task Breakdown for Phase 3
1. Implement `ToolRegistry` and integrate `deepagents` FS tools.
2. Implement `OmniMindSandbox` for shell execution.
3. Define Tool Scopes per Agent Personality.
4. Implement DT Schemas and Migrations.
5. Implement Complexity Scorer.
6. Implement Decomposer, Scheduler, Resolver, Synthesizer.
7. Final E2E integration and SSE event wiring.
