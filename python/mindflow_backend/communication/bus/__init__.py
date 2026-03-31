"""Communication Bus — Camada de transporte unificada para agentes."""

from .communication_bus import (
    CommunicationBus,
    InternalCommunicationBus,
    get_communication_bus,
    set_communication_bus,
)
from .xmpp_bus import (
    MINDFLOW_MUC_DOMAIN,
    MINDFLOW_XMPP_DOMAIN,
    DEFAULT_AGENT_PASSWORD,
    XMPPCommunicationBus,
)

__all__ = [
    "CommunicationBus",
    "InternalCommunicationBus",
    "XMPPCommunicationBus",
    "MINDFLOW_XMPP_DOMAIN",
    "MINDFLOW_MUC_DOMAIN",
    "DEFAULT_AGENT_PASSWORD",
    "get_communication_bus",
    "set_communication_bus",
]
