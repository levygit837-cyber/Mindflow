# 👥 Fase 3A — Team Protocol: Sessões Colaborativas e MissionDAG

**Fase:** 3A | **Semana:** 5–6 | **Prioridade:** P1  
**PRD Base:** `docs/PRD/PRD-Team-Protocol-Collaborative-Missions.md`  
**Depende de:** `1A` (CommunicationBus), `1B` (AgentCommunicationMixin), `2B` (MissionLauncher)  
**Bloqueia:** `3B` (MemoryObserver usa TeamSession)  
**Paralelo a:** Nada nesta fase — requer todas as fundações anteriores

---

## 📋 Sumário

Ativar o Team Mode completo: o Orchestrator cria um time de agentes especialistas que discutem em MUC (Multi-User Chat) antes de cada missão complexa. A discussion produz um `MissionDAG` — mapa de dependências declarado pelos próprios agentes. As missões são lançadas em paralelo seguindo o DAG. O resultado final é sintetizado pelo Orchestrator.

O módulo `communication/teams/` já tem `Team`, `TeamChat`, `TeamManager` — esta fase os **ativa e conecta** ao fluxo de execução.

---

## 🏗️ Arquitetura

```
IntelligentRouter
    │ complexity_score >= 0.7 AND 2+ agentes
    │ → execution_strategy = "team_session"
    ↓
TeamOrchestrator.run_full_team_session()
    │
    ├─ PHASE 1: Formation
    │   TeamManager.create_team(name, agents)
    │   → MUC room criada (TeamChat)
    │   → Orchestrator entra como LEADER
    │
    ├─ PHASE 2: Discussion (max 3 rounds)
    │   Orchestrator → TeamChat: "Task: [X]. Discuss."
    │   Analyst → TeamChat: "I'll investigate [Y]."
    │   Coder   → TeamChat: "I need Analyst output first."
    │   → MissionDAG extraído das declarações
    │
    ├─ PHASE 3: Autonomous Missions
    │   MissionDAG.get_ordered_missions()
    │   → Researcher e Analyst em paralelo (sem dependências)
    │   → Coder aguarda P2P signal de ambos
    │   → Cada agente anota memória durante missão
    │
    └─ PHASE 4: Synthesis
        Orchestrator lê todos os MissionResults
        + lê anotações da memória universal
        → Sintetiza resposta final ao usuário
```

---

## 🎯 O Que Criar

```
execution/
  teams/
    __init__.py                   ← CRIAR
    team_session.py               ← CRIAR: TeamSession, TeamPhase
    team_orchestrator.py          ← CRIAR: TeamOrchestrator
    mission_dag.py                ← CRIAR: MissionDAG, MissionNode, MissionEdge

orchestrator/routing/
  intelligent_router.py           ← MODIFICAR: adicionar team_session strategy

schemas/orchestration/
  orchestrator.py                 ← MODIFICAR: ExecutionStrategy.TEAM_SESSION
```

---

## 🔧 Implementação Passo a Passo

### Passo 1 — `execution/teams/mission_dag.py`

```python
# execution/teams/mission_dag.py
"""
MissionDAG — Grafo de dependências entre missões num team session.

Extraído das declarações dos agentes no pre-mission discussion.
Determina a ordem de execução respeitando dependências.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mindflow_backend.schemas.orchestration.communication import MissionGraphType


@dataclass
class MissionNode:
    """Nó no DAG — representa a missão de um agente específico."""
    agent_id: str
    mission_type: MissionGraphType
    task_description: str
    declared_dependencies: list[str] = field(default_factory=list)
    """agent_ids dos quais este nó depende"""
    signal_type: str = "p2p_ready_signal"
    """Como este agente sinaliza completude aos dependentes"""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MissionEdge:
    """Aresta no DAG — dependência direcional entre missões."""
    from_agent: str
    """Agente que produz o output (deve completar primeiro)"""
    to_agent: str
    """Agente que precisa do output (aguarda sinal)"""
    signal_type: str = "p2p_ready_signal"
    """Tipo de sinal: p2p_ready_signal | memory_annotation | completion"""


class MissionDAG:
    """
    Directed Acyclic Graph de missões para um team session.
    
    Construído a partir das declarações dos agentes no team chat.
    Garante que missões são executadas na ordem correta.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, MissionNode] = {}
        self._edges: list[MissionEdge] = []

    def add_mission(self, node: MissionNode) -> None:
        self._nodes[node.agent_id] = node
        for dep_agent_id in node.declared_dependencies:
            self._edges.append(MissionEdge(
                from_agent=dep_agent_id,
                to_agent=node.agent_id,
            ))

    def get_execution_waves(self) -> list[list[str]]:
        """
        Retorna missões agrupadas em waves de execução paralela.
        
        Wave 0: missões sem dependências (executam em paralelo imediatamente)
        Wave 1: missões que dependem de wave 0
        Wave N: missões que dependem de wave N-1
        """
        remaining = set(self._nodes.keys())
        completed: set[str] = set()
        waves: list[list[str]] = []
        
        # Detectar ciclos (proteção)
        max_iterations = len(self._nodes) + 1
        iteration = 0
        
        while remaining and iteration < max_iterations:
            wave = []
            for agent_id in remaining:
                node = self._nodes[agent_id]
                deps = set(node.declared_dependencies)
                if deps.issubset(completed):
                    wave.append(agent_id)
            
            if not wave:
                # Ciclo detectado — adicionar restantes em wave única
                wave = list(remaining)
            
            waves.append(wave)
            completed.update(wave)
            remaining.difference_update(wave)
            iteration += 1
        
        return waves

    def get_dependents_of(self, agent_id: str) -> list[str]:
        """Retorna agentes que dependem do agente dado."""
        return [e.to_agent for e in self._edges if e.from_agent == agent_id]

    def is_valid(self) -> tuple[bool, str]:
        """Valida o DAG (sem ciclos, agents existem)."""
        agents = set(self._nodes.keys())
        for edge in self._edges:
            if edge.from_agent not in agents:
                return False, f"Unknown from_agent: {edge.from_agent}"
            if edge.to_agent not in agents:
                return False, f"Unknown to_agent: {edge.to_agent}"
        return True, ""

    @classmethod
    def from_discussion(
        cls,
        chat_messages: list[Any],
        agent_ids: list[str],
    ) -> "MissionDAG":
        """
        Extrai MissionDAG a partir das mensagens do team chat.
        
        Analisa frases como:
        - "I need [agent] output first" → dependency
        - "I'll start after [agent] completes" → dependency
        - "I can start immediately" → no dependency
        
        Fallback: se não conseguir extrair, retorna DAG sem dependências.
        """
        dag = cls()
        
        for agent_id in agent_ids:
            from mindflow_backend.agents.specialists.runtime_policy import (
                get_agent_runtime_policy,
            )
            try:
                policy = get_agent_runtime_policy(agent_id=agent_id)
                graphs = policy.available_mission_graphs
                mission_type = graphs[0] if graphs else None
            except (KeyError, IndexError):
                mission_type = None
            
            if mission_type is None:
                continue
            
            # Tentar extrair dependências das mensagens do chat deste agente
            deps = cls._extract_dependencies_from_chat(
                agent_id=agent_id,
                messages=chat_messages,
                all_agents=agent_ids,
            )
            
            dag.add_mission(MissionNode(
                agent_id=agent_id,
                mission_type=mission_type,
                task_description=f"Mission for {agent_id}",
                declared_dependencies=deps,
            ))
        
        return dag

    @staticmethod
    def _extract_dependencies_from_chat(
        agent_id: str,
        messages: list[Any],
        all_agents: list[str],
    ) -> list[str]:
        """Parse simples de dependências declaradas no chat."""
        deps = []
        dependency_keywords = [
            "need", "after", "wait", "primeiro", "antes", "depende", "depends"
        ]
        
        for msg in messages:
            if msg.sender_jid != agent_id:
                continue
            content_lower = msg.content.lower()
            if any(kw in content_lower for kw in dependency_keywords):
                for other_agent in all_agents:
                    if other_agent != agent_id and other_agent in content_lower:
                        deps.append(other_agent)
        
        return list(set(deps))
```

**Arquivo:** `python/mindflow_backend/execution/teams/mission_dag.py`

---

### Passo 2 — `execution/teams/team_session.py`

```python
# execution/teams/team_session.py
"""
TeamSession — Estado de uma sessão colaborativa completa entre agentes.

Passa pelas fases: Formation → Discussion → Missions → Synthesis → Completed
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mindflow_backend.communication.teams.team import Team
    from mindflow_backend.communication.teams.team_chat import TeamMessage
    from mindflow_backend.execution.missions.mission_result import MissionResult
    from .mission_dag import MissionDAG


class TeamPhase(str, Enum):
    FORMATION = "formation"
    DISCUSSION = "discussion"
    MISSIONS = "missions"
    SYNTHESIS = "synthesis"
    COMPLETED = "completed"


@dataclass
class TeamSessionResult:
    """Resultado final de uma team session completa."""
    session_id: str
    task: str
    final_result: str
    success: bool
    missions: dict[str, Any]  # agent_id → MissionResult serialized
    chat_history_length: int
    total_duration_seconds: float
    phases_completed: list[str]
    error: str | None = None


@dataclass
class TeamSession:
    """
    Sessão colaborativa entre múltiplos agentes.
    
    Gerenciada pelo TeamOrchestrator através de 4 fases.
    """
    task: str
    agent_ids: list[str]
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team: Any | None = None  # Team
    phase: TeamPhase = TeamPhase.FORMATION
    mission_dag: Any | None = None  # MissionDAG
    missions: dict[str, Any] = field(default_factory=dict)  # agent_id → MissionResult
    chat_history: list[Any] = field(default_factory=list)  # list[TeamMessage]
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def advance_phase(self, next_phase: TeamPhase) -> None:
        self.phase = next_phase
    
    def record_mission_result(self, agent_id: str, result: Any) -> None:
        self.missions[agent_id] = result
    
    def all_missions_complete(self) -> bool:
        return len(self.missions) == len(self.agent_ids)
    
    def get_duration(self) -> float:
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    def to_summary(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "phase": self.phase.value,
            "agents": self.agent_ids,
            "missions_complete": len(self.missions),
            "missions_total": len(self.agent_ids),
            "duration_seconds": self.get_duration(),
        }
```

**Arquivo:** `python/mindflow_backend/execution/teams/team_session.py`

---

### Passo 3 — `execution/teams/team_orchestrator.py`

```python
# execution/teams/team_orchestrator.py
"""
TeamOrchestrator — Coordena sessões colaborativas multi-agente.

Fases: Formation → Discussion → Missions → Synthesis
"""

from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.communication.teams.team import Team, TeamMember
from mindflow_backend.communication.teams.team_chat import TeamChat
from mindflow_backend.communication.teams.team_manager import TeamManager
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.communication import CommRole

from .mission_dag import MissionDAG
from .team_session import TeamPhase, TeamSession, TeamSessionResult

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus
    from mindflow_backend.execution.missions.mission_launcher import MissionLauncher

_logger = get_logger(__name__)

MAX_DISCUSSION_ROUNDS = 3
DISCUSSION_TIMEOUT_SECONDS = 60.0
MISSION_SIGNAL_TIMEOUT = 120.0


class TeamOrchestrator:
    """
    Coordena sessões colaborativas entre múltiplos agentes.
    
    O Orchestrator é sempre o LEADER.
    Especialistas discutem, declaram dependências, e lançam missões autônomas.
    """

    def __init__(
        self,
        team_manager: TeamManager,
        mission_launcher: "MissionLauncher",
        comm_bus: "CommunicationBus",
    ) -> None:
        self._team_manager = team_manager
        self._mission_launcher = mission_launcher
        self._comm_bus = comm_bus

    async def run_full_team_session(
        self,
        task: str,
        agent_ids: list[str],
        session_id: str,
    ) -> TeamSessionResult:
        """
        Executa uma team session completa pelas 4 fases.
        
        Returns TeamSessionResult com resultado sintetizado.
        """
        session = TeamSession(
            task=task,
            agent_ids=agent_ids,
            session_id=session_id,
        )
        
        try:
            # FASE 1: Formation
            await self._phase_formation(session)
            
            # FASE 2: Discussion
            await self._phase_discussion(session)
            
            # FASE 3: Missions
            await self._phase_missions(session)
            
            # FASE 4: Synthesis
            final_result = await self._phase_synthesis(session)
            
            return TeamSessionResult(
                session_id=session.session_id,
                task=task,
                final_result=final_result,
                success=True,
                missions={
                    agent_id: result.to_delegation_result_data()
                    for agent_id, result in session.missions.items()
                },
                chat_history_length=len(session.chat_history),
                total_duration_seconds=session.get_duration(),
                phases_completed=[p.value for p in TeamPhase if p != TeamPhase.COMPLETED],
            )
        
        except Exception as exc:
            _logger.error("team_session_failed", session_id=session_id, error=str(exc))
            return TeamSessionResult(
                session_id=session.session_id,
                task=task,
                final_result="",
                success=False,
                missions={},
                chat_history_length=len(session.chat_history),
                total_duration_seconds=session.get_duration(),
                phases_completed=[session.phase.value],
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    async def _phase_formation(self, session: TeamSession) -> None:
        """Cria o time e a sala MUC."""
        session.advance_phase(TeamPhase.FORMATION)
        _logger.info("team_formation_start", session_id=session.session_id)
        
        team = await self._team_manager.create_team(
            name=f"session_{session.session_id[:8]}",
            description=f"Team for: {session.task[:50]}",
        )
        
        # Adicionar orchestrator como leader
        team.add_member("orchestrator", role="leader")
        
        # Adicionar especialistas
        for agent_id in session.agent_ids:
            team.add_member(agent_id, role="specialist")
        
        # Criar room no bus
        for agent_id in [*session.agent_ids, "orchestrator"]:
            self._comm_bus.join_room(agent_id, team.team_id)
        
        session.team = team
        _logger.info(
            "team_formed",
            session_id=session.session_id,
            team_id=team.team_id,
            agents=session.agent_ids,
        )

    async def _phase_discussion(self, session: TeamSession) -> None:
        """Facilita discussion e extrai MissionDAG."""
        session.advance_phase(TeamPhase.DISCUSSION)
        team_chat = TeamChat(session.team.team_id, session.team.team_id)
        
        # Round 0: Orchestrator apresenta a tarefa
        intro_msg = team_chat.create_message(
            sender_jid="orchestrator",
            content=(
                f"Task: {session.task}\n\n"
                f"Please declare: (1) what you will do, "
                f"(2) what you need from other agents first."
            ),
        )
        session.chat_history.append(intro_msg)
        await self._comm_bus.broadcast("orchestrator", session.team.team_id, intro_msg)
        
        # Rounds de discussion (max MAX_DISCUSSION_ROUNDS)
        for round_num in range(MAX_DISCUSSION_ROUNDS):
            round_messages = await self._collect_agent_declarations(
                session=session,
                round_num=round_num,
                team_chat=team_chat,
            )
            session.chat_history.extend(round_messages)
            
            if self._consensus_reached(session.chat_history, session.agent_ids):
                _logger.info(
                    "team_consensus_reached",
                    session_id=session.session_id,
                    rounds=round_num + 1,
                )
                break
        
        # Extrair MissionDAG das declarações
        session.mission_dag = MissionDAG.from_discussion(
            chat_messages=session.chat_history,
            agent_ids=session.agent_ids,
        )
        
        _logger.info(
            "team_discussion_complete",
            session_id=session.session_id,
            dag_waves=len(session.mission_dag.get_execution_waves()),
        )

    async def _phase_missions(self, session: TeamSession) -> None:
        """Executa missões em paralelo seguindo o MissionDAG."""
        session.advance_phase(TeamPhase.MISSIONS)
        
        waves = session.mission_dag.get_execution_waves()
        _logger.info(
            "team_missions_start",
            session_id=session.session_id,
            waves=len(waves),
        )
        
        for wave_idx, wave in enumerate(waves):
            _logger.info(
                "team_wave_start",
                wave=wave_idx,
                agents=wave,
            )
            
            # Executar todos os agentes desta wave em paralelo
            tasks = []
            for agent_id in wave:
                node = session.mission_dag._nodes.get(agent_id)
                if node:
                    tasks.append(
                        self._run_agent_mission(
                            session=session,
                            agent_id=agent_id,
                            mission_type=node.mission_type,
                        )
                    )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for agent_id, result in zip(wave, results):
                if isinstance(result, Exception):
                    _logger.error(
                        "team_mission_error",
                        agent_id=agent_id,
                        error=str(result),
                    )
                else:
                    session.record_mission_result(agent_id, result)
                    # Notificar dependentes que esta missão completou
                    dependents = session.mission_dag.get_dependents_of(agent_id)
                    for dep in dependents:
                        if self._comm_bus.is_available:
                            from mindflow_backend.communication.mixins.agent_communication import AgentCommunicationMixin
                            comm = AgentCommunicationMixin(agent_id=agent_id, bus=self._comm_bus)
                            await comm.notify(dep, "mission_complete", {"agent": agent_id})

    async def _phase_synthesis(self, session: TeamSession) -> str:
        """Orquestrador sintetiza todos os resultados em resposta final."""
        session.advance_phase(TeamPhase.SYNTHESIS)
        
        results_summary = "\n\n".join(
            f"=== {agent_id} ===\n{result.result}"
            for agent_id, result in session.missions.items()
            if result.success
        )
        
        _logger.info(
            "team_synthesis",
            session_id=session.session_id,
            missions_successful=sum(1 for r in session.missions.values() if r.success),
        )
        
        # O Orchestrator sintetiza via LLM (delegado ao sistema existente)
        # Por ora: concatenação estruturada
        synthesis = (
            f"Team Session Results for: {session.task}\n\n"
            f"{results_summary}"
        )
        
        session.advance_phase(TeamPhase.COMPLETED)
        return synthesis

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _run_agent_mission(
        self,
        session: TeamSession,
        agent_id: str,
        mission_type: Any,
    ) -> Any:
        """Lança missão de um agente específico."""
        return await self._mission_launcher.launch_mission(
            agent_id=agent_id,
            mission_type=mission_type,
            task=session.task,
            session_id=session.session_id,
        )

    async def _collect_agent_declarations(
        self,
        session: TeamSession,
        round_num: int,
        team_chat: Any,
    ) -> list[Any]:
        """Coleta declarações de todos os agentes no round."""
        msgs = []
        for agent_id in session.agent_ids:
            policy = get_agent_runtime_policy(agent_id=agent_id)
            declaration = (
                f"[Round {round_num + 1}] {agent_id}: "
                f"I will handle {[g.value for g in policy.available_mission_graphs[:2]]}. "
                f"Starting immediately."
            )
            msg = team_chat.create_message(sender_jid=agent_id, content=declaration)
            msgs.append(msg)
        return msgs

    @staticmethod
    def _consensus_reached(
        messages: list[Any],
        agent_ids: list[str],
    ) -> bool:
        """Verifica se todos os agentes fizeram pelo menos 1 declaração."""
        declaring_agents = {m.sender_jid for m in messages if m.sender_jid != "orchestrator"}
        return declaring_agents.issuperset(set(agent_ids))
```

**Arquivo:** `python/mindflow_backend/execution/teams/team_orchestrator.py`

---

### Passo 4 — Estender `IntelligentRouter`

**Arquivo:** `python/mindflow_backend/orchestrator/routing/intelligent_router.py`

Adicionar `team_session` ao prompt de routing:

```python
### 4. team_session — Múltiplos especialistas com interdependências:
| Quando usar |
|---|
| 2+ agentes distintos com interdependências explícitas |
| complexity_score estimado >= 0.7 |
| Decisões de design que afetam múltiplos domínios |

Exemplo: "redesign the auth system with security review and implementation"
→ team_session, agents: [analyst:security_guard, coder:arch_tech, researcher]
```

E no `route_message_strategy()`, adicionar handling para `TEAM_SESSION`:

```python
if intent.execution_strategy == ExecutionStrategy.TEAM_SESSION:
    agent_ids = [a.value for a in intent.agent_sequence] if intent.agent_sequence else []
    return WorkflowRouteDecision(
        rationale=f"Team session: {len(agent_ids)} agents will collaborate.",
        agent_role=AgentType.ORCHESTRATOR,
        task=message,
        execution_strategy=ExecutionStrategy.TEAM_SESSION,
        confidence=intent.confidence,
        metadata={"team_agent_ids": agent_ids},
    )
```

---

## ✅ Checklist de Conclusão

### Semana 5 (Dias 1–3)
- [ ] Criar `execution/teams/__init__.py`
- [ ] Criar `execution/teams/mission_dag.py`
  - [ ] `MissionNode`, `MissionEdge`, `MissionDAG`
  - [ ] `get_execution_waves()` funcional
  - [ ] `from_discussion()` extrai deps básicas
  - [ ] `is_valid()` detecta ciclos
- [ ] Criar `execution/teams/team_session.py`
  - [ ] `TeamPhase`, `TeamSession`, `TeamSessionResult`

### Semana 5–6 (Dias 4–10)
- [ ] Criar `execution/teams/team_orchestrator.py`
  - [ ] `run_full_team_session()` completo
  - [ ] `_phase_formation()`: cria Team + MUC room
  - [ ] `_phase_discussion()`: rounds + extrai DAG
  - [ ] `_phase_missions()`: waves paralelas via asyncio.gather
  - [ ] `_phase_synthesis()`: coleta e sintetiza resultados
- [ ] Ativar `TeamManager` do módulo `communication/teams/`
- [ ] Estender `IntelligentRouter` com `team_session` strategy
- [ ] Estender `ExecuteNode` para disparar `TeamOrchestrator` quando strategy == TEAM_SESSION

### Testes
- [ ] `test_mission_dag_waves()`
- [ ] `test_mission_dag_no_cycles()`
- [ ] `test_mission_dag_from_discussion()`
- [ ] `test_team_orchestrator_formation()`
- [ ] `test_team_orchestrator_discussion_max_rounds()`
- [ ] `test_team_orchestrator_parallel_missions()`
- [ ] `test_intelligent_router_team_session_strategy()`

---

## 📊 Métricas de Sucesso

| Métrica | Target |
|---|---|
| Team sessions com DAG correto (sem ciclos) | 100% |
| Missões paralelas executam em paralelo | ≥ 2x speedup vs. sequential |
| Discussion rounds ≤ 3 em 95% das sessões | ✅ por design |
| Consensus detectado corretamente | 100% quando todos declararam |

---

## ⚠️ Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| Discussion não gera DAG útil | Fallback: DAG sem dependências (todas as missões em paralelo) |
| Missão de wave N falha e bloqueia N+1 | `asyncio.gather(return_exceptions=True)` + missão falha gracefully |
| Orchestrator não consegue sintetizar resultados | Concatenação básica como fallback |
| Team session muito lenta (overhead) | Usar team_session APENAS para complexity >= 0.7 |
