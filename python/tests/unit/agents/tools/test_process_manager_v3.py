"""Unit tests for ProcessManagerToolV3."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.agents.tools.system.process_manager_v3 import (
    ProcessManagerInput,
    ProcessManagerToolV3,
    process_manager_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.fixture
def mock_psutil_process():
    """Mock psutil.Process."""
    process = MagicMock()
    process.pid = 1234
    process.name.return_value = "test_process"
    process.info = {
        'pid': 1234,
        'name': 'test_process',
        'username': 'testuser',
        'cpu_percent': 10.5,
        'memory_percent': 5.2,
        'status': 'running'
    }
    process.is_running.return_value = False  # After kill
    process.cpu_percent.return_value = 10.5
    process.memory_info.return_value = MagicMock(rss=1024000, vms=2048000)
    process.memory_percent.return_value = 5.2
    process.create_time.return_value = 1234567890.0
    process.status.return_value = 'running'
    return process


@pytest.mark.asyncio
async def test_process_manager_list(mock_tool_context):
    """Test listing processes."""
    with patch('psutil.process_iter') as mock_process_iter:
        # Mock process_iter
        mock_proc1 = MagicMock()
        mock_proc1.info = {
            'pid': 1,
            'name': 'init',
            'username': 'root',
            'cpu_percent': 0.1,
            'memory_percent': 0.5,
            'status': 'sleeping'
        }
        mock_proc2 = MagicMock()
        mock_proc2.info = {
            'pid': 2,
            'name': 'python',
            'username': 'testuser',
            'cpu_percent': 10.0,
            'memory_percent': 5.0,
            'status': 'running'
        }
        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        input_data = ProcessManagerInput(
            action="list"
        )

        result = await process_manager_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["action"] == "list"
        assert result["count"] == 2
        assert len(result["processes"]) == 2


@pytest.mark.asyncio
async def test_process_manager_list_with_filter_name(mock_tool_context):
    """Test listing processes with name filter."""
    with patch('psutil.process_iter') as mock_process_iter:
        mock_proc1 = MagicMock()
        mock_proc1.info = {'pid': 1, 'name': 'python', 'username': 'user', 'cpu_percent': 1.0, 'memory_percent': 1.0, 'status': 'running'}
        mock_proc2 = MagicMock()
        mock_proc2.info = {'pid': 2, 'name': 'node', 'username': 'user', 'cpu_percent': 1.0, 'memory_percent': 1.0, 'status': 'running'}
        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        input_data = ProcessManagerInput(
            action="list",
            filter_name="python"
        )

        result = await process_manager_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["processes"][0]["name"] == "python"


@pytest.mark.asyncio
async def test_process_manager_list_with_filter_user(mock_tool_context):
    """Test listing processes with user filter."""
    with patch('psutil.process_iter') as mock_process_iter:
        mock_proc1 = MagicMock()
        mock_proc1.info = {'pid': 1, 'name': 'proc1', 'username': 'root', 'cpu_percent': 1.0, 'memory_percent': 1.0, 'status': 'running'}
        mock_proc2 = MagicMock()
        mock_proc2.info = {'pid': 2, 'name': 'proc2', 'username': 'testuser', 'cpu_percent': 1.0, 'memory_percent': 1.0, 'status': 'running'}
        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        input_data = ProcessManagerInput(
            action="list",
            filter_user="testuser"
        )

        result = await process_manager_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["processes"][0]["user"] == "testuser"


@pytest.mark.asyncio
async def test_process_manager_kill(mock_tool_context, mock_psutil_process):
    """Test killing a process."""
    with patch('psutil.Process') as mock_process_class:
        mock_process_class.return_value = mock_psutil_process

        input_data = ProcessManagerInput(
            action="kill",
            pid=1234,
            signal_name="SIGTERM"
        )

        result = await process_manager_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["action"] == "kill"
        assert result["pid"] == 1234
        assert result["killed"] is True


@pytest.mark.asyncio
async def test_process_manager_kill_critical_process_blocked(mock_tool_context):
    """Test that killing critical processes is blocked."""
    with patch('psutil.Process') as mock_process_class:
        mock_proc = MagicMock()
        mock_proc.name.return_value = "init"
        mock_process_class.return_value = mock_proc

        input_data = ProcessManagerInput(
            action="kill",
            pid=1
        )

        result = await process_manager_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "CRITICAL_PROCESS_BLOCKED"


@pytest.mark.asyncio
async def test_process_manager_kill_missing_pid(mock_tool_context):
    """Test killing without PID."""
    input_data = ProcessManagerInput(
        action="kill",
        pid=None
    )

    result = await process_manager_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "MISSING_PID"


@pytest.mark.asyncio
async def test_process_manager_kill_unknown_signal(mock_tool_context):
    """Test killing with unknown signal."""
    input_data = ProcessManagerInput(
        action="kill",
        pid=1234,
        signal_name="SIGUNKNOWN"
    )

    result = await process_manager_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "UNKNOWN_SIGNAL"


@pytest.mark.asyncio
async def test_process_manager_monitor(mock_tool_context, mock_psutil_process):
    """Test monitoring a process."""
    with patch('psutil.Process') as mock_process_class:
        mock_process_class.return_value = mock_psutil_process

        input_data = ProcessManagerInput(
            action="monitor",
            pid=1234
        )

        result = await process_manager_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["action"] == "monitor"
        assert result["pid"] == 1234
        assert "cpu_percent" in result
        assert "memory_percent" in result
        assert "status" in result


@pytest.mark.asyncio
async def test_process_manager_monitor_missing_pid(mock_tool_context):
    """Test monitoring without PID."""
    input_data = ProcessManagerInput(
        action="monitor",
        pid=None
    )

    result = await process_manager_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "MISSING_PID"


@pytest.mark.asyncio
async def test_process_manager_unknown_action(mock_tool_context):
    """Test unknown action."""
    input_data = ProcessManagerInput(
        action="unknown"
    )

    result = await process_manager_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "UNKNOWN_ACTION"
