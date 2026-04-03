# PLANO DE IMPLEMENTAÇÃO: Sistema de Build Tools Claude Code → MindFlow

## 📋 Resumo Executivo

Este plano implementa as funcionalidades avançadas de ferramentas do Claude Code no MindFlow, focando em:

- Build Tool pattern com defaults inteligentes
- Deferred loading para ferramentas MCP
- Progress callbacks em tempo real
- Synthetic error messages
- Progress tracking avançado

---

## 🎯 Componentes a Implementar

### FASE 1: Fundação (Prioridade CRÍTICA)

#### 1.1 build_tool() Pattern

**Arquivo:** `python/mindflow_backend/schemas/tools/builder.py`

**Responsabilidades:**

- Factory function para criar ferramentas com defaults
- Type safety com Generics
- Interrupt behavior configuration
- Max result size limits

**Estrutura:**

```python
@dataclass
class ToolBuilder(Generic[TInput, TOutput]):
    name: str
    description: str | Callable[[], str]
    input_schema: type[TInput]
    callable: Callable[[TInput, ToolContext], TOutput]
    is_concurrency_safe: bool = True
    is_read_only: bool = False
    interrupt_behavior: InterruptBehavior = InterruptBehavior.BLOCK
    max_result_size_chars: int = 100_000
    timeout_seconds: float = 30.0
```

#### 1.2 Deferred Tool Loader

**Arquivo:** `python/mindflow_backend/agents/tools/deferred_loader.py`

**Responsabilidades:**

- Gerenciar carregamento lazy de ferramentas
- Search tool por query
- Cache de ferramentas carregadas

#### 1.3 Tool Search Tool

**Arquivo:** `python/mindflow_backend/agents/tools/search_tool.py`

**Responsabilidades:**

- Busca por ferramentas deferred
- Select prefix: `select:ToolA,ToolB`
- Keyword search

---

### FASE 2: Progress e Erros (Prioridade ALTA)

#### 2.1 Progress Callbacks

**Arquivo:** `python/mindflow_backend/schemas/tools/progress.py`

**Responsabilidades:**

- ProgressType enum: STARTED, PROGRESS, COMPLETED, ERROR
- ToolProgress dataclass
- ProgressCallback protocol

#### 2.2 Synthetic Error Messages

**Arquivo:** `python/mindflow_backend/schemas/tools/errors.py`

**Responsabilidades:**

- ErrorReason enum
- SyntheticError dataclass com mensagens contextuais
- Integração com StreamingToolExecutor

---

### FASE 3: Integração (Prioridade ALTA)

#### 3.1 StreamingToolExecutor Enhancement

**Arquivo:** `python/mindflow_backend/runtime/execution/streaming_executor.py`

**Melhorias:**

- Integrar progress callbacks
- Integrar synthetic errors
- Melhorar sibling abort control
- Adicionar pending_progress queue

#### 3.2 ToolDefinition Enhancement

**Arquivo:** `python/mindflow_backend/runtime/execution/streaming_executor.py`

**Melhorias:**

- Adicionar interrupt_behavior
- Adicionar is_read_only
- Adicionar max_result_size_chars
- Adicionar timeout_seconds

---

## 📊 Estado Atual vs Objetivo (ATUALIZADO)

| Componente | Status | Arquivo | Notas |
|-----------|--------|---------|-------|
| StreamingToolExecutor | ✅ Implementado | `runtime/execution/streaming_executor.py` | Completo com hooks |
| ToolDefinition | ✅ Atualizado | `runtime/execution/streaming_executor.py` | Adicionado interrupt_behavior, is_read_only, timeout |
| is_concurrency_safe | ✅ Implementado | `runtime/execution/streaming_executor.py` | Funcional |
| AbortController | ✅ Implementado | `schemas/tools/streaming_types.py` | Hierárquico |
| Semaphore | ✅ Implementado | `runtime/execution/streaming_executor.py` | asyncio.Semaphore |
| **build_tool()** | ✅ **IMPLEMENTADO** | `schemas/tools/builder.py` | Factory + ToolBuilder fluent |
| **Deferred Loading** | ✅ **IMPLEMENTADO** | `agents/tools/deferred_loader.py` | DeferredToolLoader + search |
| **Tool Search** | ✅ **IMPLEMENTADO** | `agents/tools/search_tool.py` | ToolSearch + ToolInfo |
| **Synthetic Errors** | ✅ **IMPLEMENTADO** | `schemas/tools/errors.py` | ErrorReason + 9 tipos de erro |
| Progress Callbacks | ✅ Implementado | `schemas/tools/progress.py` | Tipos robustos existentes |
| Progress Tracking | ✅ Implementado | `runtime/execution/streaming_executor.py` | TrackedTool completo |

---

## 🔄 Ordem de Implementação

1. **build_tool() pattern** - Base para todas as ferramentas
2. **ToolDefinition enhancement** - Expandir definição existente
3. **Progress callbacks** - Sistema de progresso
4. **Synthetic errors** - Tratamento de erros
5. **Deferred loading** - Carregamento lazy
6. **Tool search** - Busca de ferramentas
7. **StreamingToolExecutor integration** - Integrar tudo

---

## 📁 Arquivos a Criar/Modificar

### Novos Arquivos

- `python/mindflow_backend/schemas/tools/builder.py`
- `python/mindflow_backend/agents/tools/deferred_loader.py`
- `python/mindflow_backend/agents/tools/search_tool.py`
- `python/mindflow_backend/schemas/tools/errors.py`

### Arquivos a Modificar

- `python/mindflow_backend/runtime/execution/streaming_executor.py`
- `python/mindflow_backend/schemas/tools/progress.py`
- `python/mindflow_backend/schemas/tools/__init__.py`
- `python/mindflow_backend/agents/tools/__init__.py`

---

## ✅ Critérios de Sucesso

1. **build_tool()** funciona com defaults inteligentes
2. **Deferred loading** carrega ferramentas sob demanda
3. **Progress callbacks** emitem atualizações em tempo real
4. **Synthetic errors** geram mensagens contextuais
5. **Progress tracking** rastreia estado detalhado
6. **StreamingToolExecutor** integra todos os componentes
7. **Testes unitários** passam para todos os componentes

---

## 🚀 Próximos Passos

1. Revisar este plano
2. Implementar Fase 1 (build_tool, deferred_loader, search_tool)
3. Implementar Fase 2 (progress, errors)
4. Implementar Fase 3 (integração)
5. Testes e validação
6. Documentação

---

*Data: 2026-04-02*
*Responsável: MindFlow AI Architecture Team*
