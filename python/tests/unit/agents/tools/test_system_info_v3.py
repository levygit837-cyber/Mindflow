"""Unit tests for SystemInfoToolV3."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.agents.tools.system.system_info_v3 import (
    SystemInfoInput,
    SystemInfoToolV3,
    system_info_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.mark.asyncio
async def test_system_info_all(mock_tool_context):
    """Test collecting all system information."""
    input_data = SystemInfoInput(
        info_type="all",
        include_sensitive=False
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert "timestamp" in result
    assert "hardware" in result
    assert "software" in result
    assert "network" in result
    assert "environment" in result


@pytest.mark.asyncio
async def test_system_info_hardware_only(mock_tool_context):
    """Test collecting only hardware information."""
    input_data = SystemInfoInput(
        info_type="hardware"
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert "hardware" in result
    assert "software" not in result
    assert "network" not in result


@pytest.mark.asyncio
async def test_system_info_software_only(mock_tool_context):
    """Test collecting only software information."""
    input_data = SystemInfoInput(
        info_type="software"
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert "software" in result
    assert "hardware" not in result


@pytest.mark.asyncio
async def test_system_info_network_only(mock_tool_context):
    """Test collecting only network information."""
    input_data = SystemInfoInput(
        info_type="network"
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert "network" in result
    assert "hardware" not in result


@pytest.mark.asyncio
async def test_system_info_environment_only(mock_tool_context):
    """Test collecting only environment information."""
    input_data = SystemInfoInput(
        info_type="environment"
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert "environment" in result
    assert "hardware" not in result


@pytest.mark.asyncio
async def test_system_info_hardware_structure(mock_tool_context):
    """Test hardware information structure."""
    input_data = SystemInfoInput(
        info_type="hardware"
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    hardware = result["hardware"]
    assert "system" in hardware
    assert "platform" in hardware["system"]
    assert "hostname" in hardware["system"]


@pytest.mark.asyncio
async def test_system_info_software_structure(mock_tool_context):
    """Test software information structure."""
    input_data = SystemInfoInput(
        info_type="software"
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    software = result["software"]
    assert "python" in software
    assert "os" in software
    assert "version" in software["python"]


@pytest.mark.asyncio
async def test_system_info_environment_without_sensitive(mock_tool_context):
    """Test environment info without sensitive variables."""
    input_data = SystemInfoInput(
        info_type="environment",
        include_sensitive=False
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    env = result["environment"]
    assert "user" in env
    assert "working_directory" in env
    assert "variables" in env


@pytest.mark.asyncio
async def test_system_info_environment_with_sensitive(mock_tool_context):
    """Test environment info with sensitive variables masked."""
    # Set a sensitive env var
    os.environ["TEST_API_KEY"] = "secret123"

    input_data = SystemInfoInput(
        info_type="environment",
        include_sensitive=True
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    env = result["environment"]

    # Check that sensitive vars are masked
    if "TEST_API_KEY" in env["variables"]:
        assert env["variables"]["TEST_API_KEY"] == "***HIDDEN***"

    # Cleanup
    del os.environ["TEST_API_KEY"]


@pytest.mark.asyncio
async def test_system_info_timestamp(mock_tool_context):
    """Test that timestamp is included."""
    input_data = SystemInfoInput(
        info_type="all"
    )

    result = await system_info_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert "timestamp" in result
    assert isinstance(result["timestamp"], float)
