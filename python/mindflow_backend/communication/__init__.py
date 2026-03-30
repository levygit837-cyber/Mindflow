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

from .protocols.xmpp_protocol import XMPPProtocol
from .protocols.p2p_protocol import P2PProtocol, P2PMessage, MessageType
from .teams.team import Team, TeamMember, TeamStatus
from .teams.team_chat import TeamChat, TeamMessage
from .teams.team_manager import TeamManager
from .connection.xmpp_connection import XMPPConnectionManager, XMPPConfig
from .services.xmpp_service import XMPPService
from .services.p2p_service import P2PService
from .services.team_service import TeamService

__all__ = [
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
    "XMPPConfig",
    
    # Services
    "XMPPService",
    "P2PService",
    "TeamService",
]