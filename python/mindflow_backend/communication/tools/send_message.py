"""SendMessageTool — Send messages between agents using AgentMailbox.

Based on Claude Code's SendMessageTool, this provides fast in-process
communication between agents via AgentMailbox, complementing the
CommunicationBus for XMPP/Fase 4.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.communication.mailbox import get_agent_mailbox, StructuredMessage
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SendMessageTool(AsyncToolInterface):
    """Send a message to another agent using AgentMailbox.

    This tool provides fast point-to-point and broadcast messaging between
    agents using the AgentMailbox layer, which is much faster than
    CommunicationBus broadcast for in-process coordination.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "SendMessage"
        self.description = (
            "Send a message to another agent. "
            "Use this for agent coordination, task handoffs, or requesting help. "
            "Messages are delivered automatically to the recipient's inbox."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": (
                            "Recipient: teammate name, or '*' for broadcast to all teammates. "
                            "Broadcast is expensive (linear in team size), use only when everyone genuinely needs it."
                        ),
                    },
                    "summary": {
                        "type": "string",
                        "description": "A 5-10 word summary shown as a preview in the UI (required when message is a string).",
                    },
                    "message": {
                        "type": "string",
                        "description": "Plain text message content.",
                    },
                },
                "required": ["to", "message"],
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        to: str = kwargs.get("to", "")
        summary: str | None = kwargs.get("summary")
        message: str = kwargs.get("message", "")

        if not to:
            return "Error: 'to' parameter is required."
        if not message:
            return "Error: 'message' parameter is required."

        _logger.info(
            "send_message_tool_invoked",
            to=to,
            summary=summary,
            message_length=len(message),
        )

        try:
            mailbox = get_agent_mailbox()
            from_agent = self.agent_id or "orchestrator"

            if to == "*":
                # Broadcast to all team members
                # Note: This is a simplified implementation. In a full implementation,
                # you would fetch team members from TeamContext.
                recipients = await mailbox.broadcast(
                    message=message,
                    summary=summary,
                    from_agent=from_agent,
                    team_name=None,  # Would be fetched from TeamContext
                    team_members=None,  # Would be fetched from TeamContext
                )
                return f"Message broadcast to {len(recipients)} teammate(s): {', '.join(recipients) if recipients else 'none'}"
            else:
                # Send to specific agent
                success = await mailbox.send_message(
                    to=to,
                    message=message,
                    summary=summary,
                    from_agent=from_agent,
                )
                if success:
                    return f"Message sent to {to}'s inbox"
                else:
                    return f"Failed to send message to {to} (mailbox full or unavailable)"

        except Exception as exc:
            _logger.error(f"send_message_tool_error: {exc}")
            return f"Error sending message: {exc}"
