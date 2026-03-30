"""XMPP configuration schemas for MindFlow communication."""

from typing import Optional
from pydantic import BaseModel, Field


class XMPPConfig(BaseModel):
    """XMPP server configuration."""
    
    server: str = Field(
        default="localhost",
        description="XMPP server hostname"
    )
    port: int = Field(
        default=5222,
        description="XMPP server port"
    )
    domain: str = Field(
        default="mindflow.local",
        description="XMPP domain name"
    )
    use_tls: bool = Field(
        default=True,
        description="Enable TLS encryption"
    )
    use_ssl: bool = Field(
        default=False,
        description="Enable SSL (legacy)"
    )
    timeout: int = Field(
        default=30,
        description="Connection timeout in seconds"
    )
    
    def get_jid(self, username: str) -> str:
        """Generate full JID for a user."""
        return f"{username}@{self.domain}"
    
    def get_connection_url(self) -> str:
        """Get connection URL."""
        protocol = "xmpps" if self.use_ssl else "xmpp"
        return f"{protocol}://{self.server}:{self.port}"


class AgentIdentity(BaseModel):
    """Agent identity for XMPP communication."""
    
    agent_id: str = Field(
        description="Unique agent identifier"
    )
    agent_type: str = Field(
        description="Agent type (analyst, coder, researcher, etc)"
    )
    username: str = Field(
        description="XMPP username"
    )
    password: str = Field(
        description="XMPP password"
    )
    jid: Optional[str] = Field(
        default=None,
        description="Full JID (auto-generated if not provided)"
    )
    resource: Optional[str] = Field(
        default=None,
        description="XMPP resource identifier"
    )
    
    def model_post_init(self, __context) -> None:
        """Generate JID if not provided."""
        if not self.jid:
            self.jid = f"{self.username}@mindflow.local"
        if self.resource:
            self.jid = f"{self.jid}/{self.resource}"


class MessageEnvelope(BaseModel):
    """Message envelope for agent communication."""
    
    message_id: str = Field(
        description="Unique message identifier"
    )
    from_agent: str = Field(
        description="Sender agent ID"
    )
    to_agent: str = Field(
        description="Recipient agent ID"
    )
    content: str = Field(
        description="Message content"
    )
    message_type: str = Field(
        default="direct",
        description="Message type (direct, request, response, notification, urgent)"
    )
    urgency: str = Field(
        default="MEDIUM",
        description="Message urgency level (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    requires_response: bool = Field(
        default=False,
        description="Whether this message requires a response"
    )
    in_reply_to: Optional[str] = Field(
        default=None,
        description="ID of the message this is replying to"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    def to_xmpp_metadata(self) -> dict:
        """Convert to XMPP metadata format."""
        return {
            "type": self.message_type,
            "urgency": self.urgency,
            "requires_response": str(self.requires_response),
            "message_id": self.message_id,
            **self.metadata
        }