"""Unit tests for ResourceMonitorToolV3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.agents.tools.system.resource_monitor_v3 import (
    ResourceMonitorInput,
    ResourceMonitorToolV3,
    resource_monitor_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.mark.asyncio
async def test_resource_monitor_get_current(mock_tool_context):
    """Test getting current resource usage."""
    with patch('psutil.cpu_percent') as mock_cpu_percent, \
         patch('psutil.cpu_count') as mock_cpu_count, \
         patch('psutil.cpu_freq') as mock_cpu_freq, \
         patch('psutil.getloadavg') as mock_getloadavg, \
         patch('psutil.virtual_memory') as mock_virtual_memory, \
         patch('psutil.swap_memory') as mock_swap_memory:

        # Mock CPU
        mock_cpu_percent.return_value = 50.0
        mock_cpu_count.return_value = 4
        mock_cpu_freq.return_value = MagicMock(current=2400, min=800, max=3200)
        mock_getloadavg.return_value = (1.5, 1.2, 1.0)

        # Mock memory
        mock_memory = MagicMock(total=8000000000, available=4000000000, used=4000000000, percent=50.0)
        mock_swap = MagicMock(total=2000000000, used=500000000, free=1500000000, percent=25.0)
        mock_virtual_memory.return_value = mock_memory
        mock_swap_memory.return_value = mock_swap

        input_data = ResourceMonitorInput(
            action="get_current",
            resources=["cpu", "memory"]
        )

        result = await resource_monitor_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["action"] == "get_current"
        assert "current" in result
        assert "cpu" in result["current"]
        assert "memory" in result["current"]
        assert result["current"]["cpu"]["percentage"] == 50.0


@pytest.mark.asyncio
async def test_resource_monitor_get_current_disk(mock_tool_context):
    """Test getting current disk usage."""
    with patch('psutil.disk_partitions') as mock_disk_partitions, \
         patch('psutil.disk_usage') as mock_disk_usage:

        # Mock disk
        mock_partition = MagicMock(mountpoint="/", device="/dev/sda1", fstype="ext4")
        mock_disk_partitions.return_value = [mock_partition]
        mock_usage = MagicMock(total=100000000000, used=50000000000, free=50000000000)
        mock_disk_usage.return_value = mock_usage

        input_data = ResourceMonitorInput(
            action="get_current",
            resources=["disk"]
        )

        result = await resource_monitor_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert "disk" in result["current"]
        assert "/" in result["current"]["disk"]


@pytest.mark.asyncio
async def test_resource_monitor_get_current_network(mock_tool_context):
    """Test getting current network usage."""
    with patch('psutil.net_io_counters') as mock_net_io_counters:
        # Mock network
        mock_net = MagicMock(
            bytes_sent=1000000,
            bytes_recv=2000000,
            packets_sent=1000,
            packets_recv=2000,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0
        )
        mock_net_io_counters.return_value = mock_net

        input_data = ResourceMonitorInput(
            action="get_current",
            resources=["network"]
        )

        result = await resource_monitor_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert "network" in result["current"]
        assert result["current"]["network"]["bytes_sent"] == 1000000


@pytest.mark.asyncio
async def test_resource_monitor_start(mock_tool_context):
    """Test starting resource monitoring."""
    input_data = ResourceMonitorInput(
        action="start",
        resources=["cpu", "memory"],
        duration=60,
        interval=5
    )

    result = await resource_monitor_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["action"] == "start"
    assert result["monitoring"] is True
    assert result["resources"] == ["cpu", "memory"]
    assert result["duration"] == 60
    assert result["interval"] == 5


@pytest.mark.asyncio
async def test_resource_monitor_stop(mock_tool_context):
    """Test stopping resource monitoring."""
    # First start monitoring
    start_input = ResourceMonitorInput(
        action="start",
        resources=["cpu"],
        duration=60
    )
    await resource_monitor_execute(start_input, mock_tool_context)

    # Then stop
    stop_input = ResourceMonitorInput(
        action="stop"
    )

    result = await resource_monitor_execute(stop_input, mock_tool_context)

    assert result["success"] is True
    assert result["action"] == "stop"
    assert result["monitoring"] is False


@pytest.mark.asyncio
async def test_resource_monitor_stop_not_started(mock_tool_context):
    """Test stopping when monitoring not started."""
    # Reset monitoring state
    from mindflow_backend.agents.tools.system.resource_monitor_v3 import _monitoring_state
    _monitoring_state["active"] = False

    input_data = ResourceMonitorInput(
        action="stop"
    )

    result = await resource_monitor_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "NOT_MONITORING"


@pytest.mark.asyncio
async def test_resource_monitor_get_history(mock_tool_context):
    """Test getting resource history."""
    # Add some mock history
    from mindflow_backend.agents.tools.system.resource_monitor_v3 import _monitoring_state
    _monitoring_state["history"]["cpu"] = [
        {"value": 50.0, "timestamp": 1234567890.0},
        {"value": 60.0, "timestamp": 1234567895.0}
    ]

    input_data = ResourceMonitorInput(
        action="get_history",
        resources=["cpu"]
    )

    result = await resource_monitor_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["action"] == "get_history"
    assert "history" in result
    assert "cpu" in result["history"]
    assert len(result["history"]["cpu"]) == 2


@pytest.mark.asyncio
async def test_resource_monitor_with_alert_conditions(mock_tool_context):
    """Test monitoring with custom alert thresholds."""
    input_data = ResourceMonitorInput(
        action="start",
        resources=["cpu"],
        alert_conditions={"cpu": 90.0, "memory": 95.0}
    )

    result = await resource_monitor_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["monitoring"] is True


@pytest.mark.asyncio
async def test_resource_monitor_unknown_action(mock_tool_context):
    """Test unknown action."""
    input_data = ResourceMonitorInput(
        action="unknown"
    )

    result = await resource_monitor_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "UNKNOWN_ACTION"
