"""Shared fixtures for tool tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from mindflow_backend.permissions.types import PermissionContext
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.permission import (
    PermissionBehavior,
    PermissionResult,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_file(temp_dir):
    """Create a test file with sample content."""
    file_path = temp_dir / "test.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def tool_context(temp_dir):
    """Create a basic ToolContext for testing."""
    from mindflow_backend.permissions.types import PermissionMode

    permission_context = PermissionContext(
        mode=PermissionMode.BYPASS,  # Allow all for testing
    )
    return ToolContext(
        permission_context=permission_context,
        metadata={"root_dir": str(temp_dir)},
        permission_manager=None,
        abort_signal=None,
    )


@pytest.fixture
def tool_context_with_permissions(temp_dir):
    """Create a ToolContext with mock permission manager."""
    from mindflow_backend.permissions.types import PermissionMode

    permission_context = PermissionContext(
        mode=PermissionMode.DEFAULT,
    )

    mock_permission_manager = AsyncMock()

    async def mock_check_permission(tool_name, input, context, tool_content=None, tool_use_id=None):
        # Default: allow all
        return PermissionResult(
            behavior=PermissionBehavior.ALLOW,
            reason="Test permission granted"
        )

    mock_permission_manager.check_permission = mock_check_permission

    return ToolContext(
        permission_context=permission_context,
        metadata={"root_dir": str(temp_dir)},
        permission_manager=mock_permission_manager,
        abort_signal=None,
    )


@pytest.fixture
def tool_context_deny_permissions(temp_dir):
    """Create a ToolContext that denies all permissions."""
    from mindflow_backend.permissions.types import PermissionMode

    permission_context = PermissionContext(
        mode=PermissionMode.DONT_ASK,  # Deny mode
    )

    mock_permission_manager = AsyncMock()

    async def mock_check_permission(tool_name, input, context, tool_content=None, tool_use_id=None):
        return PermissionResult(
            behavior=PermissionBehavior.DENY,
            reason="Test permission denied"
        )

    mock_permission_manager.check_permission = mock_check_permission

    return ToolContext(
        permission_context=permission_context,
        metadata={"root_dir": str(temp_dir)},
        permission_manager=mock_permission_manager,
        abort_signal=None,
    )


@pytest.fixture
def mock_tool_context(temp_dir):
    """Alias for tool_context - used by v3 tests."""
    from mindflow_backend.permissions.types import PermissionMode

    permission_context = PermissionContext(
        mode=PermissionMode.BYPASS,  # Allow all for testing
    )
    return ToolContext(
        permission_context=permission_context,
        metadata={"root_dir": str(temp_dir)},
        permission_manager=None,
        abort_signal=None,
    )
