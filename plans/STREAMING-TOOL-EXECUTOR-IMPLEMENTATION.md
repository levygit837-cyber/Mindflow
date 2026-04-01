# Plano de Implementação: StreamingToolExecutor para MindFlow

## 📊 Análise da Arquitetura Atual

### Componentes Existentes Relevantes

1. **RuntimeExecutor** (`runtime/execution/executor.py`): Executa ferramentas, mas sem controle de concorrência sofisticado
2. **StreamManager** (`runtime/streaming/stream_manager.py`): Cria eventos de stream, mas não executa ferramentas em paralelo
3. **ParallelNode** (`nodes/implementations/control/parallel_node.py`): Já tem suporte a execução paralela com `asyncio.gather` e semáforos
4. **StreamableNode** (`nodes/base/streamable.py`): Suporte a streaming de nós
5. **ToolExecutionBatch** (`schemas/tools/tool_execution.py`): Suporte a batch execution com `max_concurrent` e `fail_fast`

### Gap Identificado

O MindFlow **já tem** os componentes básicos para execução paralela e streaming, mas **não tem** um `StreamingToolExecutor` integrado que:

- Execute ferramentas conforme chegam no stream (não espera todas)
- Controle concorrência com `concurrent_safe` flag
- Buffer resultados e emita em ordem
- Abort subprocessos irmãos em caso de erro

---

## 🎯 Arquitetura Proposta

### Visão Geral

```
┌─────────────────────────────────────────────────────────┐
│                   StreamingToolExecutor                  │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Tool Queue  │  │ Concurrency │  │ Result      │    │
│  │ (pending)   │──│ Controller  │──│ Buffer      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│         │                │                │             │
│         ▼                ▼                ▼             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Tool        │  │ Abort       │  │ Discard     │    │
│  │ Executor    │  │ Controller  │  │ Manager     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Componentes Principais

#### 1. TrackedTool (Ferramenta Rastreada)

```python
@dataclass
class TrackedTool:
    """Ferramenta rastreada pelo executor."""
    id: str                          # ID único da ferramenta
    block: ToolUseBlock              # Bloco de uso da ferramenta
    assistant_message: AssistantMessage  # Mensagem do assistente
    status: ToolStatus               # Status: pending, running, completed, error, discarded
    is_concurrency_safe: bool        # Se pode rodar em paralelo
    results: list[ToolResult]        # Resultados da execução
    started_at: float | None = None  # Timestamp de início
    completed_at: float | None = None  # Timestamp de conclusão
```

#### 2. StreamingToolExecutor

```python
class StreamingToolExecutor:
    """Executa ferramentas conforme chegam no stream.
    
    Características:
    - Ferramentas concorrentes podem rodar em paralelo
    - Ferramentas não-concorrentes rodam sozinhas
    - Resultados são bufferados e emitidos em ordem
    - Abort Controller cancela subprocessos em caso de erro
    
    Inspirado no StreamingToolExecutor do Claude Code.
    """
    
    def __init__(
        self,
        tool_definitions: Tools,
        can_use_tool: CanUseToolFn,
        tool_use_context: ToolUseContext,
        max_concurrent: int = 5,
    ):
        self._tools: list[TrackedTool] = []
        self._tool_definitions = tool_definitions
        self._can_use_tool = can_use_tool
        self._tool_use_context = tool_use_context
        self._max_concurrent = max_concurrent
        
        # Abort Controller para subprocessos
        self._sibling_abort_controller = create_child_abort_controller(
            tool_use_context.abort_controller,
        )
        
        # Semáforo para controle de concorrência
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Estado interno
        self._has_errored = False
        self._discarded = False
        self._running_tasks: dict[str, asyncio.Task] = {}
        
        # Integração com HookManager
        self._hook_manager = HookManager.get_instance()
```

---

## 📋 Plano de Implementação

### Fase 1: Tipos e Estruturas (1-2 dias)

**Arquivos:**

- `schemas/tools/tool_execution.py`: Adicionar `TrackedTool`, `ToolStatus`
- `schemas/tools/__init__.py`: Exportar novos tipos

**Tarefas:**

- [ ] Criar `ToolStatus` enum (pending, running, completed, error, discarded)
- [ ] Criar `TrackedTool` dataclass
- [ ] Criar `ToolResult` dataclass com status
- [ ] Atualizar `ToolExecutionBatch` para suportar streaming

### Fase 2: StreamingToolExecutor Core (3-5 dias)

**Arquivos:**

- `runtime/execution/streaming_executor.py`: NOVO
- `runtime/execution/__init__.py`: Exportar StreamingToolExecutor

**Tarefas:**

- [ ] Implementar `StreamingToolExecutor` com:
  - `add_tool()`: Adiciona ferramenta à fila
  - `get_remaining_results()`: Retorna resultados conforme ficam prontos
  - `discard()`: Descarta ferramentas pendentes
  - `_execute_tool()`: Executa ferramenta com controle de concorrência
- [ ] Implementar controle de concorrência com semáforo
- [ ] Implementar Abort Controller para subprocessos
- [ ] Implementar integração com HookManager

### Fase 3: Integração com RuntimeExecutor (2-3 dias)

**Arquivos:**

- `runtime/execution/executor.py`: Modificar

**Tarefas:**

- [ ] Adicionar método `execute_with_streaming()` ao RuntimeExecutor
- [ ] Integrar StreamingToolExecutor com fluxo existente
- [ ] Manter backward compatibility com execução sequencial
- [ ] Adicionar feature flag para habilitar streaming

### Fase 4: Integração com StreamManager (2-3 dias)

**Arquivos:**

- `runtime/streaming/stream_manager.py`: Modificar

**Tarefas:**

- [ ] Adicionar método `stream_tool_execution()` ao StreamManager
- [ ] Criar eventos de stream para tool execution:
  - `tool_start`: Quando ferramenta inicia
  - `tool_progress`: Durante execução
  - `tool_result`: Quando ferramenta completa
  - `tool_error`: Quando ferramenta falha
- [ ] Integrar com fluxo de streaming existente

### Fase 5: Testes e Validação (3-5 dias)

**Arquivos:**

- `tests/unit/runtime/execution/test_streaming_executor.py`: NOVO
- `tests/unit/runtime/execution/test_tracked_tool.py`: NOVO

**Tarefas:**

- [ ] Testes unitários para StreamingToolExecutor
- [ ] Testes unitários para TrackedTool
- [ ] Testes de integração com RuntimeExecutor
- [ ] Testes de integração com StreamManager
- [ ] Testes de concorrência e thread-safety
- [ ] Testes de abort e cleanup

### Fase 6: Documentação e Exemplos (1-2 dias)

**Arquivos:**

- `docs/architecture/STREAMING_TOOL_EXECUTOR.md`: NOVO
- `examples/streaming_tool_execution.py`: NOVO

**Tarefas:**

- [ ] Documentar arquitetura do StreamingToolExecutor
- [ ] Documentar como usar com exemplos
- [ ] Criar exemplos de uso
- [ ] Atualizar README principal

---

## 🎯 Métricas de Sucesso

| Métrica | Objetivo | Como Medir |
|---------|----------|------------|
| **Execução Paralela** | 50% de melhoria em tarefas multi-ferramenta | Benchmark com 5+ ferramentas |
| **Latência** | 30% de redução em latência de streaming | Medição de TTFT (Time To First Token) |
| **Concorrência** | Suporte a 10+ ferramentas simultâneas | Teste de carga |
| **Abort** | 100% de subprocessos abortados em caso de erro | Teste de cenários de erro |
| **Hooks** | 100% de integração com HookManager existente | Teste de hooks |

---

## ⚠️ Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| **Breaking Changes** | Média | Alto | Feature flag para desabilitar streaming |
| **Performance Overhead** | Baixa | Média | Benchmark antes/depois |
| **Complexidade** | Média | Média | Documentação detalhada |
| **Thread Safety** | Baixa | Alto | Testes de concorrência |

---

## 🚀 Próximos Passos

1. **Revisão do Plano**: Discutir com a equipe
2. **Feature Flag**: Criar feature flag para habilitar streaming
3. **Fase 1**: Implementar tipos e estruturas
4. **Fase 2**: Implementar StreamingToolExecutor core
5. **Fase 3**: Integrar com RuntimeExecutor
6. **Fase 4**: Integrar com StreamManager
7. **Fase 5**: Testes e validação
8. **Fase 6**: Documentação e exemplos

**Tempo Estimado Total:** 12-18 dias úteis
**Equipe Necessária:** 1-2 desenvolvedores
