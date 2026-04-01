"""
Testes de integração do Memory Observer com TeamOrchestrator.

Fase 3B — SPADE Memory Observer Protocol
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.execution.observers.memory_observer import MemoryObserver
from mindflow_backend.runtime.monitoring.log_bus import AgentLogBus


@pytest.fixture
def mock_memory_facade():
    """Mock do MemoryFacade."""
    facade = MagicMock()
    facade.save_annotation = AsyncMock()
    return facade


@pytest.fixture
def log_bus():
    """Instância limpa do AgentLogBus para cada teste."""
    return AgentLogBus()


@pytest.mark.asyncio
async def test_memory_observer_receives_events_from_log_bus(
    mock_memory_facade,
    log_bus,
):
    """Testa que MemoryObserver recebe eventos via AgentLogBus."""
    observer = MemoryObserver(
        observer_agent_id="observer-1",
        memory_facade=mock_memory_facade,
        session_id="test-session-123",
    )

    # Iniciar observação
    await observer.start_observing(["mission-alpha"])

    # Registrar no log_bus
    log_bus.subscribe_to_mission(
        mission_id="mission-alpha",
        observer_id="observer-1",
        handler=observer.receive_event,
    )

    # Simular evento importante
    important_event = {
        "type": "finding",
        "agent_id": "coder-1",
        "mission_id": "mission-alpha",
        "level": "WARNING",
        "message": "SQL injection pattern detected in auth.py",
        "data": {"file": "auth.py", "pattern": "f-string SQL"},
    }

    # Publicar evento via log_bus
    await log_bus._notify_observers("mission-alpha", important_event)

    # Aguardar processamento
    await asyncio.sleep(0.1)

    # Verificar que observer processou o evento
    stats = observer.get_stats()
    assert stats["running"] is True
    assert "mission-alpha" in stats["observed_missions"]

    # Parar observer
    await observer.stop_observing()


@pytest.mark.asyncio
async def test_memory_observer_filters_low_importance_events(
    mock_memory_facade,
    log_bus,
):
    """Testa que eventos de baixa importância são filtrados."""
    observer = MemoryObserver(
        observer_agent_id="observer-2",
        memory_facade=mock_memory_facade,
        session_id="test-session-456",
    )

    await observer.start_observing(["mission-beta"])

    log_bus.subscribe_to_mission(
        mission_id="mission-beta",
        observer_id="observer-2",
        handler=observer.receive_event,
    )

    # Evento de baixa importância (DEBUG)
    low_importance_event = {
        "type": "progress",
        "agent_id": "analyst-1",
        "mission_id": "mission-beta",
        "level": "DEBUG",
        "message": "Step 3/10 completed",
        "data": {},
    }

    await log_bus._notify_observers("mission-beta", low_importance_event)
    await asyncio.sleep(0.1)

    # save_annotation NÃO deve ter sido chamado
    mock_memory_facade.save_annotation.assert_not_called()

    await observer.stop_observing()


@pytest.mark.asyncio
async def test_memory_observer_saves_important_annotations(
    mock_memory_facade,
    log_bus,
):
    """Testa que eventos importantes geram anotações de memória."""
    observer = MemoryObserver(
        observer_agent_id="observer-3",
        memory_facade=mock_memory_facade,
        session_id="test-session-789",
    )

    await observer.start_observing(["mission-gamma"])

    log_bus.subscribe_to_mission(
        mission_id="mission-gamma",
        observer_id="observer-3",
        handler=observer.receive_event,
    )

    # Evento importante (ERROR)
    important_event = {
        "type": "tool_result",
        "agent_id": "security-1",
        "mission_id": "mission-gamma",
        "level": "ERROR",
        "message": "Critical vulnerability found",
        "data": {"vulnerability": "XSS", "file": "index.html"},
    }

    await log_bus._notify_observers("mission-gamma", important_event)
    await asyncio.sleep(0.2)

    # save_annotation DEVE ter sido chamado
    mock_memory_facade.save_annotation.assert_called_once()

    # Verificar que a anotação tem os campos corretos
    call_args = mock_memory_facade.save_annotation.call_args
    annotation = call_args[0][0]
    assert annotation.observer_agent_id == "observer-3"
    assert annotation.source_agent_id == "security-1"
    assert annotation.mission_id == "mission-gamma"
    assert annotation.session_id == "test-session-789"
    assert annotation.importance >= 0.7  # ERROR events têm alta importância

    await observer.stop_observing()


@pytest.mark.asyncio
async def test_log_bus_subscription_and_unsubscription(log_bus):
    """Testa subscribe e unsubscribe no AgentLogBus."""
    handler1 = AsyncMock()
    handler2 = AsyncMock()

    # Subscribe
    log_bus.subscribe_to_mission("mission-1", "obs-1", handler1)
    log_bus.subscribe_to_mission("mission-1", "obs-2", handler2)

    stats1 = log_bus.get_observer_stats("obs-1")
    assert "mission-1" in stats1["subscribed_missions"]

    # Notificar
    await log_bus._notify_observers("mission-1", {"type": "test"})
    handler1.assert_called_once()
    handler2.assert_called_once()

    # Unsubscribe
    log_bus.unsubscribe_from_mission("mission-1", "obs-1", handler1)

    # Notificar novamente — só handler2 deve receber
    handler1.reset_mock()
    handler2.reset_mock()
    await log_bus._notify_observers("mission-1", {"type": "test2"})
    handler1.assert_not_called()
    handler2.assert_called_once()


@pytest.mark.asyncio
async def test_memory_observer_rate_limiting(
    mock_memory_facade,
    log_bus,
):
    """Testa rate limiting de anotações (máx 10/min)."""
    observer = MemoryObserver(
        observer_agent_id="observer-4",
        memory_facade=mock_memory_facade,
        session_id="test-session-rate",
    )

    await observer.start_observing(["mission-rate"])

    log_bus.subscribe_to_mission(
        mission_id="mission-rate",
        observer_id="observer-4",
        handler=observer.receive_event,
    )

    # Enviar 15 eventos importantes rapidamente
    for i in range(15):
        event = {
            "type": "finding",
            "agent_id": f"agent-{i}",
            "mission_id": "mission-rate",
            "level": "ERROR",
            "message": f"Finding {i}",
            "data": {},
        }
        await log_bus._notify_observers("mission-rate", event)

    await asyncio.sleep(0.5)

    # Máximo de 10 anotações por minuto
    assert mock_memory_facade.save_annotation.call_count <= 10

    await observer.stop_observing()


@pytest.mark.asyncio
async def test_memory_observer_graceful_stop(
    mock_memory_facade,
    log_bus,
):
    """Testa parada graceful do observer."""
    observer = MemoryObserver(
        observer_agent_id="observer-5",
        memory_facade=mock_memory_facade,
        session_id="test-session-stop",
    )

    await observer.start_observing(["mission-stop"])

    log_bus.subscribe_to_mission(
        mission_id="mission-stop",
        observer_id="observer-5",
        handler=observer.receive_event,
    )

    # Parar observer
    await observer.stop_observing()

    stats = observer.get_stats()
    assert stats["running"] is False

    # Eventos após stop devem ser ignorados
    event = {
        "type": "finding",
        "agent_id": "agent-1",
        "mission_id": "mission-stop",
        "level": "ERROR",
        "message": "Should be ignored",
        "data": {},
    }
    await log_bus._notify_observers("mission-stop", event)
    await asyncio.sleep(0.1)

    # Não deve ter salvo nada após stop
    mock_memory_facade.save_annotation.assert_not_called()