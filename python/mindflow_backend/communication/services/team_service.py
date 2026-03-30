"""
Team Service for MindFlow agent communication.

Adapted from Plexo project for MindFlow architecture.
Manages teams and team chats.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..teams.team_manager import TeamManager
from ..teams.team import Team, TeamStatus
from ..teams.team_chat import TeamChat
from .xmpp_service import XMPPService

logger = logging.getLogger(__name__)


class TeamService:
    """
    Service for managing teams and team communication.
    
    Provides high-level interface for team operations.
    """
    
    def __init__(self, xmpp_service: XMPPService):
        self.xmpp_service = xmpp_service
        self.team_manager = TeamManager()
        logger.info("TeamService initialized")
    
    def create_team(
        self,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new team.
        
        Args:
            name: Team name
            description: Team description
            metadata: Optional metadata
            
        Returns:
            Team dictionary
        """
        try:
            team = self.team_manager.create_team(
                name=name,
                description=description,
                metadata=metadata
            )
            logger.info(f"Team '{name}' created with ID {team.team_id}")
            return team.to_dict()
        except Exception as e:
            logger.error(f"Error creating team: {e}")
            return {"error": str(e)}
    
    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team by ID."""
        team = self.team_manager.get_team(team_id)
        return team.to_dict() if team else None
    
    def get_team_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get team by name."""
        team = self.team_manager.get_team_by_name(name)
        return team.to_dict() if team else None
    
    def get_all_teams(self) -> List[Dict[str, Any]]:
        """Get all teams."""
        return [t.to_dict() for t in self.team_manager.get_all_teams()]
    
    def get_active_teams(self) -> List[Dict[str, Any]]:
        """Get active teams."""
        return [t.to_dict() for t in self.team_manager.get_active_teams()]
    
    def update_team(
        self,
        team_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a team."""
        team_status = TeamStatus(status) if status else None
        team = self.team_manager.update_team(
            team_id=team_id,
            name=name,
            description=description,
            status=team_status,
            metadata=metadata
        )
        return team.to_dict() if team else None
    
    def delete_team(self, team_id: str) -> bool:
        """Delete a team."""
        return self.team_manager.delete_team(team_id)
    
    def add_member(
        self,
        team_id: str,
        agent_jid: str,
        role: str = "member"
    ) -> bool:
        """Add a member to a team."""
        return self.team_manager.add_member(team_id, agent_jid, role)
    
    def remove_member(self, team_id: str, agent_jid: str) -> bool:
        """Remove a member from a team."""
        return self.team_manager.remove_member(team_id, agent_jid)
    
    def get_member_teams(self, agent_jid: str) -> List[Dict[str, Any]]:
        """Get teams that an agent is a member of."""
        return [
            t.to_dict() for t in self.team_manager.get_member_teams(agent_jid)
        ]
    
    def send_team_message(
        self,
        team_id: str,
        sender_jid: str,
        content: str,
        reference_message_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message to a team.
        
        Args:
            team_id: Team ID
            sender_jid: Sender JID
            content: Message content
            reference_message_id: Optional reference to another message
            
        Returns:
            Message dictionary or None
        """
        return self.team_manager.send_team_message(
            team_id=team_id,
            sender_jid=sender_jid,
            content=content,
            reference_message_id=reference_message_id
        )
    
    def get_team_messages(
        self,
        team_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages from a team."""
        return self.team_manager.get_team_messages(team_id, limit)
    
    def search_team_messages(
        self,
        team_id: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """Search messages in a team."""
        return self.team_manager.search_team_messages(team_id, query)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return self.team_manager.get_stats()