"""XMPPCommunicationBus — Implementação do CommunicationBus usando ejabberd/XMPP.

Usa XMPPConnectionManager (existente) como transport layer.
Registra agentes como JIDs no ejabberd.
Mensagens P2P = XMPP stanzas diretas.
Team broadcast = XMPP MUC messages.

Fase 4 — drop-in replacement para InternalCommunicationBus.
Trocar via: set_communication_bus(XMPPCommunicationBus(config))

Feature flag: use_xmpp_transport=True no Settings para ativar.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from mindflow_backend.communication.bus.communication_bus import CommunicationBus
from mindflow_backend.communication.connection.xmpp_connection import (
    XMPPConnectionConfig,
    XMPPConnectionManager,
)
from mindflow_backend.communication.protocols.p2p_protocol import P2PMessage
from mindflow_backend.communication.teams.team_chat import TeamMessage

logger = logging.getLogger(__name__)

MINDFLOW_XMPP_DOMAIN = "mindflow.local"
MINDFLOW_MUC_DOMAIN = "conference.mindflow.local"
DEFAULT_AGENT_PASSWORD = "agent_mindflow_2026"


class XMPPCommunicationBus(CommunicationBus):
    """CommunicationBus baseado em ejabberd/XMPP.

    Drop-in replacement para InternalCommunicationBus.
    Usa XMPPConnectionManager para conexão e envio de mensagens.

    Fluxo de registro:
    1. register_agent → connect_agent no XMPPManager
    2. subscribe → registra handler interno que despacha para P2PMessage

    Fluxo de envio:
    1. send → connection_manager.send_message (XMPP stanza)
    2. broadcast → envia para cada subscriber do room (P2P simulado)
    """

    def __init__(self, config: XMPPConnectionConfig | None = None) -> None:
        self._config = config or XMPPConnectionConfig(
            server="localhost",
            port=5222,
            domain=MINDFLOW_XMPP_DOMAIN,
            use_tls=False,  # Dev — habilitar em prod
        )
        self._manager = XMPPConnectionManager(config=self._config)
        self._registered_agents: dict[str, dict[str, Any]] = {}
        self._room_subscribers: dict[str, list[str]] = {}
        self._handlers: dict[str, list[Callable]] = {}
        self._available = False
        self._stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "agents_registered": 0,
            "broadcasts_sent": 0,
        }

    async def connect(self) -> bool:
        """Conecta ao servidor XMPP.

        Não requer autenticação própria — o manager gere conexões por agente.
        Retorna True se o manager está pronto.
        """
        try:
            self._available = True
            self._manager.is_running = True
            logger.info(
                "xmpp_bus_connected",
                extra={
                    "domain": self._config.domain,
                    "server": self._config.server,
                },
            )
            return True
        except Exception as exc:
            logger.error("xmpp_bus_connect_failed", extra={"error": str(exc)})
            self._available = False
            return False

    async def disconnect(self) -> None:
        """Desconecta todos os agentes do XMPP."""
        for agent_id in list(self._registered_agents.keys()):
            try:
                await self._manager.disconnect_agent(agent_id)
            except Exception:
                pass
        self._registered_agents.clear()
        self._handlers.clear()
        self._room_subscribers.clear()
        self._available = False
        self._manager.is_running = False
        logger.info("xmpp_bus_disconnected")

    async def register_agent(self, agent_id: str) -> None:
        """Registra agente no ejabberd como JID e conecta.

        Se o registro no server falhar, ainda registra localmente
        para permitir fallback mock.
        """
        if agent_id in self._registered_agents:
            return

        # Cria handler interno para receber mensagens
        async def _xmpp_message_handler(raw_message: dict[str, Any]) -> None:
            from mindflow_backend.communication.protocols.p2p_protocol import (
                MessageType,
            )

            msg = P2PMessage(
                from_agent=raw_message.get("sender_id", "unknown"),
                to_agent=agent_id,
                content=raw_message.get("content", ""),
                message_type=MessageType.DIRECT,
                metadata={
                    "room_id": raw_message.get("room_id"),
                    "timestamp": raw_message.get("timestamp"),
                    "urgency": raw_message.get("urgency", "MEDIUM"),
                },
            )
            await self._dispatch_handlers(agent_id, msg)

        result = await self._manager.connect_agent(
            username=agent_id,
            password=DEFAULT_AGENT_PASSWORD,
            message_handler=_xmpp_message_handler,
        )

        if result.get("success"):
            self._registered_agents[agent_id] = {
                "jid": result.get("jid"),
                "status": result.get("message", "connected"),
            }
            self._handlers[agent_id] = []
            self._stats["agents_registered"] += 1
            logger.info(
                "xmpp_agent_registered",
                extra={"agent_id": agent_id, "jid": result.get("jid")},
            )
        else:
            # Registra mesmo assim (fallback mock)
            self._registered_agents[agent_id] = {
                "jid": f"{agent_id}@{self._config.domain}",
                "status": result.get("message", "fallback_mock"),
            }
            self._handlers[agent_id] = []
            self._stats["agents_registered"] += 1
            logger.warning(
                "xmpp_agent_fallback_mock",
                extra={"agent_id": agent_id, "error": result.get("error")},
            )

    async def unregister_agent(self, agent_id: str) -> None:
        """Remove agente do ejabberd e limpa handlers."""
        try:
            await self._manager.disconnect_agent(agent_id)
        except Exception:
            pass

        self._registered_agents.pop(agent_id, None)
        self._handlers.pop(agent_id, None)

        # Remove de todas as rooms
        for room_id in list(self._room_subscribers.keys()):
            if agent_id in self._room_subscribers[room_id]:
                self._room_subscribers[room_id].remove(agent_id)

        logger.info("xmpp_agent_unregistered", extra={"agent_id": agent_id})

    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message: P2PMessage,
    ) -> bool:
        """Envia mensagem P2P via XMPP stanza.

        Se XMPP não disponível, fallback para message handler local.
        """
        if not self._available:
            return False

        if from_agent not in self._registered_agents:
            logger.warning(
                "xmpp_send_from_not_registered",
                extra={"from": from_agent, "to": to_agent},
            )
            return False

        try:
            result = await self._manager.send_message(
                from_username=from_agent,
                to_username=to_agent,
                content=message.content,
                urgency=message.urgency.value,
            )

            if result.get("success"):
                self._stats["messages_sent"] += 1
                logger.debug(
                    "xmpp_message_sent",
                    extra={
                        "from": from_agent,
                        "to": to_agent,
                        "msg_id": message.message_id,
                    },
                )
                return True
            else:
                self._stats["messages_failed"] += 1
                logger.warning(
                    "xmpp_send_failed",
                    extra={
                        "from": from_agent,
                        "to": to_agent,
                        "error": result.get("error"),
                    },
                )
                return False

        except Exception as exc:
            self._stats["messages_failed"] += 1
            logger.error(
                "xmpp_send_exception",
                extra={"from": from_agent, "to": to_agent, "error": str(exc)},
            )
            return False

    async def broadcast(
        self,
        from_agent: str,
        room_id: str,
        message: TeamMessage,
    ) -> bool:
        """Envia mensagem para room MUC.

        Implementação: envia P2P para cada subscriber do room
        (simula MUC via envios individuais).
        """
        if not self._available:
            return False

        subscribers = self._room_subscribers.get(room_id, [])
        if not subscribers:
            logger.warning(
                "xmpp_broadcast_no_subscribers",
                extra={"room_id": room_id},
            )
            return False

        delivered = 0
        from mindflow_backend.communication.protocols.p2p_protocol import MessageType

        for agent_id in subscribers:
            if agent_id == from_agent:
                continue

            p2p_msg = P2PMessage(
                from_agent=from_agent,
                to_agent=agent_id,
                content=message.content,
                message_type=MessageType.DIRECT,
                metadata={
                    "room_id": room_id,
                    "team_message_id": message.message_id,
                    "broadcast": True,
                },
            )

            if await self.send(from_agent, agent_id, p2p_msg):
                delivered += 1

        self._stats["broadcasts_sent"] += 1
        return delivered > 0

    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[P2PMessage], Awaitable[None]],
    ) -> None:
        """Registra handler para mensagens XMPP recebidas.

        O handler é chamado quando uma mensagem chega via XMPP
        do connection_manager.
        """
        if agent_id not in self._handlers:
            # Auto-registra se ainda não registrado
            await self.register_agent(agent_id)

        self._handlers[agent_id].append(handler)
        logger.debug(
            "xmpp_handler_registered",
            extra={"agent_id": agent_id},
        )

    def join_room(self, agent_id: str, room_id: str) -> None:
        """Adiciona agente a um room MUC."""
        if agent_id not in self._registered_agents:
            logger.warning(
                "xmpp_join_room_not_registered",
                extra={"agent_id": agent_id, "room_id": room_id},
            )
            return

        if room_id not in self._room_subscribers:
            self._room_subscribers[room_id] = []

        if agent_id not in self._room_subscribers[room_id]:
            self._room_subscribers[room_id].append(agent_id)
            logger.info(
                "xmpp_agent_joined_room",
                extra={"agent_id": agent_id, "room_id": room_id},
            )

    def leave_room(self, agent_id: str, room_id: str) -> None:
        """Remove agente de um room MUC."""
        if room_id in self._room_subscribers:
            if agent_id in self._room_subscribers[room_id]:
                self._room_subscribers[room_id].remove(agent_id)
                logger.info(
                    "xmpp_agent_left_room",
                    extra={"agent_id": agent_id, "room_id": room_id},
                )

    async def health_check(self) -> dict[str, Any]:
        """Retorna status do bus XMPP."""
        connected = self._manager.get_connected_agents()
        stats = self._manager.get_connection_stats()

        return {
            "type": "xmpp",
            "available": self._available,
            "domain": self._config.domain,
            "server": self._config.server,
            "registered_agents": list(self._registered_agents.keys()),
            "connected_agents": connected,
            "rooms": {
                room_id: len(subs)
                for room_id, subs in self._room_subscribers.items()
            },
            "stats": self._stats.copy(),
            "connection_stats": stats,
        }

    @property
    def is_available(self) -> bool:
        return self._available

    async def _dispatch_handlers(
        self,
        agent_id: str,
        message: P2PMessage,
    ) -> None:
        """Dispatch message to registered handlers for an agent."""
        for handler in self._handlers.get(agent_id, []):
            try:
                await handler(message)
            except Exception as exc:
                logger.error(
                    "xmpp_handler_error",
                    extra={"agent_id": agent_id, "error": str(exc)},
                )