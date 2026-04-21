"""AgentMailbox — Fast in-process communication layer for agents."""

from .agent_mailbox import (
    AgentMailbox,
    MailboxMessage,
    StructuredMessage,
    get_agent_mailbox,
    set_agent_mailbox,
)

__all__ = [
    "AgentMailbox",
    "MailboxMessage",
    "StructuredMessage",
    "get_agent_mailbox",
    "set_agent_mailbox",
]
