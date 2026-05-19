# Implementation Plan — Phase 2B: MissionLauncher

[Overview]
Criar o sistema MissionLauncher que seleciona, configura e executa execution graphs autônomos para agentes especializados, integrando-se ao CommunicationBus e ao DelegationEngine existentes.

A Phase 2B conecta os execution graphs da Phase 2A ao sistema de delegação, permitindo que missões autônomas sejam lançadas automaticamente quando um tipo de missão está disponível. O MissionLauncher valida que o agente pode executar o mission_type solicitado, cria um contexto de execução completo, executa o graph correto e retorna um resultado estruturado com anotações de memória e métricas.

Esta implementação depende de:

- Phase 1A: CommunicationBus (existente em `communication/bus/communication_bus.py`)
- Phase 1C: CommRole + MissionGraphType (existente em `schemas/orchestration/communication.py`)
- Phase 2A: Execution Graphs (registrados no `GraphFactory`)

O DelegationEngine já tem `AgentCommunicationMixin` injetado e o `CommunicationBus` disponível — falta apenas integrar o MissionLauncher como fallback primário para missões com tipo definido.

[Types]
Não há alterações nos types existentes. Todos os types necessários já estão definidos em `schemas/orchestration/communication.py` (MissionGraphType, CommRole) e `graphs/base/types.py` (GraphType).

Os novos types criados são dataclasses internas aos módulos da Phase 2B:

**MissionContext** (`execution/missions/mission_context.py`):

- `agent_id: str` — ID do agente executor
- `mission_type: MissionGraphType` — Tipo da missão
- `task: str` — Descrição da tarefa
- `session_id: str` — ID da sessão pai
- `comm_bus: CommunicationBus | None` — Bus de comunicação (opcional)
- `memory_scope: str = "universal"` — Escopo de memória
- `parent_mission_id: str | None = None` — ID da missão pai (sub-missões)
- `mission_id: str = uuid4()` — Identificador único
- `max_duration_seconds: float = 300.0` — Timeout
- `max_iterations: int = 500` — Limite de iterações
- `metadata: dict[str, Any]` — Metadados extras
- `to_graph_state()` — Converte para dict compatível com GraphState

**MemoryAnnotationRef** (`execution/missions/mission_result.py`):

- `content: str` — Conteúdo da anotação
- `importance: float = 0.5` — Importância (0-1)
- `iteration: int = 0` — Iteração em que foi criada
- `timestamp: datetime` — Timestamp
- `tags: list[str]` — Tags associadas

**MissionResult** (`execution/missions/mission_result.py`):

- `agent_id: str` — Agente executor
- `mission_type: MissionGraphType` — Tipo da missão
- `mission_id: str = uuid4()` — ID único
- `success: bool = False` — Se completou com sucesso
- `result: str = ""` — Conteúdo textual principal
- `annotations: list[MemoryAnnotationRef]` — Anotações de memória
- `messages_sent: list[dict]` — Mensagens P2P enviadas
- `duration_seconds: float = 0.0` — Duração
- `iterations: int = 0` — Iterações executadas
- `error: str | None = None` — Erro, se houver
- `started_at: datetime` — Início
- `completed_at: datetime | None = None` — Fim
- `metadata: dict[str, Any]` — Metadados extras
- `from_graph_state()` — Classmethod para criar a partir do estado final do graph
- `to_delegation_result_data()` — Converte para formato DelegationResult

**Mapeamento MissionGraphType → GraphType string** (interno ao MissionLauncher):

```python
_MISSION_TO_GRAPH_TYPE = {
    MissionGraphType.ANALYSIS: "analysis",
    MissionGraphType.DEEP_INVESTIGATION: "deep_investigation",
    MissionGraphType.SECURITY_AUDIT: "security_audit",
    MissionGraphType.CODE_REVIEW: "code_review",
    MissionGraphType.IDEATION: "analysis",              # reutiliza
    MissionGraphType.MULTI_PASS_ANALYSIS: "deep_investigation",
    MissionGraphType.VULNERABILITY_SCAN: "security_audit",
    MissionGraphType.EXPLORATION: "analysis",
    MissionGraphType.CODING_TASK: "coding_task",
    MissionGraphType.BUG_FIX: "bug_fix",
    MissionGraphType.REFACTOR: "refactor",
    MissionGraphType.IMPLEMENTATION: "coding_task",
    MissionGraphType.ARCHITECTURE_DESIGN: "coding_task",
    MissionGraphType.STRUCTURAL_REFACTOR: "refactor",
    MissionGraphType.WEB_RESEARCH: "web_research",
    MissionGraphType.DOCUMENTATION_LOOKUP: "web_research",
    MissionGraphType.COMPARISON_ANALYSIS: "comparison",
}
```

[Files]

**Novos arquivos a criar:**

1. `python/mindflow_backend/execution/__init__.py`
   - Exporta MissionLauncher, MissionContext, MissionResult, get_mission_launcher

2. `python/mindflow_backend/execution/missions/__init__.py`
   - Exporta MissionLauncher, get_mission_launcher, MissionContext, MissionResult, MemoryAnnotationRef

3. `python/mindflow_backend/execution/missions/mission_context.py`
   - Dataclass MissionContext com todos os campos descritos na seção Types
   - Método to_graph_state() para converter para formato compatível com GraphState

4. `python/mindflow_backend/execution/missions/mission_result.py`
   - Dataclass MemoryAnnotationRef
   - Dataclass MissionResult com classmethod from_graph_state e to_delegation_result_data

5. `python/mindflow_backend/execution/missions/mission_launcher.py`
   - Classe MissionLauncher com launch_mission() e can_agent_run()
   - Singleton get_mission_launcher()
   - Mapeamento _MISSION_TO_GRAPH_TYPE

**Arquivos a modificar:**

1. `python/mindflow_backend/orchestrator/delegation/engine.py`
   - Adicionar campo `_mission_launcher: Any | None = None`
   - Adicionar método `_get_mission_launcher()` (lazy init)
   - Modificar `delegate_task()` para verificar se task tem mission_type e usar MissionLauncher quando disponível
   - Fallback para comportamento existente quando não há mission_type

2. `python/mindflow_backend/graphs/factory.py`
   - NÃO MODIFICAR — O GraphFactory já tem `create_graph()` registrado para todos os graph types da Phase 2A. O MissionLauncher usa o factory existente, não precisa de alterações.

[Functions]

**Novas funções:**

1. `MissionLauncher.__init__(self, comm_bus: CommunicationBus | None = None)`
   - Arquivo: `python/mindflow_backend/execution/missions/mission_launcher.py`
   - Inicializa com referência ao GraphFactory e ao CommunicationBus

2. `MissionLauncher.launch_mission(self, agent_id, mission_type, task, session_id, context, max_duration_seconds, max_iterations) -> MissionResult`
   - Arquivo: `python/mindflow_backend/execution/missions/mission_launcher.py`
   - Valida agente → resolve GraphType → cria MissionContext → executa graph → retorna MissionResult
   - Usa asyncio.timeout para timeout de execução
   - Graceful degradation: retorna MissionResult com error em caso de falha

3. `MissionLauncher.can_agent_run(self, agent_id: str, mission_type: MissionGraphType) -> bool`
   - Arquivo: `python/mindflow_backend/execution/missions/mission_launcher.py`
   - Verifica se agente pode executar o mission_type via RuntimePolicy

4. `get_mission_launcher() -> MissionLauncher`
   - Arquivo: `python/mindflow_backend/execution/missions/mission_launcher.py`
   - Singleton global, lazy init do CommunicationBus

5. `MissionResult.from_graph_state(state, agent_id, mission_type, started_at) -> MissionResult`
   - Arquivo: `python/mindflow_backend/execution/missions/mission_result.py`
   - Classmethod para converter estado final do graph em MissionResult

6. `MissionResult.to_delegation_result_data() -> dict`
   - Arquivo: `python/mindflow_backend/execution/missions/mission_result.py`
   - Converte para formato compatível com DelegationResult

7. `MissionContext.to_graph_state() -> dict[str, Any]`
   - Arquivo: `python/mindflow_backend/execution/missions/mission_context.py`
   - Converte MissionContext para dict compatível com GraphState

**Funções a modificar:**

1. `DelegationEngine.__init__(self, *, execution_memory)`
   - Arquivo: `python/mindflow_backend/orchestrator/delegation/engine.py`
   - Adicionar: `self._mission_launcher: Any | None = None`

2. `DelegationEngine._get_mission_launcher() -> MissionLauncher | None`
   - Arquivo: `python/mindflow_backend/orchestrator/delegation/engine.py`
   - NOVA função lazy init para obter o MissionLauncher com graceful degradation

3. `DelegationEngine.delegate_task(self, task, session, *, session_id, root_execution_id, parent_execution_id) -> DelegationResult`
    - Arquivo: `python/mindflow_backend/orchestrator/delegation/engine.py`
    - Adicionar verificação no início: se task tem mission_type e launcher disponível, usar MissionLauncher
    - Fallback: comportamento existente de delegação (_legacy_delegate)

**Funções a remover:** Nenhuma.

[Classes]

**Novas classes:**

1. `MissionLauncher` — `python/mindflow_backend/execution/missions/mission_launcher.py`
   - Responsável por lançar missões autônomas
   - Dependências: GraphFactory (via get_graph_factory), CommunicationBus (opcional)
   - Métodos: **init**, launch_mission, can_agent_run

2. `MissionContext` (dataclass) — `python/mindflow_backend/execution/missions/mission_context.py`
   - Estado e dependências injetados em cada missão autônoma
   - Sem herança — dataclass pura
   - Método to_graph_state para compatibilidade com graphs

3. `MissionResult` (dataclass) — `python/mindflow_backend/execution/missions/mission_result.py`
   - Resultado de uma missão autônoma
   - Classmethod from_graph_state para criar a partir do estado do graph
   - Método to_delegation_result_data para compatibilidade com DelegationResult

4. `MemoryAnnotationRef` (dataclass) — `python/mindflow_backend/execution/missions/mission_result.py`
   - Referência a anotação de memória criada durante a missão

**Classes a modificar:**

1. `DelegationEngine` — `python/mindflow_backend/orchestrator/delegation/engine.py`
   - Adicionar campo _mission_launcher
   - Adicionar método _get_mission_launcher
   - Modificar delegate_task para tentar MissionLauncher primeiro quando mission_type disponível

**Classes a remover:** Nenhuma.

[Dependencies]
Não há novas dependências externas (packages pip). Todas as dependências são módulos internos do projeto:

- `communication.bus.communication_bus` — CommunicationBus, get_communication_bus (já existe)
- `communication.protocols.p2p_protocol` — P2PMessage (TYPE_CHECKING only)
- `agents.specialists.runtime_policy` — get_agent_runtime_policy (já existe)
- `graphs.factory` — get_graph_factory (já existe)
- `graphs.base.types` — GraphType (já existe)
- `schemas.orchestration.communication` — MissionGraphType (já existe)
- `infra.logging` — get_logger (já existe)

[Testing]
Criar `python/mindflow_backend/tests/unit/execution/` com os seguintes arquivos:

1. `test_mission_context.py`
   - test_create_context_defaults — verificar que todos os campos têm defaults
   - test_to_graph_state — verificar que retorna dict com todos os campos esperados

2. `test_mission_result.py`
   - test_from_graph_state_success — criar a partir de estado de sucesso
   - test_from_graph_state_error — criar a partir de estado com erro
   - test_to_delegation_result_data — verificar conversão correta

3. `test_mission_launcher.py`
   - test_launch_analysis_mission — missão de analysis bem-sucedida (mock do graph factory)
   - test_launch_fails_if_agent_cannot_run_type — fallback quando agente não tem mission_type
   - test_launch_returns_error_on_timeout — timeout retorna MissionResult com error
   - test_launch_removes_graph_after_completion — factory.remove_graph chamado em finally
   - test_can_agent_run — verificação de can_agent_run

4. `test_delegation_integration.py`
   - test_delegation_engine_uses_launcher_when_mission_type_set — DelegationEngine usa MissionLauncher
   - test_delegation_engine_fallback_when_no_launcher — Fallback quando launcher não disponível
   - test_delegation_engine_fallback_when_no_mission_type — Fallback quando task não tem mission_type

[Implementation Order]
A implementação deve seguir esta sequência para minimizar conflitos e permitir testes incrementais:

1. Criar estrutura de diretórios: `execution/__init__.py` e `execution/missions/__init__.py`
2. Criar `execution/missions/mission_context.py` (dataclass pura, sem dependências externas complexas)
3. Criar `execution/missions/mission_result.py` (dataclass pura, depende apenas de mission_context)
4. Criar `execution/missions/mission_launcher.py` (depende de mission_context, mission_result, graph factory, runtime policy)
5. Criar testes unitários para os 3 módulos acima
6. Modificar `orchestrator/delegation/engine.py` para integrar MissionLauncher
7. Criar teste de integração DelegationEngine + MissionLauncher
8. Executar testes completos e verificar que fallback funciona corretamente
