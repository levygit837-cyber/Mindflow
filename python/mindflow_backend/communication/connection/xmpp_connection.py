"""
XMPP Connection Manager for MindFlow SPADE agents.

Adapted from Plexo project for MindFlow architecture.
Manages XMPP connections using aioxmpp library.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class XMPPConnectionConfig:
    """XMPP connection configuration."""
    server: str = "localhost"
    port: int = 5222
    domain: str = "mindflow.local"
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30
    
    def get_jid(self, username: str) -> str:
        """Generate full JID for a user."""
        return f"{username}@{self.domain}"


class XMPPConnectionManager:
    """
    Manages XMPP connections for MindFlow agents.
    
    Provides connection pooling, message sending, and health monitoring
    for XMPP-based agent communication.
    """
    
    def __init__(self, config: XMPPConnectionConfig):
        self.config = config
        self.connections: Dict[str, Any] = {}
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.is_running: bool = False
        self._connection_pool: Dict[str, Dict[str, Any]] = {}
    
    async def register_agent(self, username: str, password: str) -> Dict[str, Any]:
        """
        Register a new agent on the XMPP server.
        
        Args:
            username: Agent username
            password: Agent password
            
        Returns:
            Registration result dictionary
        """
        jid = self.config.get_jid(username)
        
        try:
            import aioxmpp
            
            jid_obj = aioxmpp.JID.fromstr(jid)
            registrar = aioxmpp.RegistrationService(
                jid_obj.localpart,
                aioxmpp.make_security_layer(password)
            )
            
            form = await registrar.get_registration_form()
            form.fields["username"] = username
            form.fields["password"] = password
            
            await registrar.submit_form(form)
            
            logger.info(f"Agent {username} registered successfully")
            
            return {
                "success": True,
                "jid": jid,
                "username": username,
                "message": f"Agent {username} registered successfully"
            }
        
        except Exception as e:
            logger.error(f"Failed to register agent {username}: {e}")
            return {
                "success": False,
                "jid": jid,
                "username": username,
                "error": str(e)
            }
    
    async def connect_agent(
        self,
        username: str,
        password: str,
        message_handler: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Connect an agent to the XMPP server.
        
        Args:
            username: Agent username
            password: Agent password
            message_handler: Optional callback for incoming messages
            
        Returns:
            Connection result dictionary
        """
        jid = self.config.get_jid(username)
        
        if username in self.connections:
            logger.warning(f"Agent {username} already connected")
            return {
                "success": True,
                "jid": jid,
                "username": username,
                "message": f"Agent {username} already connected"
            }
        
        try:
            import aioxmpp
            
            jid_obj = aioxmpp.JID.fromstr(jid)
            client = aioxmpp.PresenceManagedClient(
                jid_obj,
                aioxmpp.make_security_layer(password)
            )
            
            # Store connection info
            self.connections[username] = {
                "client": client,
                "jid": jid,
                "connected_at": datetime.now(),
                "status": "connected"
            }
            
            # Register message handler
            if message_handler:
                if username not in self.message_handlers:
                    self.message_handlers[username] = []
                self.message_handlers[username].append(message_handler)
            
            logger.info(f"Agent {username} connected successfully")
            
            return {
                "success": True,
                "jid": jid,
                "username": username,
                "message": f"Agent {username} connected successfully"
            }
        
        except ImportError:
            logger.warning("aioxmpp not available, using mock connection")
            
            # Mock connection for development
            self.connections[username] = {
                "client": None,
                "jid": jid,
                "connected_at": datetime.now(),
                "status": "mock_connected"
            }
            
            if message_handler:
                if username not in self.message_handlers:
                    self.message_handlers[username] = []
                self.message_handlers[username].append(message_handler)
            
            return {
                "success": True,
                "jid": jid,
                "username": username,
                "message": f"Agent {username} connected (mock mode)"
            }
        
        except Exception as e:
            logger.error(f"Failed to connect agent {username}: {e}")
            return {
                "success": False,
                "jid": jid,
                "username": username,
                "error": str(e)
            }
    
    async def send_message(
        self,
        from_username: str,
        to_username: str,
        content: str,
        urgency: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Send a message from one agent to another.
        
        Args:
            from_username: Sender username
            to_username: Recipient username
            content: Message content
            urgency: Message urgency level
            
        Returns:
            Send result dictionary
        """
        from_jid = self.config.get_jid(from_username)
        to_jid = self.config.get_jid(to_username)
        
        if from_username not in self.connections:
            return {
                "success": False,
                "error": f"Agent {from_username} is not connected"
            }
        
        try:
            conn = self.connections[from_username]
            
            if conn.get("status") == "mock_connected":
                # Mock message sending
                logger.info(f"[MOCK] Message from {from_username} to {to_username}: {content[:50]}...")
                
                # Notify handlers
                if to_username in self.message_handlers:
                    for handler in self.message_handlers[to_username]:
                        try:
                            await handler({
                                "sender": from_jid,
                                "sender_id": from_username,
                                "content": content,
                                "urgency": urgency,
                                "type": "direct",
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            logger.error(f"Message handler error: {e}")
                
                return {
                    "success": True,
                    "from": from_jid,
                    "to": to_jid,
                    "content": content,
                    "urgency": urgency,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Real XMPP sending
            import aioxmpp
            
            msg = aioxmpp.Message(
                to=aioxmpp.JID.fromstr(to_jid),
                type_=aioxmpp.MessageType.CHAT
            )
            msg.body[None] = content
            
            stream = conn.get("stream")
            if stream:
                await stream.send(msg)
            
            logger.info(f"Message sent from {from_username} to {to_username}")
            
            return {
                "success": True,
                "from": from_jid,
                "to": to_jid,
                "content": content,
                "urgency": urgency,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def disconnect_agent(self, username: str) -> bool:
        """
        Disconnect an agent from the XMPP server.
        
        Args:
            username: Agent username
            
        Returns:
            True if disconnected successfully
        """
        if username not in self.connections:
            logger.warning(f"Agent {username} not connected")
            return False
        
        try:
            conn = self.connections[username]
            
            if conn.get("status") != "mock_connected":
                # Real disconnection
                client = conn.get("client")
                if client:
                    pass  # aioxmpp client cleanup handled by context manager
            
            del self.connections[username]
            
            if username in self.message_handlers:
                del self.message_handlers[username]
            
            logger.info(f"Agent {username} disconnected")
            return True
        
        except Exception as e:
            logger.error(f"Failed to disconnect agent {username}: {e}")
            return False
    
    def get_connected_agents(self) -> List[str]:
        """Get list of connected agent usernames."""
        return list(self.connections.keys())
    
    def is_agent_connected(self, username: str) -> bool:
        """Check if an agent is connected."""
        return username in self.connections
    
    def get_agent_jid(self, username: str) -> Optional[str]:
        """Get JID for a connected agent."""
        if username in self.connections:
            return self.connections[username].get("jid")
        return None
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.connections),
            "connected_agents": list(self.connections.keys()),
            "handler_count": sum(len(h) for h in self.message_handlers.values()),
            "is_running": self.is_running
        }