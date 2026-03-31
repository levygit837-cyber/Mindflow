"""
Team Manager for MindFlow agent groups.

Adapted from Plexo project for MindFlow architecture.
Manages teams, members, and team chats.
"""

import uuid
from typing import Any

from .team import Team, TeamStatus
from .team_chat import TeamChat


class TeamManager:
    """
    Manages teams of MindFlow agents.
    
    Provides team creation, member management, and chat operations.
    """
    
    def __init__(self):
        self.teams: dict[str, Team] = {}
        self.team_chats: dict[str, TeamChat] = {}
    
    def create_team(
        self,
        name: str,
        description: str = "",
        muc_room_jid: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> Team:
        """
        Create a new team.
        
        Args:
            name: Team name
            description: Team description
            muc_room_jid: Optional MUC room JID
            metadata: Optional metadata
            
        Returns:
            Created Team
        """
        team = Team(
            name=name,
            description=description,
            muc_room_jid=muc_room_jid or f"{uuid.uuid4()}@conference.mindflow.local",
            metadata=metadata or {}
        )
        
        self.teams[team.team_id] = team
        self.team_chats[team.team_id] = TeamChat(team.team_id, team.muc_room_jid)
        
        return team
    
    def get_team(self, team_id: str) -> Team | None:
        """Get team by ID."""
        return self.teams.get(team_id)
    
    def get_team_by_name(self, name: str) -> Team | None:
        """Get team by name."""
        for team in self.teams.values():
            if team.name == name:
                return team
        return None
    
    def get_all_teams(self) -> list[Team]:
        """Get all teams."""
        return list(self.teams.values())
    
    def get_active_teams(self) -> list[Team]:
        """Get active teams."""
        return [t for t in self.teams.values() if t.status == TeamStatus.ACTIVE]
    
    def delete_team(self, team_id: str) -> bool:
        """Delete a team."""
        if team_id in self.teams:
            del self.teams[team_id]
            if team_id in self.team_chats:
                del self.team_chats[team_id]
            return True
        return False
    
    def update_team(
        self,
        team_id: str,
        name: str | None = None,
        description: str | None = None,
        status: TeamStatus | None = None,
        metadata: dict[str, Any] | None = None
    ) -> Team | None:
        """Update a team."""
        team = self.get_team(team_id)
        if not team:
            return None
        
        if name is not None:
            team.name = name
        if description is not None:
            team.description = description
        if status is not None:
            team.status = status
        if metadata is not None:
            team.metadata.update(metadata)
        
        return team
    
    def add_member(self, team_id: str, agent_jid: str, role: str = "member") -> bool:
        """Add a member to a team."""
        team = self.get_team(team_id)
        if team:
            return team.add_member(agent_jid, role)
        return False
    
    def remove_member(self, team_id: str, agent_jid: str) -> bool:
        """Remove a member from a team."""
        team = self.get_team(team_id)
        if team:
            return team.remove_member(agent_jid)
        return False
    
    def get_member_teams(self, agent_jid: str) -> list[Team]:
        """Get teams that an agent is a member of."""
        return [t for t in self.teams.values() if t.has_member(agent_jid)]
    
    def get_team_chat(self, team_id: str) -> TeamChat | None:
        """Get team chat."""
        return self.team_chats.get(team_id)
    
    def send_team_message(
        self,
        team_id: str,
        sender_jid: str,
        content: str,
        reference_message_id: str | None = None
    ) -> dict[str, Any] | None:
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
        chat = self.get_team_chat(team_id)
        if chat:
            message = chat.create_message(
                sender_jid=sender_jid,
                content=content,
                reference_message_id=reference_message_id
            )
            return message.to_dict()
        return None
    
    def get_team_messages(
        self,
        team_id: str,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get messages from a team."""
        chat = self.get_team_chat(team_id)
        if chat:
            return [m.to_dict() for m in chat.get_recent_messages(limit)]
        return []
    
    def search_team_messages(
        self,
        team_id: str,
        query: str
    ) -> list[dict[str, Any]]:
        """Search messages in a team."""
        chat = self.get_team_chat(team_id)
        if chat:
            return [m.to_dict() for m in chat.search_messages(query)]
        return []
    
    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        total_members = sum(t.get_member_count() for t in self.teams.values())
        active_teams = len(self.get_active_teams())
        
        return {
            "total_teams": len(self.teams),
            "active_teams": active_teams,
            "total_members": total_members,
            "average_members_per_team": (
                total_members / len(self.teams) if self.teams else 0
            )
        }