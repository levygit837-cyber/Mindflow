# MindFlow Orchestration System — Code Documentation

## Overview

O sistema de orquestração do MindFlow implementa um padrão de **delegação inteligente** onde um Orquestrador central analisa intenções do usuário e delega tarefas para especialistas (Analyst, Coder, Researcher) com suporte a especialistas registrados (security_guard, critic, arch_tech, brainstorm, deep_iteration).

---

## Core Modules

### 1. IntelligentRouter (`orchestrator/routing/intelligent_router.py`)

**Propósito**: Análise de intenção baseada em LLM e roteamento inteligente de mensagens.

**Classe Principal**: `IntelligentRouter`

#### Métodos Públicos

```python
async def analyze_intent_with_llm(
    message: str,
    session_context: str = "",
    folder_path: str | None = None,
    has_folder_path: bool = False,
) -> IntentAnalysis
```
- **Descrição**: Usa LLM para analisar intenção do usuário e decidir estratégia de execução
- **Entrada**: Mensagem do usuário, contexto de sessão, caminho da pasta (opcional)
- **Saída**: `IntentAnalysis` com intenção, agente recomendado, especialista, confiança
- **Estratégias Suportadas**:
  - `direct_response` — Orquestrador responde diretamente (greetings, meta-questions)
  - `single_agent` — Delega para um agente único
  - `chain` — Executa múltiplos agentes em sequência
  - `graph` — Executa grafo de agentes

```python
async def route_message_strategy(
    message: str,
    session: OrchestratorSession | None = None,
    folder_path: str | None = None,
) -> WorkflowRouteDecision
```
- **Descrição**: Roteia mensagem usando análise de intenção, retorna decisão de workflow
- **Entrada**: Mensagem, sessão (opcional), caminho da pasta (opcional)
- **Saída**: `WorkflowRouteDecision` com agente, especialista, ferramentas, prioridade
- **Nota**: Responsabilidade do router termina em estratégia + identidade; resolução de chain/graph acontece na camada planner

```python
async def route_message_intelligently(
    message: str,
    session: OrchestratorSession | None = None,
    folder_path: str | None = None,
) -> OrchestratorDecision
```
- **Descrição**: Compatibilidade; retorna plano final de execução
- **Entrada**: Mensagem, sessão (opcional), caminho da pasta (opcional)
- **Saída**: `OrchestratorDecision` com plano de execução completo

#### Classe Interna: `IntentAnalysis`

```python
@dataclass
class IntentAnalysis(BaseModel):
    user_intent: str  # Interpretação clara da intenção
    recommended_agent: AgentType  # Agente recomendado (ANALYST, CODER, RESEARCHER, ORCHESTRATOR)
    recommended_specialist: str | None  # Especialista opcional (security_guard, critic, etc.)
    formulated_objective: str  # Objetivo preciso para o agente
    confidence: float  # Confiança da análise (0-1)
    is_multi_agent: bool  # Requer múltiplos agentes?
    agent_sequence: list[AgentType]  # Sequência de agentes se multi-agent
    execution_strategy: ExecutionStrategy  # Estratégia de execução
```

#### Fluxo de Análise

1. **Construir Roster Dinâmico**: Lê agentes registrados do registry
2. **Construir Prompt**: Inclui roster, estratégias, exemplos, regras
3. **Invocar LLM**: Envia prompt para análise
4. **Parsear Resposta**: Extrai JSON, valida com Pydantic
5. **Normalizar**: Converte strings para enums, trata valores nulos
6. **Retornar**: `IntentAnalysis` com decisão

#### Regras de Roteamento

| Estratégia | Quando Usar | Exemplo |
|-----------|-----------|---------|
| `direct_response` | Greetings, thanks, meta-questions | "olá", "quem é você?" |
| `single_agent` | Tarefa que um agente pode resolver | "explica o fluxo de delegação" |
| `chain` | Múltiplas fases distintas | "implementa feature X lendo código atual" |
| `graph` | Dependências complexas | (raro; para workflows muito complexos) |

---

### 2. DelegationEngine (`orchestrator/delegation/engine.py`)

**Propósito**: Executa tarefas delegadas para agentes, gerencia ciclo de vida, retorna resultados estruturados.

**Classe Principal**: `DelegationEngine`

#### Método Principal

```python
async def delegate_task(
    self,
    task: DelegationTask,
    session: Any,  # OrchestratorSession
    *,
    session_id: str | None = None,
    root_execution_id: str | None = None,
    parent_execution_id: str | None = None,
) -> DelegationResult
```

- **Descrição**: Executa uma tarefa delegada e retorna resultado estruturado
- **Entrada**:
  - `task`: `DelegationTask` com objetivo, escopo, contexto, saída esperada
  - `session`: Sessão do orquestrador
  - `session_id`, `root_execution_id`, `parent_execution_id`: IDs para rastreamento
- **Saída**: `DelegationResult` com status, achados, saída completa, confiança, tokens consumidos
- **Fluxo**:
  1. Log de início
  2. Criar execução filha (rastreamento)
  3. Obter agente do registry
  4. Preparar mensagens (system + contexto + tarefa)
  5. Criar sandbox e ferramentas
  6. Obter modelo LLM
  7. Invocar com tool binding (se ferramentas disponíveis)
  8. Extrair achados, arquivos, símbolos
  9. Retornar resultado estruturado
  10. Log de conclusão

#### Métodos Auxiliares

```python
def _format_task_for_agent(self, task: DelegationTask) -> str
```
- **Descrição**: Formata tarefa em prompt legível para agente
- **Entrada**: `DelegationTask`
- **Saída**: String com objetivo, escopo, exclusões, saída esperada, prioridade, iterações

```python
def _create_sandbox_for_agent(self, agent, task=None) -> MindFlowSandbox
```
- **Descrição**: Cria sandbox apropriado para agente
- **Entrada**: Agente, tarefa (opcional)
- **Saída**: `MindFlowSandbox` com root_dir e read_only flag
- **Prioridade**: `task.root_dir` > `settings.working_path` > None

```python
def _extract_key_findings(self, response: str, expected_output: str) -> str
```
- **Descrição**: Extrai achados-chave de resposta do agente
- **Entrada**: Resposta, formato esperado
- **Saída**: String comprimida (max 500 chars) ou resposta completa se curta
- **TODO**: Implementar extração mais inteligente baseada em `expected_output`

```python
def _extract_files_mentioned(self, response: str) -> list[str]
```
- **Descrição**: Extrai caminhos de arquivo mencionados na resposta
- **Entrada**: Resposta do agente
- **Saída**: Lista de caminhos únicos (regex: `\b[\w\-_\/\.]+\.(py|js|ts|json|yaml|yml|md|txt|sql)\b`)

```python
def _extract_symbols_mentioned(self, response: str) -> list[str]
```
- **Descrição**: Extrai nomes de funções/classes mencionados
- **Entrada**: Resposta do agente
- **Saída**: Lista de símbolos únicos (regex: `\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(`)

#### Integração com ExecutionMemoryService

- Cria execução filha com `start_execution()`
- Registra eventos com `append_event()`
- Marca status com `mark_status()`
- Registra mensagens com `record_message()`
- Consome mensagens pendentes com `consume_pending_messages()` (feedback do orquestrador)

#### Integração com Tool Invocation

- Converte ferramentas para LangChain com `to_langchain_tools()`
- Invoca com loop de tool calling via `invoke_with_tools()`
- Suporta até `max_iterations * 5` iterações de tool calling
- Despacha eventos customizados durante execução

---

### 3. ExecutionMemoryService (`execution_memory/service.py`)

**Propósito**: Persistência durável de estado de execução para pausa/retomada e auditoria.

**Classe Principal**: `ExecutionMemoryService`

#### Métodos de Execução

```python
async def start_execution(
    db: Any | None = None,
    *,
    session_id: str,
    agent_id: str | None = None,
    goal: str | None = None,
    execution_id: str | None = None,
    root_execution_id: str | None = None,
    parent_execution_id: str | None = None,
    execution_role: str | None = None,
    status: str = "running",
    stage: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentExecution
```
- **Descrição**: Inicia nova execução de agente
- **Entrada**: IDs de sessão/execução, objetivo, metadados
- **Saída**: `AgentExecution` com ID gerado, timestamps, status
- **Nota**: Gera `execution_id` se não fornecido; usa `execution_id` como `root_execution_id` se não fornecido

```python
async def mark_status(
    execution_id: str,
    status: str,
    db: Any | None = None,
    **updates: Any,
) -> AgentExecution
```
- **Descrição**: Atualiza status e metadados de execução
- **Entrada**: ID de execução, novo status, atualizações adicionais
- **Saída**: `AgentExecution` atualizado
- **Statuses Suportados**: running, completed, failed, paused, pause_requested, resuming
- **Atualizações Especiais**:
  - `stage`: Atualiza `current_stage`
  - `error`: Atualiza `error_message`
  - `metadata`: Mescla com metadados existentes

#### Métodos de Eventos

```python
async def append_event(
    execution_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    db: Any | None = None,
    message: str | None = None,
    stage: str | None = None,
) -> AgentExecutionEvent
```
- **Descrição**: Registra evento de execução
- **Entrada**: ID de execução, tipo de evento, payload, mensagem, stage
- **Saída**: `AgentExecutionEvent` com sequência, timestamp
- **Nota**: Payload é enriquecido automaticamente com execution_id, root_execution_id, parent_execution_id, agent, status, stage, progress

#### Métodos de Snapshots

```python
async def create_snapshot(
    db: Any | None = None,
    *,
    execution_id: str,
    snapshot_kind: str = "checkpoint",
    stage: str | None = None,
    state: dict[str, Any] | None = None,
    context: str | dict[str, Any] | None = None,
    is_resume_point: bool | None = None,
    checkpoint_id: str | None = None,
    next_nodes: list[str] | None = None,
) -> AgentExecutionSnapshot
```
- **Descrição**: Cria snapshot de estado para pausa/retomada
- **Entrada**: ID de execução, tipo, stage, estado, contexto, próximos nós
- **Saída**: `AgentExecutionSnapshot` com hash de estado, sequência
- **Nota**: Calcula `state_hash` para detecção de duplicatas

```python
async def get_latest_snapshot(
    execution_id: str,
    db: Any | None = None,
) -> AgentExecutionSnapshot | None
```
- **Descrição**: Obtém snapshot mais recente de uma execução
- **Entrada**: ID de execução
- **Saída**: `AgentExecutionSnapshot` ou None

#### Métodos de Mensagens

```python
async def record_message(
    db: Any | None = None,
    *,
    execution_id: str,
    message_type: str,
    sender_execution_id: str | None = None,
    recipient_execution_id: str | None = None,
    content: str = "",
    visibility: str = "internal",
    payload: dict[str, Any] | None = None,
    status: str = "pending",
) -> AgentExecutionMessage
```
- **Descrição**: Registra mensagem entre execuções (feedback, contexto)
- **Entrada**: IDs, tipo, conteúdo, visibilidade, payload, status
- **Saída**: `AgentExecutionMessage` com sequência
- **Visibilidades**: internal, external, user_visible
- **Statuses**: pending, consumed

```python
async def consume_pending_messages(
    db: Any | None = None,
    *,
    execution_id: str,
) -> list[SimpleNamespace]
```
- **Descrição**: Consome mensagens pendentes para uma execução
- **Entrada**: ID de execução
- **Saída**: Lista de mensagens, marca como consumed
- **Uso**: Agente checa mensagens pendentes antes de cada iteração

#### Métodos de Processos

```python
async def record_process(
    db: Any | None = None,
    *,
    execution_id: str,
    process_key: str,
    tab_id: str | None = None,
    pid: int | None = None,
    owner_agent_id: str | None = None,
    terminal_key: str | None = None,
    cwd: str | None = None,
    state: str = "running",
    metadata: dict[str, Any] | None = None,
) -> AgentExecutionProcess
```
- **Descrição**: Registra processo (terminal, shell) associado a execução
- **Entrada**: ID de execução, chave de processo, PID, terminal, CWD, estado
- **Saída**: `AgentExecutionProcess`
- **Nota**: Idempotente por `process_key`; atualiza se já existe

#### Métodos de Árvore de Execução

```python
async def get_execution_tree(
    execution_id: str,
    db: Any | None = None,
) -> dict[str, Any]
```
- **Descrição**: Obtém árvore completa de execuções (raiz + filhas)
- **Entrada**: ID de execução (raiz ou filha)
- **Saída**: Dicionário aninhado com execuções, mensagens, processos, filhas
- **Estrutura**:
  ```python
  {
    "execution": {...},
    "messages": [...],
    "processes": [...],
    "children": [
      {"execution": {...}, "messages": [...], "processes": [...], "children": [...]},
      ...
    ]
  }
  ```

#### Padrão de Transação

```python
async def _run_db(
    self,
    db: Any | None,
    operation: Callable[..., Awaitable[_T]],
    **kwargs: Any,
) -> _T
```
- **Descrição**: Padrão para executar operação com ou sem sessão fornecida
- **Entrada**: Sessão (opcional), operação, kwargs
- **Saída**: Resultado da operação
- **Lógica**:
  - Se `db` fornecido: usa diretamente
  - Se `db` None: obtém nova sessão via `get_db_session()`, executa, fecha

---

### 4. AgentRuntimePolicy (`agents/specialists/runtime_policy.py`)

**Propósito**: Contrato imutável de identidade e capacidades de agente.

**Classe Principal**: `AgentRuntimePolicy`

```python
@dataclass(frozen=True, slots=True)
class AgentRuntimePolicy:
    agent_role: AgentType  # ANALYST, CODER, RESEARCHER, ORCHESTRATOR
    system_prompt: str  # Prompt de sistema do agente
    specialist: SpecialistType | None = None  # Especialista opcional
    tools: tuple[ToolScope, ...] = ()  # Ferramentas disponíveis
    sandbox: SandboxMode = SandboxMode.NONE  # Modo de sandbox
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM  # Nível de reflexão
    keep_context: bool = True  # Manter contexto entre iterações?
    max_iterations: int = 1  # Máximo de iterações de tool calling
    summary: str = ""  # Resumo de capacidades
    use_when: str = ""  # Quando usar este agente
```

#### Propriedade

```python
@property
def agent_id(self) -> str
```
- **Descrição**: Retorna ID único do agente
- **Formato**: `"role"` se sem especialista, `"role:specialist"` se com especialista
- **Exemplo**: `"analyst"`, `"analyst:security_guard"`, `"coder:arch_tech"`

#### Método

```python
def build_agent(self) -> BaseAgent
```
- **Descrição**: Cria agente concreto a partir da política
- **Saída**: `BaseAgent` com todos os parâmetros da política

#### Políticas Registradas

| Agent ID | Role | Specialist | Tools | Sandbox | Max Iterations | Uso |
|----------|------|-----------|-------|---------|---|---|
| `orchestrator` | ORCHESTRATOR | None | MEMORY, PLANNING, DELEGATION | NONE | 50 | Entrada única, delegação |
| `analyst` | ANALYST | None | CODE_ANALYSIS, FILESYSTEM, SHELL | READ_ONLY | 10 | Investigação de código |
| `analyst:security_guard` | ANALYST | SECURITY_GUARD | CODE_ANALYSIS, FILESYSTEM, SHELL | READ_ONLY | 1 | Auditorias de segurança |
| `analyst:critic` | ANALYST | CRITIC | CODE_ANALYSIS, FILESYSTEM, SHELL | READ_ONLY | 1 | Revisão de código |
| `analyst:brainstorm` | ANALYST | BRAINSTORM | CODE_ANALYSIS, FILESYSTEM | READ_ONLY | 2 | Geração de ideias |
| `analyst:deep_iteration` | ANALYST | DEEP_ITERATION | CODE_ANALYSIS, FILESYSTEM, SHELL | READ_ONLY | 3 | Análise exaustiva |
| `analyst:planner` | ANALYST | DEEP_ITERATION | CODE_ANALYSIS, FILESYSTEM, PLANNING | READ_ONLY | 3 | Planejamento estruturado |
| `coder` | CODER | None | FILESYSTEM, SHELL | FULL | 10 | Implementação de código |
| `coder:arch_tech` | CODER | ARCH_TECH | CODE_ANALYSIS, FILESYSTEM, SHELL | FULL | 10 | Design arquitetural |
| `researcher` | RESEARCHER | None | WEB_SEARCH, PINCHTAB_FLEET, PINCHTAB_BROWSER | READ_ONLY | 5 | Pesquisa externa |

#### Função de Acesso

```python
def get_agent_runtime_policy(
    agent_role: AgentType | str | None = None,
    *,
    specialist: SpecialistType | str | None = None,
    agent_id: str | None = None,
) -> AgentRuntimePolicy
```
- **Descrição**: Obtém política de runtime para identidade de agente
- **Entrada**: Role + specialist OU agent_id
- **Saída**: `AgentRuntimePolicy`
- **Exceção**: `KeyError` se identidade desconhecida

```python
def list_agent_runtime_policies() -> list[AgentRuntimePolicy]
```
- **Descrição**: Lista todas as políticas registradas
- **Saída**: Lista de `AgentRuntimePolicy`

---

## Data Structures

### OrchestratorSession

```python
@dataclass
class OrchestratorSession:
    """Sessão de orquestração com contexto de conversa."""
    user_intent: str
    session_checkpoints: list[str] = field(default_factory=list)
    # Checkpoints são resumos de contexto de iterações anteriores
```

### DelegationTask

```python
@dataclass
class DelegationTask:
    """Tarefa a ser delegada para um agente."""
    task_id: UUID
    agent: AgentType
    agent_role: AgentType | None = None
    specialist: SpecialistType | None = None
    agent_id: str | None = None
    objective: str
    scope: list[str] | None = None  # Arquivos/áreas a focar
    exclusions: list[str] | None = None  # Arquivos/áreas a evitar
    context_from_session: str | None = None  # Contexto do orquestrador
    expected_output: str | None = None  # Formato esperado
    priority: Priority = Priority.NORMAL
    max_iterations: int = 1
    root_dir: str | None = None  # Diretório raiz para sandbox
```

### DelegationResult

```python
@dataclass
class DelegationResult:
    """Resultado de uma delegação."""
    task_id: UUID
    agent: AgentType
    agent_role: AgentType | None = None
    specialist: SpecialistType | None = None
    agent_id: str | None = None
    status: str  # "completed", "failed"
    key_findings: str  # Resumo dos achados
    full_output: str  # Resposta completa do agente
    files_analyzed: list[str] = field(default_factory=list)
    symbols_found: list[str] = field(default_factory=list)
    confidence: float = 0.0
    tokens_consumed: int = 0
    error_message: str | None = None
```

### WorkflowRouteDecision

```python
@dataclass
class WorkflowRouteDecision:
    """Decisão de roteamento de workflow."""
    rationale: str  # Por que esta decisão?
    agent_role: AgentType
    specialist: SpecialistType | None = None
    task: str  # Tarefa formulada
    thinking: ThinkingLevel
    priority: Priority
    execution_strategy: ExecutionStrategy
    tools: list[ToolScope]
    confidence: float
```

### OrchestratorDecision

```python
@dataclass
class OrchestratorDecision:
    """Decisão final de execução do orquestrador."""
    # Contém plano de execução completo
    # (estrutura exata depende de ExecutionStrategy)
```

---

## Fluxos de Execução

### Fluxo 1: Direct Response

```
User Message
    ↓
IntelligentRouter.analyze_intent_with_llm()
    ↓
IntentAnalysis(strategy=DIRECT_RESPONSE)
    ↓
Orchestrator responde diretamente
    ↓
Response to User
```

### Fluxo 2: Single Agent Delegation

```
User Message
    ↓
IntelligentRouter.analyze_intent_with_llm()
    ↓
IntentAnalysis(strategy=SINGLE_AGENT, agent=ANALYST)
    ↓
DelegationEngine.delegate_task()
    ├─ Create child execution
    ├─ Prepare messages
    ├─ Create sandbox
    ├─ Get tools
    ├─ Invoke LLM with tools
    ├─ Extract findings
    └─ Return DelegationResult
    ↓
Orchestrator synthesizes result
    ↓
Response to User
```

### Fluxo 3: Chain Execution

```
User Message
    ↓
IntelligentRouter.analyze_intent_with_llm()
    ↓
IntentAnalysis(strategy=CHAIN, agent_sequence=[ANALYST, CODER])
    ↓
Planner resolves concrete chain
    ├─ Step 1: DelegationEngine.delegate_task(ANALYST)
    ├─ Step 2: DelegationEngine.delegate_task(CODER, context=result_1)
    └─ ...
    ↓
Orchestrator synthesizes all results
    ↓
Response to User
```

---

## Padrões de Integração

### Padrão 1: Feedback em Tempo Real

```python
# Agente está iterando
for iteration in range(max_iterations):
    # Antes de cada iteração, consome mensagens pendentes
    pending_messages = await execution_memory.consume_pending_messages(execution_id)
    
    # Agente processa feedback
    for message in pending_messages:
        messages.append({
            "role": "system",
            "content": f"Feedback: {message.content}"
        })
    
    # Agente continua com novo contexto
    response = await llm.ainvoke(messages)
```

### Padrão 2: Rastreamento de Execução

```python
# Iniciar execução
execution = await execution_memory.start_execution(
    session_id=session_id,
    agent_id=agent_id,
    goal=objective,
    root_execution_id=root_execution_id,
    parent_execution_id=parent_execution_id,
)

# Registrar eventos
await execution_memory.append_event(
    execution.id,
    "tool_called",
    {"tool": "read_file", "path": "/path/to/file"},
    stage="working",
)

# Criar checkpoint
checkpoint = await execution_memory.create_snapshot(
    execution.id,
    snapshot_kind="checkpoint",
    state={"current_analysis": "..."},
    is_resume_point=True,
)

# Marcar conclusão
await execution_memory.mark_status(
    execution.id,
    "completed",
    stage="finalizing",
)
```

### Padrão 3: Extração de Achados

```python
# DelegationEngine extrai achados de resposta
key_findings = engine._extract_key_findings(
    response_text,
    expected_output="Lista de vulnerabilidades",
)

files_analyzed = engine._extract_files_mentioned(response_text)
symbols_found = engine._extract_symbols_mentioned(response_text)

# Retorna resultado estruturado
result = DelegationResult(
    task_id=task.task_id,
    agent=task.agent,
    status="completed",
    key_findings=key_findings,
    full_output=response_text,
    files_analyzed=files_analyzed,
    symbols_found=symbols_found,
    confidence=0.8,
    tokens_consumed=tokens_consumed,
)
```

---

## Considerações de Performance

### Context Window Management
- Orquestrador mantém contexto comprimido
- Cada agente recebe apenas contexto relevante
- Snapshots permitem retomada sem reprocessamento

### Tool Invocation Loop
- Máximo de iterações por política (1-50)
- Cada iteração: LLM → tool call → tool result → próxima iteração
- Eventos registrados para auditoria

### Database Transactions
- Padrão `_run_db()` garante transações ACID
- Snapshots com hash para detecção de duplicatas
- Índices em `execution_id`, `root_execution_id`, `session_id`

---

## Extensibilidade

### Adicionar Novo Especialista

1. Criar `SpecialistType` enum em `schemas/orchestration/specialists.py`
2. Criar prompt em `agents/prompts/specialized/`
3. Registrar política em `agents/specialists/runtime_policy.py`:
   ```python
   "analyst:my_specialist": AgentRuntimePolicy(
       agent_role=AgentType.ANALYST,
       specialist=SpecialistType.MY_SPECIALIST,
       system_prompt=MY_SPECIALIST_PROMPT,
       tools=(...),
       sandbox=SandboxMode.READ_ONLY,
       thinking_level=ThinkingLevel.HIGH,
       max_iterations=5,
       summary="...",
       use_when="...",
   )
   ```
4. Adicionar ao roster dinâmico em `IntelligentRouter._build_available_agents_section()`

### Adicionar Nova Estratégia de Execução

1. Adicionar `ExecutionStrategy` enum
2. Implementar lógica em `IntelligentRouter.analyze_intent_with_llm()`
3. Implementar resolução em planner layer
4. Adicionar exemplos ao prompt de análise

### Adicionar Novo Tipo de Ferramenta

1. Criar classe em `agents/tools/`
2. Registrar em `agents/tools/base/registry.py`
3. Adicionar ao `ToolScope` enum
4. Atualizar políticas de agente que devem ter acesso

---

## Troubleshooting

### Problema: Agente não recebe feedback

**Causa**: Mensagens não estão sendo registradas ou consumidas

**Solução**:
1. Verificar se `record_message()` está sendo chamado
2. Verificar se `consume_pending_messages()` está sendo chamado antes de cada iteração
3. Verificar status das mensagens em `AgentExecutionMessage.status`

### Problema: Execução não é rastreada

**Causa**: `execution_id` não está sendo passado para `DelegationEngine`

**Solução**:
1. Verificar se `session_id` e `root_execution_id` estão sendo passados
2. Verificar se `ExecutionMemoryService` está inicializado
3. Verificar logs para erros de persistência

### Problema: Agente escolhido incorretamente

**Causa**: Análise de intenção falhou ou prompt não é claro

**Solução**:
1. Verificar `IntentAnalysis.confidence` — se < 0.5, considerar fallback
2. Verificar se especialista registrado está no roster dinâmico
3. Adicionar exemplos ao prompt de análise para caso similar

---

## Referências

- **Schemas**: `python/mindflow_backend/schemas/orchestration/`
- **Models**: `python/mindflow_backend/storage/postgresql/models/`
- **Prompts**: `python/mindflow_backend/agents/prompts/`
- **Tests**: `python/mindflow_backend/tests/`
- **Examples**: `python/examples/`

