"""
MissionDAG — Grafo de dependências entre missões num team session.

Extraído das declarações dos agentes no pre-mission discussion.
Determina a ordem de execução respeitando dependências.

Fase 3A — SPADE Team Protocol
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mindflow_backend.schemas.orchestration.communication import MissionGraphType


@dataclass
class MissionNode:
    """Nó no DAG — representa a missão de um agente específico."""
    agent_id: str
    mission_type: MissionGraphType | None
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

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_mission(self, node: MissionNode) -> None:
        """Adiciona um nó e gera edges automáticos para cada dependência."""
        self._nodes[node.agent_id] = node
        for dep_agent_id in node.declared_dependencies:
            self._edges.append(MissionEdge(
                from_agent=dep_agent_id,
                to_agent=node.agent_id,
                signal_type=node.signal_type,
            ))

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

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
                # Ciclo detectado — adicionar restantes em wave única como fallback
                wave = list(remaining)

            waves.append(sorted(wave))  # sort para determinismo
            completed.update(wave)
            remaining.difference_update(wave)
            iteration += 1

        return waves

    def get_dependents_of(self, agent_id: str) -> list[str]:
        """Retorna agentes que dependem do agente dado."""
        return sorted({e.to_agent for e in self._edges if e.from_agent == agent_id})

    def get_node(self, agent_id: str) -> MissionNode | None:
        """Retorna o nó de um agente específico."""
        return self._nodes.get(agent_id)

    @property
    def nodes(self) -> dict[str, MissionNode]:
        return self._nodes

    @property
    def edges(self) -> list[MissionEdge]:
        return list(self._edges)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid(self) -> tuple[bool, str]:
        """Valida o DAG (sem ciclos, agents existem)."""
        agents = set(self._nodes.keys())

        # Checar que todos os agentes nas edges existem
        for edge in self._edges:
            if edge.from_agent not in agents:
                return False, f"Unknown from_agent in edge: {edge.from_agent}"
            if edge.to_agent not in agents:
                return False, f"Unknown to_agent in edge: {edge.to_agent}"

        # Checar ciclos via topological sort
        in_degree: dict[str, int] = {a: 0 for a in agents}
        adj: dict[str, list[str]] = {a: [] for a in agents}
        for edge in self._edges:
            adj[edge.from_agent].append(edge.to_agent)
            in_degree[edge.to_agent] += 1

        queue = [a for a in agents if in_degree[a] == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(agents):
            return False, "Cycle detected in MissionDAG"

        return True, ""

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_discussion(
        cls,
        chat_messages: list[Any],
        agent_ids: list[str],
        session_id: str | None = None,
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
            # Obter mission_type do agente via RuntimePolicy
            mission_type = cls._resolve_mission_type(agent_id, session_id=session_id)
            if mission_type is None:
                continue

            # Extrair dependências das mensagens do chat deste agente
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
    def _resolve_mission_type(
        agent_id: str,
        session_id: str | None = None,
    ) -> MissionGraphType | None:
        """Obter o primeiro mission_type disponível para o agente."""
        try:
            from mindflow_backend.agents.specialists.runtime_policy import (
                get_agent_runtime_policy,
            )
            policy = get_agent_runtime_policy(
                agent_id=agent_id,
                session_id=session_id,
            )
            graphs = policy.available_mission_graphs
            return graphs[0] if graphs else None
        except (KeyError, IndexError, ValueError):
            return None

    @staticmethod
    def _extract_dependencies_from_chat(
        agent_id: str,
        messages: list[Any],
        all_agents: list[str],
    ) -> list[str]:
        """Parse simples de dependências declaradas no chat."""
        deps: list[str] = []
        dependency_keywords = [
            "need", "after", "wait", "primeiro", "antes", "depende", "depends",
            "quando", "completar", "terminar", "output", "result"
        ]

        for msg in messages:
            sender = getattr(msg, "sender_jid", None) or ""
            if sender != agent_id:
                continue

            content = getattr(msg, "content", "") or ""
            content_lower = content.lower()

            if any(kw in content_lower for kw in dependency_keywords):
                for other_agent in all_agents:
                    if other_agent != agent_id and other_agent in content_lower:
                        deps.append(other_agent)
                    # Verificar também por substring parcial (ex: "analyst" em "security_analyst")
                    elif other_agent != agent_id and other_agent.replace("_", " ") in content_lower:
                        deps.append(other_agent)

        return list(set(deps))
