"""Communication Bus — Camada de transporte unificada para agentes."""

from .communication_bus import (
    CommunicationBus,
    InternalCommunicationBus,
    get_communication_bus,
    set_communication_bus,
)

__all__ = [
    "CommunicationBus",
    "InternalCommunicationBus",
    "get_communication_bus",
    "set_communication_bus",
]