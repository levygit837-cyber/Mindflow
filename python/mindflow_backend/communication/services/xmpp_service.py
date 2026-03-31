"""
XMPP Service for MindFlow agent communication.

Adapted from Plexo project for MindFlow architecture.
Manages XMPP connections for agents.
"""

import logging
from typing import Any

from ..circuit_breaker import circuit_protected
from ..connection.xmpp_connection import XMPPConnectionConfig, XMPPConnectionManager

logger = logging.getLogger(__name__)


class XMPPService:
    """
    Service for managing XMPP connections.
    
    Provides high-level interface for agent XMPP communication.
    """
    
    def __init__(
        self,
        server: str = "localhost",
        port: int = 5222,
        domain: str = "mindflow.local"
    ):
        self.config = XMPPConnectionConfig(
            server=server,
            port=port,
            domain=domain
        )
        self.connection_manager = XMPPConnectionManager(self.config)
        logger.info(
            f"XMPPService initialized with server: {self.config.server}:{self.config.port}"
        )
    
    @circuit_protected(
        breaker_name="xmpp_register",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "XMPP circuit open"},
    )
    async def register_agent(self, username: str, password: str) -> dict[str, Any]:
        """
        Register a new agent on the XMPP server.
        
        Args:
            username: Agent username
            password: Agent password
            
        Returns:
            Registration result
        """
        try:
            result = await self.connection_manager.register_agent(username, password)
            if result.get("success"):
                logger.info(f"Agent {username} registered successfully")
            else:
                logger.error(
                    f"Failed to register agent {username}: {result.get('error')}"
                )
            return result
        except Exception as e:
            logger.error(f"Error registering agent {username}: {e}")
            return {"success": False, "error": str(e)}
    
    @circuit_protected(
        breaker_name="xmpp_connect",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "XMPP circuit open"},
    )
    async def connect_agent(self, username: str, password: str) -> dict[str, Any]:
        """
        Connect an agent to the XMPP server.
        
        Args:
            username: Agent username
            password: Agent password
            
        Returns:
            Connection result
        """
        try:
            result = await self.connection_manager.connect_agent(username, password)
            if result.get("success"):
                logger.info(f"Agent {username} connected successfully")
            else:
                logger.error(
                    f"Failed to connect agent {username}: {result.get('error')}"
                )
            return result
        except Exception as e:
            logger.error(f"Error connecting agent {username}: {e}")
            return {"success": False, "error": str(e)}
    
    @circuit_protected(
        breaker_name="xmpp_disconnect",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return=False,
    )
    async def disconnect_agent(self, username: str) -> bool:
        """
        Disconnect an agent from the XMPP server.
        
        Args:
            username: Agent username
            
        Returns:
            True if disconnected successfully
        """
        try:
            result = await self.connection_manager.disconnect_agent(username)
            if result:
                logger.info(f"Agent {username} disconnected successfully")
            else:
                logger.error(f"Failed to disconnect agent {username}")
            return result
        except Exception as e:
            logger.error(f"Error disconnecting agent {username}: {e}")
            return False
    
    @circuit_protected(
        breaker_name="xmpp_send_message",
        failure_threshold=5,
        recovery_timeout=30,
        success_threshold=3,
        fallback_return={"success": False, "error": "XMPP circuit open"},
    )
    async def send_message(
        self,
        from_username: str,
        to_username: str,
        content: str,
        urgency: str = "MEDIUM"
    ) -> dict[str, Any]:
        """
        Send a message between agents.
        
        Args:
            from_username: Sender username
            to_username: Recipient username
            content: Message content
            urgency: Message urgency level
            
        Returns:
            Send result
        """
        try:
            result = await self.connection_manager.send_message(
                from_username=from_username,
                to_username=to_username,
                content=content,
                urgency=urgency
            )
            if result.get("success"):
                logger.info(
                    f"Message sent from {from_username} to {to_username}"
                )
            else:
                logger.error(f"Failed to send message: {result.get('error')}")
            return result
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    def get_connected_agents(self) -> list[str]:
        """Get list of connected agents."""
        return self.connection_manager.get_connected_agents()
    
    def is_agent_connected(self, username: str) -> bool:
        """Check if an agent is connected."""
        return self.connection_manager.is_agent_connected(username)
    
    def get_agent_jid(self, username: str) -> str | None:
        """Get JID for an agent."""
        return self.connection_manager.get_agent_jid(username)
    
    def get_config(self) -> dict[str, Any]:
        """Get service configuration."""
        return {
            "server": self.config.server,
            "port": self.config.port,
            "domain": self.config.domain,
            "use_tls": self.config.use_tls,
            "use_ssl": self.config.use_ssl
        }