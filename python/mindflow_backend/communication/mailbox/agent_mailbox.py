"""AgentMailbox — Fast in-process communication layer for agents.

Based on Claude Code's mailbox system, this provides a lightweight, fast
communication layer for point-to-point and broadcast messaging between agents.
It complements (but does not replace) the CommunicationBus for XMPP/Fase 4.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class MailboxMessage:
    """A message in the agent mailbox."""
    from_agent: str
    text: str
    summary: str | None
    timestamp: str
    color: str | None = None


@dataclass
class StructuredMessage:
    """Structured message types for agent coordination."""
    type: str  # "shutdown_request", "shutdown_response", "plan_approval_response", etc.
    request_id: str | None = None
    approve: bool | None = None
    reason: str | None = None
    feedback: str | None = None


class AgentMailbox:
    """Fast in-process mailbox for agent communication.

    Each agent has its own inbox (asyncio.Queue). Messages have TTL to prevent
    accumulation. This is designed to be much faster than CommunicationBus
    broadcast for in-process coordination.
    """

    TTL_SECONDS: float = 30.0
    MAX_QUEUE_SIZE: int = 100

    def __init__(self) -> None:
        self._mailboxes: dict[str, asyncio.Queue[MailboxMessage]] = {}
        self._running = True
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "broadcasts_sent": 0,
        }

    async def send_message(
        self,
        to: str,
        message: str | StructuredMessage,
        summary: str | None,
        from_agent: str,
        color: str | None = None,
    ) -> bool:
        """Send a message to a specific agent.

        Args:
            to: Agent ID or name to send to
            message: Plain text or StructuredMessage
            summary: Optional 5-10 word summary
            from_agent: Sender agent ID or name
            color: Optional sender color for UI

        Returns:
            True if message was queued successfully
        """
        if not self._running:
            _logger.warning("mailbox_not_running", action="send_message")
            return False

        # Convert StructuredMessage to string if needed
        if isinstance(message, StructuredMessage):
            import json
            message = json.dumps({
                "type": message.type,
                "request_id": message.request_id,
                "approve": message.approve,
                "reason": message.reason,
                "feedback": message.feedback,
            })

        if to not in self._mailboxes:
            self._mailboxes[to] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)

        mailbox_message = MailboxMessage(
            from_agent=from_agent,
            text=message,
            summary=summary,
            timestamp=datetime.now().isoformat(),
            color=color,
        )

        try:
            await asyncio.wait_for(
                self._mailboxes[to].put(mailbox_message),
                timeout=1.0,
            )
            self._stats["messages_sent"] += 1
            _logger.debug(
                "message_sent",
                to=to,
                from_agent=from_agent,
                summary=summary,
            )
            return True
        except asyncio.TimeoutError:
            _logger.warning("mailbox_full", to=to)
            return False

    async def broadcast(
        self,
        message: str,
        summary: str | None,
        from_agent: str,
        team_name: str | None,
        color: str | None = None,
        team_members: list[str] | None = None,
    ) -> list[str]:
        """Broadcast a message to all team members.

        Args:
            message: Plain text message
            summary: Optional 5-10 word summary
            from_agent: Sender agent ID or name
            team_name: Team name (for future use with TeamContext)
            color: Optional sender color for UI
            team_members: Optional list of member IDs to broadcast to

        Returns:
            List of recipient IDs that received the message
        """
        if not team_members:
            _logger.warning("broadcast_no_members", team_name=team_name)
            return []

        recipients = []
        for member_id in team_members:
            if member_id.lower() == from_agent.lower():
                continue  # Don't send to self

            success = await self.send_message(
                to=member_id,
                message=message,
                summary=summary,
                from_agent=from_agent,
                color=color,
            )
            if success:
                recipients.append(member_id)

        self._stats["broadcasts_sent"] += 1
        _logger.info(
            "broadcast_sent",
            from_agent=from_agent,
            recipients=recipients,
            count=len(recipients),
        )
        return recipients

    async def receive_message(self, agent_id: str, timeout: float = 5.0) -> MailboxMessage | None:
        """Receive a message from the agent's inbox.

        Args:
            agent_id: Agent ID to receive for
            timeout: Max time to wait for a message

        Returns:
            MailboxMessage if available, None if timeout or no message
        """
        if not self._running:
            return None

        if agent_id not in self._mailboxes:
            return None

        try:
            message = await asyncio.wait_for(
                self._mailboxes[agent_id].get(),
                timeout=timeout,
            )
            self._stats["messages_received"] += 1
            _logger.debug(
                "message_received",
                agent_id=agent_id,
                from_agent=message.from_agent,
                summary=message.summary,
            )
            return message
        except asyncio.TimeoutError:
            return None

    async def register_agent(self, agent_id: str) -> None:
        """Register an agent (create their inbox)."""
        if agent_id not in self._mailboxes:
            self._mailboxes[agent_id] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
            _logger.debug("agent_registered", agent_id=agent_id)

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent (remove their inbox)."""
        if agent_id in self._mailboxes:
            del self._mailboxes[agent_id]
            _logger.debug("agent_unregistered", agent_id=agent_id)

    def get_stats(self) -> dict[str, Any]:
        """Get mailbox statistics."""
        return {
            **self._stats,
            "active_mailboxes": len(self._mailboxes),
            "running": self._running,
        }

    async def shutdown(self) -> None:
        """Shutdown the mailbox (cleanup)."""
        self._running = False
        self._mailboxes.clear()
        _logger.info("mailbox_shutdown", stats=self._stats)


# Global singleton instance
_global_mailbox: AgentMailbox | None = None


def get_agent_mailbox() -> AgentMailbox:
    """Get the global AgentMailbox instance."""
    global _global_mailbox
    if _global_mailbox is None:
        _global_mailbox = AgentMailbox()
    return _global_mailbox


def set_agent_mailbox(mailbox: AgentMailbox) -> None:
    """Set a custom AgentMailbox instance (for testing)."""
    global _global_mailbox
    _global_mailbox = mailbox
