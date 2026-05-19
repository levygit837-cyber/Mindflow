# Mapeamento de Dependências das Engines

## DelegationEngine Dependências (14 arquivos)

### Diretos (importam DelegationEngine)
1. `api/controllers/a2a_controller.py` - A2A controller
2. `agents/tools/orchestration/delegate_to_agent.py` - Tool de delegação
3. `orchestrator/step_runner.py` - Step runner (usa get_delegation_engine)
4. `orchestrator/delegation/__init__.py` - Export do módulo
5. `orchestrator/delegation/converter.py` - Converter WorkflowStep → DelegationTask
6. `orchestrator/routing/intelligent_router.py` - Router inteligente (usa get_delegation_engine)

### Testes
7. `tests/unit/execution/test_delegation_integration.py` - Testes de integração
8. `tests/integration/test_unified_execution_path.py` - Testes de caminho unificado

### Referências (comentários/docstrings)
9. `communication/a2a/a2a_client.py` - Cliente A2A (comentário)
10. `runtime/execution/legacy_compat.py` - Legacy compat (comentário)

### Interface Pública
```python
class DelegationEngine:
    async def delegate_task(
        self,
        task: DelegationTask,
        session: Any,
        *,
        session_id: str | None = None,
        root_execution_id: str | None = None,
        parent_execution_id: str | None = None,
    ) -> DelegationResult

    def _delegation_primary(...) -> DelegationResult
    def _delegation_secondary(...) -> DelegationResult
    def _handle_memory_grounded(...) -> bool
    def _register_fallback_handlers(...) -> None
```

---

## RuntimeExecutor Dependências (9 arquivos)

### Diretos (importam RuntimeExecutor)
1. `runtime/core/agent_runtime.py` - AgentRuntime principal
2. `runtime/execution/__init__.py` - Export do módulo
3. `runtime/__init__.py` - Export do módulo
4. `runtime/execution/executor.py` - Self-import interno

### Indiretos (usam StreamingToolExecutor do runtime.execution)
5. `tests/unit/runtime/execution/test_unified_tool_execution.py` - Testes
6. `tests/unit/runtime/execution/test_unified_tool_execution_simple.py` - Testes
7. `archive/tool_invocation.py` - Archive (usa StreamingToolExecutor)
8. `archive/callable_executor.py` - Archive (re-export)
9. `archive/tool_loop.py` - Archive (usa StreamingToolExecutor)

### Interface Pública
```python
class RuntimeExecutor:
    async def stream_orchestrated(...) -> AsyncGenerator
    async def stream_direct_agent(...) -> AsyncGenerator
    async def stream_legacy(...) -> AsyncGenerator
    async def _get_orchestrator_graph(...) -> Any
    async def _execute_with_tools(...) -> dict
```

---

## StepRunner Dependências (4 arquivos)

### Diretos (importam run_workflow_step)
1. `chains/templates/coding_task_chain.py` - Chain de coding task
2. `orchestrator/planning_flow.py` - Planning flow
3. `graphs/implementations/orchestrator/simple_flow.py` - Simple flow graph

### Referências
4. `orchestrator/delegation/converter.py` - Converter (comentário)
5. `schemas/orchestration/delegation.py` - Schema (comentário)

### Interface Pública
```python
async def run_workflow_step(
    *,
    step: WorkflowStep,
    user_message: str,
    provider: str,
    model: str,
    session_id: str,
    folder_path: str | None = None,
    memory_context: str = "",
    memory_grounded: bool = False,
    conversation_history: list[dict[str, str]] | None = None,
    prior_context: str = "",
    chunk_dispatcher: ChunkDispatcher = None,
    event_dispatcher: EventDispatcher = None,
) -> dict[str, Any]
```

---

## UnifiedExecutionEngine Dependências (4 arquivos)

### Diretos
1. `execution/__init__.py` - Export do módulo
2. `execution/unified_engine.py` - Self-import
3. `execution/agent_team_manager.py` - Team manager
4. `runtime/unified_engine_adapter.py` - Adapter (DEAD CODE)

### Interface Pública
```python
class UnifiedExecutionEngine:
    async def execute(
        self,
        strategy: ExecutionStrategy,
        context: ExecutionContext,
    ) -> ExecutionResult

    def _execute_single_agent(...) -> ExecutionResult
    def _execute_team_session(...) -> ExecutionResult
    def _execute_chain(...) -> ExecutionResult
    def _execute_graph(...) -> ExecutionResult
    def _execute_direct_response(...) -> ExecutionResult
```

---

## UnifiedEngineAdapter Dependências (1 arquivo)

### Diretos
1. `runtime/unified_engine_adapter.py` - Self apenas (DEAD CODE)

**Status:** DEAD CODE - Não usado em nenhum lugar

---

## StreamingToolExecutor (runtime.execution.streaming_executor)

### Usado por (já existe no MindFlow)
1. `runtime/execution/executor.py` - RuntimeExecutor
2. `runtime/execution/callable_adapter.py` - Callable adapter
3. `runtime/execution/__init__.py` - Export
4. `archive/tool_invocation.py` - Archive
5. `archive/tool_loop.py` - Archive
6. `archive/callable_executor.py` - Archive

**Nota:** Já existe uma implementação de StreamingToolExecutor no MindFlow em `runtime/execution/streaming_executor.py`. Precisamos avaliar se podemos reutilizá-la ou se precisamos adaptar a versão do Claude Code.

---

## Resumo de Ações de Migração

### DelegationEngine → QueryEngine
- Mover lógica para QueryEngine
- Atualizar 6 imports diretos
- Atualizar 2 testes
- Remover comentários/referências

### RuntimeExecutor → QueryEngine
- Migrar AgentRuntime para usar QueryEngine
- Atualizar 4 imports diretos
- Avaliar StreamingToolExecutor existente vs Claude Code
- Remover archive references

### StepRunner → QueryEngine
- Adicionar método execute_workflow_step no QueryEngine
- Atualizar 3 imports diretos
- Remover converter.py
- Remover comentários/referências

### UnifiedExecutionEngine → Remover
- Remover (apenas 4 dependências)
- Remover UnifiedEngineAdapter (DEAD CODE)

### Legacy Code → Remover
- Remover legacy_compat.py
- Remover archive/tool_loop.py
- Remover archive/tool_invocation.py (se não usado)
