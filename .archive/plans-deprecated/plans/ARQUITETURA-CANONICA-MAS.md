# Arquitetura Canônica do MAS (Multi-Agent System)

## Visão Geral

O sistema MAS do MindFlow deve seguir dois fluxos distintos:

### 1. Fluxo Normal (Standard Team Flow)
```
Team de Agentes → Comunicação → Discussão → Consenso → Agentes resolvem tarefas individualmente com tools
```

### 2. Fluxo Enterprise (MissionLauncher)
```
Team de Agentes → Comunicação → Discussão → Consenso → Orquestrador delega MISSÕES individuais
→ Missão (Acesso a Graphs específicos, possibilidade de utilizar Sub-Agentes)
→ Agente delegado se torna Leader do Time e comanda Sub-Agentes na execução de graphs
```

## Estado Atual do Código

### ✅ Já Implementado

1. **CommRole** (`schemas/orchestration/communication.py`)
   - LEADER: Orquestra, cria teams, autoriza missões, sintetiza resultados
   - SPECIALIST: Executa missões autônomas, reporta ao leader
   - OBSERVER: Monitora execuções alheias e anota memória

2. **TeamMember** (`communication/teams/team.py`)
   - Tem field `role` (string, padrão "member")
   - Pode adicionar/remover membros
   - Pode definir roles via `set_member_role()`

3. **TeamOrchestrator** (`execution/teams/team_orchestrator.py`)
   - Fases: Formation → Discussion → Missions → Synthesis
   - Usa MissionLauncher para lançar missões
   - Usa MissionDAG para dependências entre missões

4. **MissionLauncher** (`execution/missions/mission_launcher.py`)
   - Suporta sub-teams via `_launch_with_sub_team()`
   - Usa AgentTeamManager para criar sub-times
   - Mapeia MissionGraphType para GraphType

### ❌ Falta Implementar

1. **Hierarquia dinâmica de roles no time**
   - Atualmente TeamMember.role é apenas string genérica
   - Não há mecanismo de eleição de líder baseado em voluntariações
   - Não há sistema de "voluntariação" para tarefas específicas

2. **Separação clara entre fluxo normal e enterprise**
   - Atualmente TeamOrchestrator sempre usa MissionLauncher
   - Não há flag para escolher entre fluxo normal (tools) vs enterprise (graphs)

3. **Agente delegado como Leader de sub-time**
   - Quando um agente recebe uma missão, ele deve poder comandar sub-agentes
   - Atualmente sub-teams são criados pelo MissionLauncher, mas não pelo agente delegado

## Proposta de Implementação

### 1. Melhorar TeamMember com Hierarquia de Roles

```python
# communication/teams/team.py
from enum import Enum

class TeamRole(str, Enum):
    """Roles hierárquicos em um time de agentes."""
    ORCHESTRATOR = "orchestrator"  # Leader principal do time
    LEADER = "leader"              # Leader de sub-time ou missão
    SPECIALIST = "specialist"      # Agente especialista
    CONTRIBUTOR = "contributor"    # Agente contribuinte
    OBSERVER = "observer"          # Apenas observa

@dataclass
class TeamMember:
    """Team member com role hierárquico."""
    agent_jid: str
    role: TeamRole = TeamRole.SPECIALIST  # Padrão: especialista
    joined_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Voluntariações
    volunteered_missions: set[MissionGraphType] = field(default_factory=set)
    volunteered_tasks: set[str] = field(default_factory=set)
    
    # Se este membro é líder de sub-time
    is_sub_team_leader: bool = False
    sub_team_members: list[str] = field(default_factory=list)
```

### 2. Adicionar Sistema de Voluntariação

```python
# execution/teams/volunteer_system.py

class VolunteerSystem:
    """Sistema de voluntariação para tarefas e missões."""
    
    async def collect_volunteers(
        self,
        team: Team,
        task: str,
        available_missions: list[MissionGraphType],
    ) -> dict[str, VolunteerDeclaration]:
        """Coleta voluntariações dos membros do time."""
        declarations = {}
        
        for member in team.members:
            if not member.is_active:
                continue
                
            # Perguntar ao agente o que ele pode fazer
            declaration = await self._ask_agent_volunteer(
                agent_id=member.agent_jid,
                task=task,
                available_missions=available_missions,
            )
            declarations[member.agent_jid] = declaration
            
        return declarations
    
    async def elect_leader(
        self,
        volunteers: dict[str, VolunteerDeclaration],
        task: str,
    ) -> str:
        """Elege líder baseado em voluntariações e expertise."""
        # Critérios:
        # 1. Agente com mais voluntariações relevantes
        # 2. Agente com maior expertise na tarefa
        # 3. Agente com role mais alto (ORCHESTRATOR > LEADER > SPECIALIST)
        
        scores = {}
        for agent_id, decl in volunteers.items():
            score = self._calculate_volunteer_score(decl, task)
            scores[agent_id] = score
        
        # Retornar agente com maior score
        return max(scores.items(), key=lambda x: x[1])[0]
```

### 3. Modificar TeamOrchestrator para Suportar Ambos Fluxos

```python
# execution/teams/team_orchestrator.py

class TeamOrchestrator:
    """Coordena sessões colaborativas multi-agente."""
    
    def __init__(
        self,
        team_manager: TeamManager,
        mission_launcher: MissionLauncher,
        comm_bus: CommunicationBus,
        volunteer_system: VolunteerSystem,  # Novo
    ) -> None:
        self._team_manager = team_manager
        self._mission_launcher = mission_launcher
        self._comm_bus = comm_bus
        self._volunteer_system = volunteer_system  # Novo
    
    async def run_full_team_session(
        self,
        task: str,
        agent_ids: list[str],
        session_id: str,
        mode: TeamSessionMode = TeamSessionMode.NORMAL,  # Novo
        skip_discussion: bool = False,
    ) -> TeamSessionResult:
        """
        Executa uma team session completa.
        
        mode:
            - NORMAL: Fluxo padrão com tools
            - ENTERPRISE: Fluxo com MissionLauncher e graphs
        """
        session = TeamSession(
            task=task,
            agent_ids=agent_ids,
            session_id=session_id,
            mode=mode,  # Novo
        )
        
        # FASE 1: Formation
        await self._phase_formation(session)
        
        # FASE 2: Discussion
        if not skip_discussion:
            await self._phase_discussion_with_volunteers(session)  # Modificado
        else:
            logger.info("team_session_skip_discussion", ...)
        
        # FASE 3: Missions (ou Task Resolution)
        if session.mode == TeamSessionMode.ENTERPRISE:
            await self._phase_missions_with_graphs(session)  # Novo
        else:
            await self._phase_task_resolution_with_tools(session)  # Novo
        
        # FASE 4: Synthesis
        final_result = await self._phase_synthesis(session)
        
        return TeamSessionResult(...)
    
    async def _phase_discussion_with_volunteers(self, session: TeamSession) -> None:
        """Discussion com sistema de voluntariação."""
        # Coletar voluntariações
        volunteers = await self._volunteer_system.collect_volunteers(
            team=session.team,
            task=session.task,
            available_missions=session.available_missions,
        )
        
        # Eleger líder
        leader_id = await self._volunteer_system.elect_leader(
            volunteers=volunteers,
            task=session.task,
        )
        
        # Definir líder no time
        session.team.set_member_role(leader_id, TeamRole.LEADER)
        session.leader_id = leader_id
        
        # Construir MissionDAG baseado em voluntariações
        session.mission_dag = MissionDAG.from_volunteers(
            volunteers=volunteers,
            leader_id=leader_id,
            session_id=session.session_id,
        )
    
    async def _phase_task_resolution_with_tools(self, session: TeamSession) -> None:
        """Resolução de tarefas com tools (fluxo normal)."""
        # Cada agente resolve sua parte com tools
        # Sem MissionLauncher, sem graphs
        for agent_id in session.agent_ids:
            result = await self._execute_agent_with_tools(
                agent_id=agent_id,
                task=session.task,
                session_id=session.session_id,
            )
            session.record_task_result(agent_id, result)
    
    async def _phase_missions_with_graphs(self, session: TeamSession) -> None:
        """Missões com graphs e sub-times (fluxo enterprise)."""
        # Usar MissionLauncher para lançar missões
        # Agente delegado se torna leader de sub-time
        for wave in session.mission_dag.get_execution_waves():
            tasks = []
            for agent_id in wave:
                node = session.mission_dag.get_node(agent_id)
                if node and node.mission_type:
                    # Lançar missão
                    mission_result = await self._mission_launcher.launch_mission(
                        agent_id=agent_id,
                        mission_type=node.mission_type,
                        task=session.task,
                        session_id=session.session_id,
                        comm_bus=self._comm_bus,
                        metadata={
                            "is_team_leader": agent_id == session.leader_id,
                            "can_spawn_sub_team": True,  # Permitir sub-times
                        },
                    )
                    tasks.append(mission_result)
            
            results = await asyncio.gather(*tasks)
            # Registrar resultados...
```

### 4. Melhorar MissionLauncher para Suportar Agente como Leader

```python
# execution/missions/mission_launcher.py

class MissionLauncher:
    """Lança missões autônomas via Execution Graphs."""
    
    async def launch_mission(
        self,
        agent_id: str,
        mission_type: MissionGraphType,
        task: str,
        session_id: str,
        *,
        comm_bus: CommunicationBus | None = None,
        max_duration_seconds: float = 300.0,
        max_iterations: int = 500,
        metadata: dict[str, Any] | None = None,
    ) -> MissionResult:
        """Lança uma missão autônoma."""
        
        metadata = metadata or {}
        is_team_leader = metadata.get("is_team_leader", False)
        can_spawn_sub_team = metadata.get("can_spawn_sub_team", False)
        
        # Se agente é líder e pode criar sub-time
        if is_team_leader and can_spawn_sub_team:
            return await self._launch_with_sub_team_as_leader(
                agent_id=agent_id,
                mission_type=mission_type,
                task=task,
                session_id=session_id,
                comm_bus=comm_bus,
                metadata=metadata,
            )
        
        # Fluxo normal...
    
    async def _launch_with_sub_team_as_leader(
        self,
        agent_id: str,
        mission_type: MissionGraphType,
        task: str,
        session_id: str,
        comm_bus: CommunicationBus | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MissionResult:
        """
        Lança missão onde o agente delegado se torna leader de sub-time.
        
        O agente pode:
        1. Comandar sub-agentes na execução do graph
        2. Delegar subtarefas específicas
        3. Sintetizar resultados dos sub-agentes
        """
        # Criar sub-time com agente como líder
        team_manager = AgentTeamManager(comm_bus=comm_bus, mission_launcher=self)
        
        # Agente líder seleciona sub-agentes
        sub_team_agents = await self._let_agent_select_sub_agents(
            leader_agent_id=agent_id,
            mission_type=mission_type,
            task=task,
        )
        
        # Criar sub-time
        sub_team = await team_manager.create_team(
            leader_id=agent_id,
            member_ids=sub_team_agents,
            team_type="sub_team",
        )
        
        # Executar graph com sub-time
        graph_type = _MISSION_TO_GRAPH_TYPE.get(mission_type)
        graph = self._graph_factory.create_graph(graph_type=graph_type)
        
        # Executar com contexto de sub-time
        initial_state = {
            "task": task,
            "session_id": session_id,
            "team": sub_team.to_dict(),
            "leader_agent_id": agent_id,
            "sub_agents": sub_team_agents,
        }
        
        final_state = await graph.execute(initial_state)
        
        return MissionResult.from_graph_state(
            state=final_state,
            agent_id=agent_id,
            mission_type=mission_type,
            started_at=datetime.now(),
        )
```

### 5. Adicionar Enum para Modo de Sessão

```python
# execution/teams/team_session.py

class TeamSessionMode(str, Enum):
    """Modo de execução da sessão de time."""
    NORMAL = "normal"           # Fluxo padrão com tools
    ENTERPRISE = "enterprise"   # Fluxo com MissionLauncher e graphs

@dataclass
class TeamSession:
    """Sessão colaborativa multi-agente."""
    task: str
    agent_ids: list[str]
    session_id: str
    mode: TeamSessionMode = TeamSessionMode.NORMAL  # Novo
    leader_id: str | None = None  # Novo
    # ...
```

## Diagrama de Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────────┐
│                    TeamOrchestrator                               │
│  (execution/teams/team_orchestrator.py)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                ┌───────────┴───────────┐
                │  TeamSessionMode      │
                └───────────┬───────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
│  NORMAL Mode     │ │ ENTERPRISE   │ │ Sub-Team Mode   │
│                  │ │ Mode         │ │ (skip_discussion)│
│ - Tools         │ │ - Graphs      │ │ - Graphs        │
│ - Sem Mission   │ │ - Mission     │ │ - Mission       │
│ - Resolução     │ │ - Sub-Times   │ │ - Sub-Times     │
│                 │ │ - Leader      │ │ - Agente como    │
└──────────────────┘ │              │ │   Leader         │
                    └──────────────┘ └─────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  VolunteerSystem      │
                │  (Novo)                │
                │  - Coleta voluntarios │
                │  - Elege líder        │
                │  - Constrói DAG      │
                └───────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  MissionLauncher      │
                │  (Melhorado)          │
                │  - Suporta sub-times  │
                │  - Agente como leader │
                │  - Hierarquia dinâmica│
                └───────────────────────┘
```

## Passos de Implementação

### Fase 1: Fundação
1. Criar `TeamRole` enum em `communication/teams/team.py`
2. Adicionar campos de voluntariação em `TeamMember`
3. Criar `VolunteerSystem` em `execution/teams/volunteer_system.py`
4. Adicionar `TeamSessionMode` enum em `execution/teams/team_session.py`

### Fase 2: TeamOrchestrator
1. Modificar `TeamOrchestrator` para aceitar `VolunteerSystem`
2. Adicionar parâmetro `mode` em `run_full_team_session`
3. Implementar `_phase_discussion_with_volunteers`
4. Implementar `_phase_task_resolution_with_tools`
5. Implementar `_phase_missions_with_graphs`

### Fase 3: MissionLauncher
1. Melhorar `launch_mission` para suportar metadata de líder
2. Implementar `_launch_with_sub_team_as_leader`
3. Implementar `_let_agent_select_sub_agents`

### Fase 4: Graphs
1. Atualizar graphs para suportar contexto de sub-time
2. Adicionar nodes para delegação de sub-agentes
3. Adicionar nodes para síntese de resultados de sub-agentes

### Fase 5: Testes
1. Testar fluxo NORMAL com tools
2. Testar fluxo ENTERPRISE com graphs
3. Testar sub-times com agente como líder
4. Testar sistema de voluntariação e eleição de líder

## Benefícios

1. **Separação clara** entre fluxo normal e enterprise
2. **Hierarquia dinâmica** baseada em voluntariações
3. **Flexibilidade** para diferentes tipos de tarefas
4. **Escalabilidade** via sub-times e sub-agentes
5. **Manutenibilidade** com código bem organizado
