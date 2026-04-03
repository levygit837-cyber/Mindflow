"""Testes para integração de synthetic errors com StreamingToolExecutor."""

import pytest

from mindflow_backend.schemas.tools.errors import (
    ErrorReason,
    SyntheticError,
    create_permission_denied_error,
    create_sibling_error,
    create_timeout_error,
    create_tool_not_found_error,
    create_user_interrupted_error,
)


class TestSyntheticErrorIntegration:
    """Testes para integração de erros sintéticos com o executor."""

    def test_user_interrupted_to_tool_result(self):
        """Testa conversão de user interrupted para ToolResult."""
        error = create_user_interrupted_error("tool-1", "TestTool")
        result = error.to_tool_result()

        assert result.is_error is True
        assert "❌" in result.content
        assert result.metadata["error_reason"] == "user_interrupted"
        assert result.metadata["synthetic"] is True

    def test_sibling_error_to_tool_result(self):
        """Testa conversão de sibling error para ToolResult."""
        error = create_sibling_error("tool-1", "Write", "Bash")
        result = error.to_tool_result()

        assert result.is_error is True
        assert "⚠️" in result.content
        assert "irmã" in result.content
        assert result.metadata["error_reason"] == "sibling_error"

    def test_permission_denied_to_tool_result(self):
        """Testa conversão de permission denied para ToolResult."""
        error = create_permission_denied_error(
            "tool-1",
            "TestTool",
            "Policy blocked",
        )
        result = error.to_tool_result()

        assert result.is_error is True
        assert "🔒" in result.content
        assert "Policy blocked" in result.content
        assert result.metadata["error_reason"] == "permission_denied"

    def test_timeout_to_tool_result(self):
        """Testa conversão de timeout para ToolResult."""
        error = create_timeout_error("tool-1", "TestTool", 60.0)
        result = error.to_tool_result()

        assert result.is_error is True
        assert "⏱️" in result.content
        assert "60s" in result.content
        assert result.metadata["error_reason"] == "timeout"

    def test_tool_not_found_to_tool_result(self):
        """Testa conversão de tool not found para ToolResult."""
        error = create_tool_not_found_error("tool-1", "MissingTool")
        result = error.to_tool_result()

        assert result.is_error is True
        assert "❓" in result.content
        assert "MissingTool" in result.content
        assert result.metadata["error_reason"] == "tool_not_found"


class TestErrorContextPropagation:
    """Testes para propagação de contexto nos erros."""

    def test_sibling_error_context(self):
        """Testa contexto do sibling error."""
        error = create_sibling_error("tool-1", "Write", "Bash")
        assert error.context["failed_tool"] == "Bash"

    def test_permission_denied_context(self):
        """Testa contexto do permission denied."""
        error = create_permission_denied_error(
            "tool-1",
            "TestTool",
            "Blocked by admin",
        )
        assert error.context["reason"] == "Blocked by admin"

    def test_timeout_context(self):
        """Testa contexto do timeout."""
        error = create_timeout_error("tool-1", "TestTool", 120.0)
        assert error.context["timeout_seconds"] == 120.0


class TestErrorMessageConsistency:
    """Testes para consistência de mensagens de erro."""

    def test_all_errors_have_tool_name(self):
        """Testa que todos os erros mencionam o nome da ferramenta."""
        errors = [
            create_user_interrupted_error("tool-1", "MyTool"),
            create_sibling_error("tool-1", "MyTool", "Other"),
            create_timeout_error("tool-1", "MyTool", 30),
            create_permission_denied_error("tool-1", "MyTool"),
            create_tool_not_found_error("tool-1", "MyTool"),
        ]

        for error in errors:
            assert "MyTool" in error.message

    def test_all_errors_have_emoji(self):
        """Testa que todos os erros têm emoji."""
        errors = [
            create_user_interrupted_error("tool-1", "Test"),
            create_sibling_error("tool-1", "Test", "Other"),
            create_timeout_error("tool-1", "Test", 30),
            create_permission_denied_error("tool-1", "Test"),
            create_tool_not_found_error("tool-1", "Test"),
        ]

        for error in errors:
            assert error.message[0] in "❌⚠️🔄⏱️🔒❓🛑📝📊"

    def test_error_messages_are_strings(self):
        """Testa que todas as mensagens são strings."""
        for reason in ErrorReason:
            error = SyntheticError(
                reason=reason,
                tool_id="tool-1",
                tool_name="Test",
                context={"timeout_seconds": 30, "size": 1000, "max_size": 500},
            )
            assert isinstance(error.message, str)
            assert len(error.message) > 0


class TestErrorMetadata:
    """Testes para metadata dos erros."""

    def test_tool_result_metadata_has_all_fields(self):
        """Testa que ToolResult tem todos os campos de metadata."""
        error = create_user_interrupted_error("tool-1", "TestTool")
        result = error.to_tool_result()

        assert "error_reason" in result.metadata
        assert "tool_id" in result.metadata
        assert "tool_name" in result.metadata
        assert "synthetic" in result.metadata

    def test_tool_result_metadata_values(self):
        """Testa valores da metadata do ToolResult."""
        error = create_sibling_error("tool-1", "Write", "Bash")
        result = error.to_tool_result()

        assert result.metadata["error_reason"] == "sibling_error"
        assert result.metadata["tool_id"] == "tool-1"
        assert result.metadata["tool_name"] == "Write"
        assert result.metadata["synthetic"] is True

    def test_tool_result_is_always_error(self):
        """Testa que ToolResult de erro sintético é sempre is_error=True."""
        for reason in ErrorReason:
            error = SyntheticError(
                reason=reason,
                tool_id="tool-1",
                tool_name="Test",
                context={"timeout_seconds": 30, "size": 1000, "max_size": 500},
            )
            result = error.to_tool_result()
            assert result.is_error is True


class TestErrorReasonMapping:
    """Testes para mapeamento de razões de erro."""

    def test_reason_to_emoji_mapping(self):
        """Testa mapeamento de razão para emoji."""
        expected = {
            ErrorReason.USER_INTERRUPTED: "❌",
            ErrorReason.SIBLING_ERROR: "⚠️",
            ErrorReason.STREAMING_FALLBACK: "🔄",
            ErrorReason.TIMEOUT: "⏱️",
            ErrorReason.PERMISSION_DENIED: "🔒",
            ErrorReason.TOOL_NOT_FOUND: "❓",
            ErrorReason.EXECUTION_ABORTED: "🛑",
            ErrorReason.INVALID_INPUT: "📝",
            ErrorReason.RESULT_TOO_LARGE: "📊",
        }

        for reason, emoji in expected.items():
            error = SyntheticError(
                reason=reason,
                tool_id="tool-1",
                tool_name="Test",
                context={"timeout_seconds": 30, "size": 1000, "max_size": 500},
            )
            assert error.message.startswith(emoji)