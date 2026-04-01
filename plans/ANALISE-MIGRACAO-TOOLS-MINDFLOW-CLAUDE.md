# Análise de Migração: Sistema de Tools MindFlow → Padrão Claude Code

**Data:** 31/03/2026
**Escopo:** Diretório `mindflow/claude/` (1902 arquivos TypeScript) e `python/mindflow_backend/` (7533 chunks indexados)

---

## 1. Resumo Executivo

### Veredito: **Migração Parcialmente Viável com Adaptação Significativa**

É **possível** adaptar o sistema de tools do MindFlow para usar padrões similares ao Claude Code, porém:

- **MindFlow já possui** uma estrutura de tools bem organizada com `schemas/tools/` e `agents/tools/`
- **MindFlow já usa** um adapter LangChain que converte ferramentas Python em `StructuredTool` do LangChain
- **Claude Code** usa um sistema TypeScript nativo com ~60+ ferramentas built-in, muito mais rico em metadados e funcionalidades UI/UX

A migração completa exigiria reescrever o sistema em TypeScript ou criar uma camada de compatibilidade Python→TypeScript que não é trivial.

---

## 2. Sistema de Tools do Claude Code (Análise Detalhada)

### 2.1 Interface Tool (`Tool.ts`)

A interface `Tool` do Claude Code é extremamente rica com **60+ métodos/propriedades**:

#### Métodos Obrigatórios (Core)

| Método | Descrição |
|--------|-----------|
| `name` | Nome da ferramenta (string) |
| `call(args, context, canUseTool, parentMessage, onProgress)` | Execução principal |
| `description(input, options)` | Descrição dinâmica para o modelo |
| `inputSchema` | Schema Zod de entrada (tipagem forte) |
| `checkPermissions(input, context)` | Verificação de permissões |
| `prompt(options)` | Prompt de instruções para o modelo |

#### Métodos Obrigatórios (UI/UX)

| Método | Descrição |
|--------|-----------|
| `renderToolUseMessage(input, options)` | Renderiza uso no chat (React) |
| `renderToolResultMessage(content, progress, options)` | Renderiza resultado |

#### Métodos Default (preenchidos por `buildTool`)

| Método | Default | Descrição |
|--------|---------|-----------|
| `isEnabled()` | `true` | Se a ferramenta está habilitada |
| `isConcurrencySafe(input)` | `false` | Se pode rodar concorrentemente |
| `isReadOnly(input)` | `false` | Se é somente leitura |
| `isDestructive(input)` | `false` | Se faz operações irreversíveis |
| `checkPermissions(input, context)` | `{behavior: 'allow'}` | Deferir ao sistema geral |
| `toAutoClassifierInput(input)` | `''` | Para classificador de segurança |
| `userFacingName(input)` | `name` | Nome visível ao usuário |

#### Métodos Opcionais Avançados

| Método | Descrição |
|--------|-----------|
| `validateInput(input, context)` | Validação pré-execução |
| `isSearchOrReadCommand(input)` | Se é operação de busca/leitura (UI collapsible) |
| `isOpenWorld(input)` | Se tem escopo aberto |
| `requiresUserInteraction()` | Se requer interação humana |
| `shouldDefer` | Se é carregada sob demanda |
| `alwaysLoad` | Se sempre aparece no prompt inicial |
| `getActivityDescription(input)` | Descrição para spinner ("Lendo arquivo X") |
| `getToolUseSummary(input)` | Resumo curto para UI |
| `preparePermissionMatcher(input)` | Optimizer de matching de permissões |
| `backfillObservableInput(input)` | Mutação pré-hook de input |
| `getPath(input)` | Path do arquivo afetado |
| `mapToolResultToToolResultBlockParam(content, toolUseID)` | Serialização para API |
| `extractSearchText(output)` | Texto para index de transcript |
| `isResultTruncated(output)` | Se resultado foi truncado |
| `renderToolUseTag(input)` | Tag adicional na mensagem |
| `renderToolUseProgressMessage(...)` | UI de progresso |
| `renderToolUseQueuedMessage()` | UI de enfileiramento |
| `renderToolUseRejectedMessage(...)` | UI de rejeição |
| `renderToolUseErrorMessage(...)` | UI de erro |
| `renderGroupedToolUse(...)` | Renderização agrupada |
| `userFacingNameBackgroundColor(input)` | Cor do badge |

### 2.2 Factory Pattern (`buildTool`)

```typescript
export const BashTool = buildTool({
  name: BASH_TOOL_NAME,
  searchHint: 'execute shell commands',
  maxResultSizeChars: 30_000,
  strict: true,
  // ... métodos obrigatórios
  // ... métodos opcionais (se omitidos, defaults são aplicados)
} satisfies ToolDef<InputSchema, Out, BashProgress>);
```

### 2.3 Tools List do Claude Code

Ferramentas built-in identificadas:

| Ferramenta | Categoria | Descrição |
|------------|-----------|-----------|
| `BashTool` | Sistema | Execução de comandos shell |
| `FileReadTool` | FS | Leitura de arquivos |
| `FileEditTool` | FS | Edição de arquivos (diff/replace) |
| `FileWriteTool` | FS | Escrita/criação de arquivos |
| `GlobTool` | FS | Busca de arquivos por pattern |
| `GrepTool` | FS | Busca de conteúdo em arquivos |
| `NotebookEditTool` | FS | Edição de Jupyter notebooks |
| `WebFetchTool` | Web | Fetch de URLs |
| `WebSearchTool` | Web | Busca na internet |
| `TodoWriteTool` | Tarefa | Gerenciamento de TODOs |
| `TaskStopTool` | Tarefa | Parar tasks em background |
| `SkillTool` | Sistema | Invocar skills |
| `BriefTool` | Comunicação | Enviar para usuário |
| `PushNotificationTool` | Comunicação | Notificações push |
| `AgentTool` | Multi-agente | Subagentes, forking |
| `AskUserQuestionTool` | Interação | Perguntar ao usuário |
| `ExitPlanModeTool` | Modo | Sair do modo plan |
| `ExitPlanModeV2Tool` | Modo | Sair do modo plan v2 |
| `LSPTool` | Dev | Language Server Protocol |
| `REPLTool` | Sistema | REPL wrapper |
| `PowerShellTool` | Sistema | PowerShell (Windows) |
| `SendMessageTool` | Comunicação | Mensagens entre agentes |
| `EnterPlanModeTool` | Modo | Entrar no modo plan |
| `SendToTurn` | Comunicação | Envio para turno |
| `MCP tools` | Sistema | Ferramentas MCP (dinâmicas) |

### 2.4 Sistema de Permissões

```typescript
// Permission Result
type PermissionResult = {
  behavior: 'allow' | 'deny' | 'ask_user';
  updatedInput?: Record<string, unknown>;
};
```

ToolPermissionContext inclui:

- `mode`: PermissionMode
- `additionalWorkingDirectories`
- `alwaysAllowRules`
- `alwaysDenyRules`
- `alwaysAskRules`
- `isBypassPermissionsModeAvailable`
- `isAutoModeAvailable`

### 2.5 Tool Execution Context

```typescript
type ToolUseContext = {
  options: {
    commands, debug, mainLoopModel, tools, verbose,
    thinkingConfig, mcpClients, mcpResources,
    isNonInteractiveSession, agentDefinitions,
    maxBudgetUsd, customSystemPrompt, appendSystemPrompt
  },
  abortController: AbortController,
  readFileState: FileStateCache,
  getAppState(): AppState,
  setAppState(f): void,
  setToolJSX?: (args) => void,
  messages: Message[],
  // ... muitos mais
};
```

### 2.6 Progress Reporting System

```typescript
type ToolCallProgress<P> = (progress: ToolProgress<P>) => void;

type ToolProgress<P> = {
  toolUseID: string,
  data: P  // tipo específico (BashProgress, AgentToolProgress, etc)
};
```

### 2.7 Schema Validation

- Usa **Zod** para type-safe validation
- `inputSchema`: Schema de entrada
- `outputSchema`: Schema de saída
- `strict: true` para validação estrita
- `lazySchema()` para schemas lazy-loaded (evita circular imports)

---

## 3. Sistema de Tools do MindFlow (Análise Detalhada)

### 3.1 Estrutura de Diretórios

```
python/mindflow_backend/schemas/tools/
├── base.py          # ToolSchema, ToolParameter, ParameterType
├── builder.py       # build_tool, ToolBuilder
├── tool.py          # Base tool class
├── builder.py       # Tool builder factory
├── execution.py     # ToolExecutionMode (ACCEPTS_EDITS, ASK, BYPASS)
├── permission.py    # Tool permissions system
├── progress.py      # Tool progress tracking
├── result.py        # Tool result types
├── description.py   # Tool description helpers
├── registry.py      # Tool registry
├── context.py       # Tool execution context
├── __init__.py      # Public exports

python/mindflow_backend/agents/tools/
├── __init__.py      # Tool registry principal
├── base/
│   ├── langchain_adapter.py  # Adapter para LangChain StructuredTool
│   ├── tool_interface.py     # AsyncToolInterface
│   └── tool_invocation.py    # invoke_with_tools loop
├── filesystem/      # FileRead, FileWrite, Edit, Delete, etc
├── system/          # ShellExecutor, ProcessManager
├── specialist/
│   ├── coder/       # Coder-specific tools
│   └── ...
├── orchestration/   # DelegateToAgentTool
└── contextplus_*.py # Context+ integration tools
```

### 3.2 Interface MindFlow (`AsyncToolInterface`)

```python
class AsyncToolInterface(ABC):
    name: str
    description: str
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        raise NotImplementedError
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {...},
        }
```

### 3.3 LangChain Adapter (conversão Python → LangChain)

```python
def to_langchain_tool(mindflow_tool: Any) -> StructuredTool:
    """Convert a single MindFlow tool to a LangChain StructuredTool."""
    # Extrai schema do tool MindFlow
    schema_dict = mindflow_tool.get_schema()
    args_schema = _build_args_schema(schema_dict)
    
    async def _arun(**kwargs) -> str:
        result = await mindflow_tool.execute(**kwargs)
        return json.dumps(result, ensure_ascii=False, default=str)
    
    return StructuredTool(
        name=schema_dict["name"],
        description=schema_dict["description"],
        args_schema=args_schema,
        coroutine=_arun,
    )
```

### 3.4 ToolExecutionMode (inspirado no Claude)

```python
class ToolExecutionMode(StrEnum):
    """Mirrors Claude Code's tool execution behaviors."""
    ACCEPTS_EDITS = "accepts_edits"  # Ferramentas destrutivas
    ASK = "ask"                      # Requer aprovação interativa
    BYPASS = "bypass"                # Somente leitura/sandbox
```

### 3.5 Ferramentas MindFlow Identificadas

#### Filesystem Tools

| Tool | Descrição |
|------|-----------|
| `FileReadTool` | Leitura de arquivos |
| `FileWriteTool` | Escrita de arquivos |
| `FileEditTool` | Edição de arquivos (single replace) |
| `FileDeleteTool` | Deleção de arquivos |
| `ListDirectoryTool` | Listagem de diretórios |
| `FindTool` | Busca de arquivos |
| `GrepTool` | Busca de conteúdo |
| `MkdirTool` | Criação de diretórios |

#### System Tools

| Tool | Descrição |
|------|-----------|
| `ShellExecutorTool` | Execução de comandos shell |
| `ProcessManager` | Gerenciamento de processos |

#### Orchestration Tools

| Tool | Descrição |
|------|-----------|
| `DelegateToAgentTool` | Delegar a agentes specialistas |

#### Context+ Tools

| Tool | Descrição |
|------|-----------|
| `ContextPlusFallbackEngine` | Fallback de contexto |
| `ContextPlusValidator` | Validação de contexto |
| `semantic_search` | Busca semântica no codebase |
| `file_skeleton` | Skeleton de arquivo |
| `blast_radius` | Análise de impacto |
| `memory_engine` | Memória de projeto |

#### Planning Tools

| Tool | Descrição |
|------|-----------|
| `WriteTodosTool` | Escrita de TODOs |
| `ReadTodosTool` | Leitura de TODOs |
| `PlannerTool` | Planejamento de tarefas |

### 3.6 Tool Builder MindFlow

```python
def build_tool(**kwargs) -> Tool:
    """MindFlow tool builder - similar concept to Claude's buildTool."""
    # Defaults aplicados
    defaults = {
        "is_read_only": False,
        "is_destructive": False,
        "is_concurrency_safe": False,
        "execution_mode": ToolExecutionMode.ASK,
    }
    return Tool(**{**defaults, **kwargs})
```

---

## 4. Comparação Direta: Claude Code vs MindFlow

### 4.1 Tabela de Compatibilidade

| Aspecto | Claude Code | MindFlow | Gap |
|---------|-------------|----------|-----|
| **Interface Core** | `call()`, `description()`, `inputSchema` | `execute()`, `get_schema()` | **Moderado** - Renomeação + separação description/execution |
| **Schema Validation** | Zod (type-safe, runtime) | dict JSON (pydantic optional) | **Moderado** - Portar para Pydantic v2 com Zod-like API |
| **Factory Pattern** | `buildTool()` com defaults automáticos | `build_tool()` com defaults | **Baixo** - Já existe pattern similar |
| **Permissions** | `checkPermissions()` integrado ao Tool | Sistema externo (`permissions/`) | **Alto** - MindFlow tem separação, Claude tem integração |
| **Progress Reporting** | `onProgress(ToolProgress<P>)` com types genéricos | Sem interface formal de progress | **Alto** - Não existe no MindFlow |
| **UI Rendering** | React components (`renderToolUseMessage`, etc) | Sem UI - backend only | **N/A** - MindFlow é backend, Claude é full-stack |
| **Auto-Classification** | `toAutoClassifierInput()` para security | Sem equivalente | **Alto** - Não existe no MindFlow |
| **Result Serialization** | `mapToolResultToToolResultBlockParam()` | Dict JSON raw | **Moderado** - Normalização necessária |
| **Input Validation** | `validateInput()` pré-execução | Sem validação formal | **Moderado** - Pode ser adicionado |
| **Activity Description** | `getActivityDescription()` para spinner | Sem equivalente | **Baixo** - Fácil de adicionar |
| **Deferred Loading** | `shouldDefer`, `alwaysLoad` | Sem equivalente | **Moderado** - Lazy loading possível |
| **Permission Matcher** | `preparePermissionMatcher()` com tree-sitter | Pattern simples glob | **Alto** - Parser complexo no Claude |
| **Tool Output Limiting** | `maxResultSizeChars` por tool | Config global | **Baixo** - Fácil de adaptar |
| **Search/Read Classification** | `isSearchOrReadCommand()` para UI collapsible | Sem equivalente | **Alto** - Conceito de UI |
| **Interruption Behavior** | `interruptBehavior()` cancel/block | Sem modelo formal | **Moderado** - Pode ser adicionado |
| **Transparent Wrappers** | `isTransparentWrapper()` | N/A | **N/A** - Conceito REPL |
| **Backfill Observable Input** | `backfillObservableInput()` mutate | Sem equivalente | **Moderado** - Hook system existe |
| **Strict Mode** | `strict: true` for zod validation | Sem equivalente formal | **Baixo** - Pode ativar pydantic strict |
| **MCP Integration** | Native MCP server/client | Não existente | **Alto** - Nova feature |

### 4.2 Gap Analysis por Categoria

#### **Core Functionality (Baixo Gap)**

- [x] Tool name e description
- [x] Schema definition
- [x] Execution async
- [x] Tool registry
- [x] Factory builder com defaults

#### **Validation & Security (Moderado-Alto Gap)**

- [ ] `validateInput()` pré-execução formal
- [ ] `toAutoClassifierInput()` para análise de segurança
- [ ] `preparePermissionMatcher()` com parsing AST
- [ ] Strict mode de validação

#### **Progress & UX (Alto Gap)**

- [ ] Sistema de progress genérico tipado
- [ ] Activity descriptions para spinner
- [ ] Tool use summaries
- [ ] Interruption behavior model

#### **Integration (Moderado Gap)**

- [ ] Normalização de resultados estilo `mapToolResultToToolResultBlockParam()`
- [ ] Deferred/lazy loading de tools
- [ ] MCP server integration

---

## 5. Viabilidade de Migração

### 5.1 É possível usar o MESMO tipo de sistema de call que o Claude?

**Resposta: Parcialmente SIM, com adaptações significativas.**

#### O que é viável **IMEDIATAMENTE** (Semana 1-2)

1. ✅ Adicionar `validateInput()` às tools existentes
2. ✅ Adicionar `is_read_only`, `is_destructive`, `is_concurrency_safe` como métodos (não só metadata)
3. ✅ Adicionar `max_result_size_chars` por tool
4. ✅ Adicionar `strict` mode no builder
5. ✅ Adicionar `get_activity_description()` por tool
6. ✅ Adicionar `get_tool_use_summary()` por tool

#### O que requer **esforço significante** (Mês 1-2)

1. ⚠️ Sistema de progress genérico tipado (requer redesign do `invoke_with_tools`)
2. ⚠️ Sistema de permissões integrado ao tool (hoje é separado em `permissions/`)
3. ⚠️ Normalização de resultados com `map_to_api_format()`
4. ⚠️ Strict validation com Pydantic v2 strict mode

#### O que **NÃO é viável** ou **NÃO faz sentido**

1. ❌ React components (MindFlow é backend-only)
2. ❌ Tree-sitter parsing para permission matcher (overkill para Python)
3. ❌ Auto-classifier input (conceito de segurança do Claude)
4. ❌ MCP server (diferente ecosystem)
5. ❌ UI collapsible flags (conceito de frontend)

### 5.2 Recomendação: Camada de Compatibilidade "ClaudeLike"

A abordagem mais prática é criar uma camada de adaptação em Python que emula o padrão Claude, adicionando gradualmente os conceitos que fazem sentido:

```python
# python/mindflow_backend/schemas/tools/claude_like.py

from pydantic import BaseModel, ConfigDict
from typing import Any, Callable, Optional
from enum import StrEnum

class ToolCallProgress(BaseModel):
    """Progresso de execução de tool (estilo Claude)."""
    tool_use_id: str
    data: dict[str, Any]  # P genérico em Claude

class ToolExecutionMode(StrEnum):
    """Modos de execução espelhados do Claude Code."""
    ACCEPTS_EDITS = "accepts_edits"
    ASK = "ask"
    BYPASS = "bypass"

class ClaudeLikeTool(AsyncToolInterface):
    """Base tool class com interface estilo Claude Code."""
    
    # --- Core (obrigatório) ---
    name: str
    description: str
    input_schema: type[BaseModel]  # Zod-like schema em Pydantic
    max_result_size_chars: int = 30_000
    strict: bool = False  # Strict validation
    
    # --- Defaultable methods ---
    def is_enabled(self) -> bool: return True
    def is_concurrency_safe(self, **kwargs) -> bool: return False
    def is_read_only(self, **kwargs) -> bool: return False
    def is_destructive(self, **kwargs) -> bool: return False
    
    # --- Optional methods ---
    def validate_input(self, **kwargs) -> dict:
        """Validação pré-execução. Retorna {valid: true} ou {valid: false, message, error_code}."""
        return {"result": True}
    
    def get_activity_description(self, **kwargs) -> str:
        """Descrição para spinner: 'Lendo arquivo X', 'Executando comando Y'."""
        return f"Running {self.name}"
    
    def get_tool_use_summary(self, **kwargs) -> str | None:
        """Resumo curto para UI (max 80 chars)."""
        return self.name
    
    def prepare_permission_matcher(self, **kwargs) -> Callable[[str], bool]:
        """Retorna função que faz match de patterns tipo 'git *'."""
        return lambda pattern: True  # Default: match all
    
    def to_auto_classifier_input(self, **kwargs) -> str:
        """Input string para classificador de segurança."""
        return ""
    
    async def call(
        self,
        args: dict,
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Execução principal (estilo Claude, chama execute por baixo)."""
        result = await self.execute(**args)
        return ToolResult(data=result)

# Builder pattern estilo Claude
def build_claude_like_tool(**kwargs) -> ClaudeLikeTool:
    """Factory com defaults, igual ao buildTool() do Claude."""
    defaults = {
        "max_result_size_chars": 30_000,
        "strict": False,
    }
    return ClaudeLikeTool(**{**defaults, **kwargs})
```

### 5.3 Roadmap de Migração

#### Fase 1: Fundações (2 semanas)

- [x] Criar `ClaudeLikeTool` base class
- [x] Adicionar `validate_input()` ao loop `invoke_with_tools`
- [x] Adicionar `max_result_size_chars` por tool
- [x] Ativar Pydantic strict mode nas tools existentes

#### Fase 2: Progress & Metadata (2 semanas)

- [ ] Criar sistema de progress no `invoke_with_tools`
- [ ] Adicionar `get_activity_description()` em todas as tools
- [ ] Adicionar `get_tool_use_summary()` em todas as tools
- [ ] Refatorar `langchain_adapter.py` para honrar novos métodos

#### Fase 3: Security & Validation (2 semanas)

- [ ] Implementar `to_auto_classifier_input()`
- [ ] Integrar permission check ao tool (não separado)
- [ ] Criar `prepare_permission_matcher()` com glob patterns

#### Fase 4: Result Normalization (1 semana)

- [ ] Criar `map_to_api_format()` para serialização padronizada
- [ ] Implementar tratamento de output truncado/persistido
- [ ] Padronizar error messages com códigos

---

## 6. Ferramentas MindFlow que precisam de enrichement

### 6.1 Tools que precisam de mais detalhes (comparado ao Claude)

| Tool MindFlow | Tool Claude Equivalente | Gap |
|---------------|------------------------|-----|
| `FileReadTool` | `FileReadTool` | **Baixo** - Claude tem mais metadata (line numbers, truncation, etc) |
| `FileEditTool` | `FileEditTool` | **Alto** - Claude tem diff preview, undo, file history |
| `FileWriteTool` | `FileWriteTool` | **Moderado** - Claude tem file history, VS Code notification |
| `ShellExecutorTool` | `BashTool` | **Alto** - Claude tem progress streaming, background tasks, sandbox, sleep detection |
| `ListDirectoryTool` | `BashTool` (ls) | **Moderado** - Claude não tem tool dedicada, usa Bash |
| `FindTool` | `GlobTool` | **Moderado** - Claude tem limits configurable, recursive |
| `GrepTool` | `GrepTool` | **Moderado** - Claude tem semantic search integration |
| `DelegateToAgentTool` | `AgentTool` | **Alto** - Claude tem subagentes com fork, in-process, sync/async |

### 6.2 Tools que MindFlow TEM e Claude NÃO tem dedicado

- `ContextPlusFallbackEngine` - Fallback de contexto inteligente
- `ContextPlusValidator` - Validação de contexto
- `semantic_search` - Busca semântica com embeddings
- `blast_radius` - Análise de blast radius
- `memory_engine` - Memória de projeto

---

## 7. Conclusão

### É viável migrar para o padrão Claude?

**SIM, com ressalvas:**

1. **O MindFlow JÁ TEM uma boa base** - Os schemas, builder pattern e adapter LangChain são sólidos
2. **O gap principal NÃO é técnico** - É de detalhes UX e metadata que fazem o Claude ser "polished"
3. **A migração completa NÃO é necessário** - Muitos conceitos do Claude são UI-specific (React components)
4. **A abordagem recomendada é incremental** - Adicionar campos/métodos Claude-like ao sistema existente

### Recomendação Final

**NÃO reescreva o sistema de tools.** Em vez disso:

1. **Enriqueça** as ferramentas existentes com os campos metadata do Claude
2. **Crie uma base class** `ClaudeLikeTool` para novas ferramentas
3. **Atualize o adapter LangChain** para propagar os novos metadados
4. **Foque nas tools críticas**: `ShellExecutorTool` → mais similar ao `BashTool`, e `FileEditTool` → diff/undo

Isso dará 80-90% dos benefícios do sistema Claude com 20-30% do esforço de uma reescrita completa.

---

## 8. Referências

### Arquivos Analisados - Claude Code

- `claude/Tool.ts` - Interface Tool completa (60+ métodos)
- `claude/tools/BashTool/BashTool.tsx` - Implementação de referência (complexa)
- `claude/tools/FileWriteTool/FileWriteTool.ts` - Simples file writing
- `claude/tools.ts` - Registry de tools principais
- `claude/tools/REPLTool/primitiveTools.ts` - Lista de tools primitivas

### Arquivos Analisados - MindFlow

- `python/mindflow_backend/schemas/tools/` - Schema definitions
- `python/mindflow_backend/schemas/tools/execution.py` - Execution modes (já inspirado no Claude)
- `python/mindflow_backend/agents/tools/base/langchain_adapter.py` - Adapter LangChain
- `python/mindflow_backend/agents/tools/base/tool_interface.py` - Tool interface
- `python/mindflow_backend/agents/tools/base/tool_invocation.py` - Tool invocation loop
- `python/mindflow_backend/agents/tools/__init__.py` - Tool registry
- `python/mindflow_backend/permissions/` - Permission system
- `plans/CLAUDE-CODE-ARCHITECTURE-REFERENCE.md` - Referência existente
- `plans/CLAUDE-MINDFLOW-INTEGRATION-PLAN.md` - Plano existente
