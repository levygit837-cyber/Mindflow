"""Tests for InternalCommunicationBus."""

import asyncio

import pytest

from mindflow_backend.communication.bus.communication_bus import (
    InternalCommunicationBus,
    get_communication_bus,
    set_communication_bus,
)
from mindflow_backend.communication.protocols.p2p_protocol import (
    MessageType,
    P2PMessage,
)
from mindflow_backend.communication.teams.team_chat import TeamMessage


@pytest.fixture
def bus():
    """Create a fresh bus for each test."""
    return InternalCommunicationBus()


@pytest.fixture
def sample_message():
    """Create a sample P2P message."""
    return P2PMessage(
        from_agent="coder",
        to_agent="analyst",
        content="Encontrei padrão arquitetural suspeito",
        message_type=MessageType.REQUEST,
        urgency="HIGH",
    )


@pytest.mark.asyncio
async def test_register_agent(bus: InternalCommunicationBus):
    """Test agent registration."""
    await bus.register_agent("analyst")
    assert "analyst" in bus._inboxes
    assert bus._stats["agents_registered"] == 1


@pytest.mark.asyncio
async def test_register_duplicate_agent(bus: InternalCommunicationBus):
    """Test that registering the same agent twice doesn't duplicate."""
    await bus.register_agent("analyst")
    await bus.register_agent("analyst")
    assert bus._stats["agents_registered"] == 1


@pytest.mark.asyncio
async def test_unregister_agent(bus: InternalCommunicationBus):
    """Test agent unregistration."""
    await bus.register_agent("analyst")
    await bus.unregister_agent("analyst")
    assert "analyst" not in bus._inboxes


@pytest.mark.asyncio
async def test_send_and_receive(
    bus: InternalCommunicationBus, sample_message: P2PMessage
):
    """Test sending and receiving a message."""
    await bus.register_agent("coder")
    await bus.register_agent("analyst")

    sent = await bus.send("coder", "analyst", sample_message)
    assert sent is True
    assert bus._stats["messages_sent"] == 1

    received = await bus.receive("analyst", timeout=1.0)
    assert received is not None
    assert received.content == "Encontrei padrão arquitetural suspeito"
    assert received.from_agent == "coder"


@pytest.mark.asyncio
async def test_send_to_unknown_agent(
    bus: InternalCommunicationBus, sample_message: P2PMessage
):
    """Test sending to an unregistered agent returns False."""
    await bus.register_agent("coder")

    sent = await bus.send("coder", "unknown_agent", sample_message)
    assert sent is False
    assert bus._stats["messages_dropped"] == 1


@pytest.mark.asyncio
async def test_queue_full_drops_message(bus: InternalCommunicationBus):
    """Test that a full queue drops the message."""
    bus.MAX_QUEUE_SIZE = 2
    await bus.register_agent("coder")
    await bus.register_agent("analyst")

    for i in range(3):
        msg = P2PMessage(
            from_agent="coder",
            to_agent="analyst",
            content=f"Message {i}",
            message_type=MessageType.DIRECT,
        )
        await bus.send("coder", "analyst", msg)

    assert bus._stats["messages_dropped"] == 1


@pytest.mark.asyncio
async def test_broadcast_to_room(bus: InternalCommunicationBus):
    """Test broadcasting to a room."""
    await bus.register_agent("orchestrator")
    await bus.register_agent("analyst")
    await bus.register_agent("coder")

    bus.join_room("analyst", "team-alpha")
    bus.join_room("coder", "team-alpha")

    team_msg = TeamMessage(
        sender_jid="orchestrator",
        team_id="team-alpha",
        content="Iniciando missão colaborativa",
    )

    delivered = await bus.broadcast("orchestrator", "team-alpha", team_msg)
    assert delivered is True

    analyst_msg = await bus.receive("analyst", timeout=1.0)
    coder_msg = await bus.receive("coder", timeout=1.0)

    assert analyst_msg is not None
    assert analyst_msg.content == "Iniciando missão colaborativa"
    assert coder_msg is not None
    assert coder_msg.content == "Iniciando missão colaborativa"


@pytest.mark.asyncio
async def test_broadcast_no_subscribers(bus: InternalCommunicationBus):
    """Test broadcast to empty room returns False."""
    await bus.register_agent("orchestrator")

    team_msg = TeamMessage(
        sender_jid="orchestrator",
        team_id="empty-room",
        content="Test",
    )

    delivered = await bus.broadcast("orchestrator", "empty-room", team_msg)
    assert delivered is False


@pytest.mark.asyncio
async def test_subscribe_handler(bus: InternalCommunicationBus, sample_message: P2PMessage):
    """Test message handler subscription."""
    received_messages = []

    async def handler(msg: P2PMessage) -> None:
        received_messages.append(msg)

    await bus.register_agent("analyst")
    await bus.subscribe("analyst", handler)
    await bus.register_agent("coder")

    await bus.send("coder", "analyst", sample_message)

    await asyncio.sleep(0.1)
    assert len(received_messages) == 1
    assert received_messages[0].content == sample_message.content


@pytest.mark.asyncio
async def test_health_check(bus: InternalCommunicationBus):
    """Test health check returns correct info."""
    await bus.register_agent("analyst")
    await bus.register_agent("coder")

    health = await bus.health_check()
    assert health["type"] == "internal"
    assert health["available"] is True
    assert "analyst" in health["agents"]
    assert "coder" in health["agents"]
    assert health["stats"]["agents_registered"] == 2


@pytest.mark.asyncio
async def test_is_available(bus: InternalCommunicationBus):
    """Test is_available property."""
    assert bus.is_available is True


@pytest.mark.asyncio
async def test_singleton_get_communication_bus():
    """Test that get_communication_bus returns singleton."""
    bus1 = get_communication_bus()
    bus2 = get_communication_bus()
    assert bus1 is bus2


@pytest.mark.asyncio
async def test_set_communication_bus():
    """Test replacing global bus."""
    original = get_communication_bus()
    new_bus = InternalCommunicationBus()
    set_communication_bus(new_bus)
    assert get_communication_bus() is new_bus
    set_communication_bus(original)


@pytest.mark.asyncio
async def test_join_leave_room(bus: InternalCommunicationBus):
    """Test room join and leave."""
    await bus.register_agent("analyst")

    bus.join_room("analyst", "team-alpha")
    assert "analyst" in bus._room_subscribers["team-alpha"]

    bus.leave_room("analyst", "team-alpha")
    assert "analyst" not in bus._room_subscribers["team-alpha"]


@pytest.mark.asyncio
async def test_receive_no_inbox(bus: InternalCommunicationBus):
    """Test receive on unregistered agent returns None."""
    result = await bus.receive("unknown", timeout=0.1)
    assert result is None


@pytest.mark.asyncio
async def test_receive_timeout(bus: InternalCommunicationBus):
    """Test receive timeout returns None."""
    await bus.register_agent("analyst")
    result = await bus.receive("analyst", timeout=0.1)
    assert result is None