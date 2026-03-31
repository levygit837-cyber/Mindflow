"""
XMPP Protocol utilities for MindFlow SPADE agents.

Adapted from Plexo project for MindFlow architecture.
Provides message formatting, parsing, and template creation.
"""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class XMPPProtocol:
    """
    XMPP protocol utilities for message formatting and parsing.
    
    Provides helper methods for creating and parsing XMPP messages
    with standardized metadata and content structure.
    """
    
    @staticmethod
    def create_message(
        to_jid: str,
        content: str,
        message_type: str = "default",
        metadata: dict[str, Any] | None = None,
        sender_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a standardized XMPP message.
        
        Args:
            to_jid: Recipient JID
            content: Message content
            message_type: Type of message
            metadata: Optional additional metadata
            sender_id: Optional sender identifier
            
        Returns:
            Message dictionary
        """
        message = {
            "to": to_jid,
            "body": content,
            "metadata": {
                "type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }
        
        if sender_id:
            message["metadata"]["sender_id"] = sender_id
        
        if metadata:
            message["metadata"].update(metadata)
        
        return message
    
    @staticmethod
    def create_request(
        to_jid: str,
        action: str,
        params: dict[str, Any] | None = None,
        sender_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a request message.
        
        Args:
            to_jid: Recipient JID
            action: Action to request
            params: Optional request parameters
            sender_id: Optional sender identifier
            
        Returns:
            Request message dictionary
        """
        content = json.dumps({
            "action": action,
            "params": params or {},
        })
        
        return XMPPProtocol.create_message(
            to_jid=to_jid,
            content=content,
            message_type="request",
            sender_id=sender_id,
        )
    
    @staticmethod
    def create_response(
        to_jid: str,
        result: Any,
        success: bool = True,
        error: str | None = None,
        sender_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a response message.
        
        Args:
            to_jid: Recipient JID
            result: Response result
            success: Whether request was successful
            error: Optional error message
            sender_id: Optional sender identifier
            
        Returns:
            Response message dictionary
        """
        content = json.dumps({
            "success": success,
            "result": result,
            "error": error,
        })
        
        return XMPPProtocol.create_message(
            to_jid=to_jid,
            content=content,
            message_type="response",
            sender_id=sender_id,
        )
    
    @staticmethod
    def create_notification(
        to_jid: str,
        event: str,
        data: dict[str, Any] | None = None,
        sender_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a notification message.
        
        Args:
            to_jid: Recipient JID
            event: Event name
            data: Optional event data
            sender_id: Optional sender identifier
            
        Returns:
            Notification message dictionary
        """
        content = json.dumps({
            "event": event,
            "data": data or {},
        })
        
        return XMPPProtocol.create_message(
            to_jid=to_jid,
            content=content,
            message_type="notification",
            sender_id=sender_id,
        )
    
    @staticmethod
    def parse_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        Parse an XMPP message into structured data.
        
        Args:
            message: Raw message dictionary
            
        Returns:
            Parsed message data
        """
        try:
            sender = message.get("sender", "")
            content = message.get("content", message.get("body", ""))
            metadata = message.get("metadata", {})
            
            message_type = metadata.get("type", "default")
            timestamp = metadata.get("timestamp")
            sender_id = metadata.get("sender_id")
            
            parsed_content = None
            if message_type in ["request", "response", "notification"]:
                try:
                    parsed_content = json.loads(content)
                except json.JSONDecodeError:
                    parsed_content = content
            else:
                parsed_content = content
            
            return {
                "sender": sender,
                "sender_id": sender_id,
                "type": message_type,
                "content": parsed_content,
                "timestamp": timestamp,
                "metadata": metadata,
            }
        
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return {
                "sender": "",
                "sender_id": None,
                "type": "error",
                "content": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {},
            }
    
    @staticmethod
    def validate_jid(jid: str) -> bool:
        """
        Validate XMPP JID format.
        
        Args:
            jid: JID to validate
            
        Returns:
            True if JID is valid
        """
        if not jid or "@" not in jid:
            return False
        
        parts = jid.split("@")
        if len(parts) != 2:
            return False
        
        username, domain = parts
        if not username or not domain:
            return False
        
        return True
    
    @staticmethod
    def extract_username(jid: str) -> str:
        """
        Extract username from JID.
        
        Args:
            jid: Full JID
            
        Returns:
            Username part of JID
        """
        if "@" in jid:
            return jid.split("@")[0]
        return jid
    
    @staticmethod
    def extract_domain(jid: str) -> str:
        """
        Extract domain from JID.
        
        Args:
            jid: Full JID
            
        Returns:
            Domain part of JID
        """
        if "@" in jid:
            domain_part = jid.split("@")[1]
            if "/" in domain_part:
                return domain_part.split("/")[0]
            return domain_part
        return ""
    
    @staticmethod
    def build_jid(username: str, domain: str, resource: str | None = None) -> str:
        """
        Build JID from components.
        
        Args:
            username: Username
            domain: Domain
            resource: Optional resource
            
        Returns:
            Full JID
        """
        jid = f"{username}@{domain}"
        if resource:
            jid = f"{jid}/{resource}"
        return jid