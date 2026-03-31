"""
P2P Service for MindFlow agent communication.

Adapted from Plexo project for MindFlow architecture.
Provides peer-to-peer messaging between agents.
"""

import logging
from typing import Any

from ..circuit_breaker import circuit_protected
from ..protocols.p2p_protocol import P2PProtocol
from .xmpp_service import XMPPService

logger = logging.getLogger(__name__)


class P2PService:
    """
    Service for peer-to-peer communication between agents.
    
    Manages P2P protocols and message routing.
    """
    
    def __init__(self, xmpp_service: XMPPService):
        self.xmpp_service = xmpp_service
        self.protocols: dict[str, P2PProtocol] = {}
        logger.info("P2PService initialized")
    
    def get_or_create_protocol(self, agent_id: str) -> P2PProtocol:
        """
        Get or create P2P protocol for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            P2PProtocol instance
        """
        if agent_id not in self.protocols:
            self.protocols[agent_id] = P2PProtocol(
                agent_id,
                self.xmpp_service.connection_manager
            )
            logger.info(f"P2P protocol created for agent {agent_id}")
        return self.protocols[agent_id]
    
    @circuit_protected(
        breaker_name="p2p_direct_message",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "P2P circuit open"},
    )
    async def send_direct_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        urgency: str = "MEDIUM"
    ) -> dict[str, Any]:
        """
        Send a direct message between agents.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            content: Message content
            urgency: Message urgency level
            
        Returns:
            Send result
        """
        try:
            protocol = self.get_or_create_protocol(from_agent)
            result = await protocol.send_direct_message(to_agent, content, urgency)
            logger.info(f"Direct message sent from {from_agent} to {to_agent}")
            return result
        except Exception as e:
            logger.error(f"Error sending direct message: {e}")
            return {"success": False, "error": str(e)}
    
    @circuit_protected(
        breaker_name="p2p_request",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "P2P circuit open"},
    )
    async def send_request(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        urgency: str = "HIGH"
    ) -> dict[str, Any]:
        """
        Send a request that requires a response.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            content: Request content
            urgency: Message urgency level
            
        Returns:
            Send result
        """
        try:
            protocol = self.get_or_create_protocol(from_agent)
            result = await protocol.send_request(to_agent, content, urgency)
            logger.info(f"Request sent from {from_agent} to {to_agent}")
            return result
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return {"success": False, "error": str(e)}
    
    @circuit_protected(
        breaker_name="p2p_response",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "P2P circuit open"},
    )
    async def send_response(
        self,
        from_agent: str,
        to_agent: str,
        original_message_id: str,
        content: str
    ) -> dict[str, Any]:
        """
        Send a response to a request.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            original_message_id: ID of the message being replied to
            content: Response content
            
        Returns:
            Send result
        """
        try:
            protocol = self.get_or_create_protocol(from_agent)
            result = await protocol.send_response(
                to_agent,
                original_message_id,
                content
            )
            logger.info(f"Response sent from {from_agent} to {to_agent}")
            return result
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            return {"success": False, "error": str(e)}
    
    @circuit_protected(
        breaker_name="p2p_urgent_message",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "P2P circuit open"},
    )
    async def send_urgent_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str
    ) -> dict[str, Any]:
        """
        Send an urgent message.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            content: Message content
            
        Returns:
            Send result
        """
        try:
            protocol = self.get_or_create_protocol(from_agent)
            result = await protocol.send_urgent_message(to_agent, content)
            logger.info(f"Urgent message sent from {from_agent} to {to_agent}")
            return result
        except Exception as e:
            logger.error(f"Error sending urgent message: {e}")
            return {"success": False, "error": str(e)}
    
    @circuit_protected(
        breaker_name="p2p_notification",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "P2P circuit open"},
    )
    async def send_notification(
        self,
        from_agent: str,
        to_agent: str,
        content: str
    ) -> dict[str, Any]:
        """
        Send a notification.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            content: Notification content
            
        Returns:
            Send result
        """
        try:
            protocol = self.get_or_create_protocol(from_agent)
            result = await protocol.send_notification(to_agent, content)
            logger.info(f"Notification sent from {from_agent} to {to_agent}")
            return result
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {"success": False, "error": str(e)}
    
    def get_pending_requests(self, agent_id: str) -> list[dict[str, Any]]:
        """Get pending requests for an agent."""
        protocol = self.get_or_create_protocol(agent_id)
        return protocol.get_pending_requests()
    
    def get_message_history(
        self,
        agent_id: str,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get message history for an agent."""
        protocol = self.get_or_create_protocol(agent_id)
        return protocol.get_message_history(limit)
    
    def get_conversation_with(
        self,
        agent_id: str,
        other_agent: str
    ) -> list[dict[str, Any]]:
        """Get conversation with another agent."""
        protocol = self.get_or_create_protocol(agent_id)
        return protocol.get_conversation_with(other_agent)
    
    def get_stats(self, agent_id: str) -> dict[str, Any]:
        """Get P2P protocol statistics for an agent."""
        protocol = self.get_or_create_protocol(agent_id)
        return protocol.get_stats()