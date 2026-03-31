"""
MindFlow Communication Module - SPADE/XMPP Integration

This module provides XMPP-based communication between MindFlow agents using the SPADE protocol.

Components:
    - protocols: XMPP and P2P protocol implementations
    - teams: Team management and MUC chat
    - connection: XMPP connection management
    - services: High-level communication services
    - circuit_breaker: Fault tolerance for agent communication
    - schemas: Data models for communication
"""

from .bus.communication_bus import (
    CommunicationBus,
    InternalCommunicationBus,
    get_communication_bus,
    set_communication_bus,
)
from .connection.xmpp_connection import XMPPConnectionConfig, XMPPConnectionManager
from .mixins.agent_communication import AgentCommunicationMixin
from .protocols.p2p_protocol import MessageType, P2PMessage, P2PProtocol
from .protocols.xmpp_protocol import XMPPProtocol
from .services.p2p_service import P2PService
from .services.team_service import TeamService
from .services.xmpp_service import XMPPService
from .teams.team import Team, TeamMember, TeamStatus
from .teams.team_chat import TeamChat, TeamMessage
from .teams.team_manager import TeamManager

__all__ = [
    # Bus
    "CommunicationBus",
    "InternalCommunicationBus",
    "get_communication_bus",
    "set_communication_bus",
    # Protocols
    "XMPPProtocol",
    "P2PProtocol",
    "P2PMessage",
    "MessageType",
    # Teams
    "Team",
    "TeamMember",
    "TeamStatus",
    "TeamChat",
    "TeamMessage",
    "TeamManager",
    # Connection
    "XMPPConnectionManager",
    "XMPPConnectionConfig",
    # Services
    "XMPPService",
    "P2PService",
    "TeamService",
    # Mixins
    "AgentCommunicationMixin",
]
