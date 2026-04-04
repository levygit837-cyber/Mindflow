"""AgentCommunicationMixin — Capacidade de comunicação P2P injetada nos agentes.

Injetado pelo DelegationEngine durante delegate_task().
Agentes acessam via self.comm (ou agent.comm no contexto do engine).
Gracefully degrades: se bus não disponível, métodos retornam None/False sem erro.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus

logger = logging.getLogger(__name__)


class AgentCommunicationMixin:
    """Capacidade de comunicação P2P para agentes em execução.

    Injetado pelo DelegationEngine. Nunca instanciado diretamente pelo agente.
    Todos os métodos são gracefully degrading.
    """

    def __init__(self, agent_id: str, bus: "CommunicationBus") -> None:
        self._agent_id = agent_id
        self._bus = bus
        self._messages_sent: int = 0
        self._messages_failed: int = 0

    # ------------------------------------------------------------------
    # API pública para uso pelos agentes
    # ------------------------------------------------------------------

    async def send_to(
        self,
        to_agent: str,
        content: str,
        urgency: str = "MEDIUM",
    ) -> bool:
        """Envia mensagem direta a outro agente.

        Retorna True se entregue, False se falhou ou bus unavailable.
        Não propaga exceção — sempre retorna.
        """
        if not self._bus.is_available:
            logger.debug("comm_send_skipped_no_bus", extra={"to": to_agent})
            return False

        from mindflow_backend.communication.protocols.p2p_protocol import (
            MessageType,
            P2PMessage,
        )

        msg = P2PMessage(
            from_agent=self._agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.DIRECT,
            urgency=urgency,
        )
        try:
            result = await self._bus.send(self._agent_id, to_agent, msg)
            if result:
                self._messages_sent += 1
                logger.debug(
                    "comm_sent",
                    extra={
                        "from": self._agent_id,
                        "to": to_agent,
                        "urgency": urgency,
                    },
                )
            else:
                self._messages_failed += 1
            return result
        except Exception as exc:
            logger.warning(
                "comm_send_error",
                extra={"to": to_agent, "error": str(exc)},
            )
            self._messages_failed += 1
            return False

    async def request_from(
        self,
        to_agent: str,
        content: str,
        timeout: float = 30.0,
    ) -> str | None:
        """Envia request e aguarda resposta com timeout.

        Retorna conteúdo da resposta ou None se timeout/falha.
        Nunca bloqueia além do timeout.
        """
        if not self._bus.is_available:
            logger.debug("comm_request_skipped_no_bus", extra={"to": to_agent})
            return None

        from mindflow_backend.communication.protocols.p2p_protocol import (
            MessageType,
            P2PMessage,
        )

        msg = P2PMessage(
            from_agent=self._agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.REQUEST,
            urgency="HIGH",
            requires_response=True,
        )

        try:
            sent = await self._bus.send(self._agent_id, to_agent, msg)
            if not sent:
                return None

            # Aguardar resposta na própria inbox com timeout
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                incoming = await self._bus.receive(
                    self._agent_id,
                    timeout=min(1.0, remaining),
                )
                if incoming and incoming.in_reply_to == msg.message_id:
                    logger.debug(
                        "comm_response_received",
                        extra={"from": to_agent, "msg_id": msg.message_id},
                    )
                    return incoming.content

            logger.warning(
                "comm_request_timeout",
                extra={"to": to_agent, "timeout": timeout},
            )
            return None

        except Exception as exc:
            logger.warning(
                "comm_request_error",
                extra={"to": to_agent, "error": str(exc)},
            )
            return None

    async def notify(
        self,
        to_agent: str,
        event: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Envia notificação fire-and-forget.

        Não aguarda resposta. Usado para progress updates ao Orchestrator.
        """
        if not self._bus.is_available:
            return

        from mindflow_backend.communication.protocols.p2p_protocol import (
            MessageType,
            P2PMessage,
        )

        payload = json.dumps({"event": event, "data": data or {}})
        msg = P2PMessage(
            from_agent=self._agent_id,
            to_agent=to_agent,
            content=payload,
            message_type=MessageType.NOTIFICATION,
            urgency="LOW",
            requires_response=False,
        )
        try:
            await self._bus.send(self._agent_id, to_agent, msg)
        except Exception as exc:
            logger.debug(
                "comm_notify_failed",
                extra={"to": to_agent, "event": event, "error": str(exc)},
            )

    async def broadcast_to_team(
        self,
        room_id: str,
        content: str,
    ) -> bool:
        """Envia mensagem para todos os membros do room/team.

        Retorna True se pelo menos 1 membro recebeu.
        """
        if not self._bus.is_available:
            return False

        from mindflow_backend.communication.teams.team_chat import TeamMessage

        team_msg = TeamMessage(
            team_id=room_id,
            sender_jid=self._agent_id,
            content=content,
        )
        try:
            return await self._bus.broadcast(self._agent_id, room_id, team_msg)
        except Exception as exc:
            logger.warning(
                "comm_broadcast_error",
                extra={"room_id": room_id, "error": str(exc)},
            )
            return False

    async def notify_progress(
        self,
        percentage: int,
        current_step: str = "",
    ) -> None:
        """Shortcut: notifica Orchestrator de progresso da missão.

        Uso: await agent.comm.notify_progress(60, "investigando módulo X")
        """
        await self.notify(
            to_agent="orchestrator",
            event="mission_progress",
            data={"pct": percentage, "step": current_step, "agent": self._agent_id},
        )

    async def request_specialist_help(
        self,
        task_description: str,
        specialist_hint: str | None = None,
        timeout: float = 60.0,
    ) -> str | None:
        """Agent-initiated collaboration (Tier-2).

        Permite que um agente em execução solicite ajuda de outro durante uma missão.
        Envia uma requisição ao Orchestrator que utilizará o DecentralizedRouter (Tier 2)
        para encontrar o agente adequado (opcionalmente restrito pelo specialist_hint).

        Args:
            task_description: Descrição do que precisa ser feito pelo especialista.
            specialist_hint: Opcional. Dica do tipo de especialista (ex: "coder", "security").
            timeout: Tempo máximo aguardando a resposta com a resolução.

        Returns:
            O resultado da tarefa realizada pelo especialista, ou None se falhar/timeout.
        """
        if not self._bus.is_available:
            logger.debug("comm_specialist_help_skipped_no_bus")
            return None

        logger.info(
            "comm_requesting_specialist_help",
            extra={
                "from": self._agent_id,
                "hint": specialist_hint,
                "task_preview": task_description[:50],
            },
        )

        payload = json.dumps({
            "action": "delegate_subtask",
            "task": task_description,
            "specialist_hint": specialist_hint,
        })

        return await self.request_from(
            to_agent="orchestrator",
            content=payload,
            timeout=timeout,
        )

    def get_stats(self) -> dict[str, Any]:
        """Estatísticas de comunicação deste agente."""
        return {
            "agent_id": self._agent_id,
            "messages_sent": self._messages_sent,
            "messages_failed": self._messages_failed,
            "bus_available": self._bus.is_available,
        }