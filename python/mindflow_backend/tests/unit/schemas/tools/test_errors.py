"""Testes para o módulo de synthetic errors."""

import pytest

from mindflow_backend.schemas.tools.errors import (
    ErrorReason,
    SyntheticError,
    create_execution_aborted_error,
    create_invalid_input_error,
    create_permission_denied_error,
    create_result_too_large_error,
    create_sibling_error,
    create_streaming_fallback_error,
    create_timeout_error,
    create_tool_not_found_error,
    create_user_interrupted_error,
)
from mindflow_backend.schemas.tools.result import TruncationReason


class TestErrorReason:
    """Testes para ErrorReason enum."""

    def test_all_reasons_exist(self):
        """Testa que todas as razões existem."""
        expected = [
            "user_interrupted",
            "sibling_error",
            "streaming_fallback",
            "timeout",
            "permission_denied",
            "tool_not_found",
            "execution_aborted",
            "invalid_input",
            "result_too_large",
        ]
        actual = [r.value for r in ErrorReason]
        assert sorted(actual) == sorted(expected)

    def test_enum_values(self):
        """Testa valores dos enums."""
        assert ErrorReason.USER_INTERRUPTED.value == "user_interrupted"
        assert ErrorReason.SIBLING_ERROR.value == "sibling_error"
        assert ErrorReason.STREAMING_FALLBACK.value == "streaming_fallback"
        assert ErrorReason.TIMEOUT.value == "timeout"
        assert ErrorReason.PERMISSION_DENIED.value == "permission_denied"
        assert ErrorReason.TOOL_NOT_FOUND.value == "tool_not_found"
        assert ErrorReason.EXECUTION_ABORTED.value == "execution_aborted"
        assert ErrorReason.INVALID_INPUT.value == "invalid_input"
        assert ErrorReason.RESULT_TOO_LARGE.value == "result_too_large"


class TestSyntheticError:
    """Testes para SyntheticError."""

    def test_user_interrupted_message(self):
        """Testa mensagem de interrupção do usuário."""
        error = SyntheticError(
            reason=ErrorReason.USER_INTERRUPTED,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "❌" in error.message
        assert "cancelada pelo usuário" in error.message

    def test_sibling_error_message(self):
        """Testa mensagem de erro de irmão."""
        error = SyntheticError(
            reason=ErrorReason.SIBLING_ERROR,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "⚠️" in error.message
        assert "abortada" in error.message
        assert "irmã" in error.message

    def test_streaming_fallback_message(self):
        """Testa mensagem de streaming fallback."""
        error = SyntheticError(
            reason=ErrorReason.STREAMING_FALLBACK,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "🔄" in error.message
        assert "Streaming fallback" in error.message
        assert "retry da API" in error.message

    def test_timeout_message(self):
        """Testa mensagem de timeout."""
        error = SyntheticError(
            reason=ErrorReason.TIMEOUT,
            tool_id="tool-1",
            tool_name="TestTool",
            context={"timeout_seconds": 60},
        )
        assert "⏱️" in error.message
        assert "Timeout" in error.message
        assert "60s" in error.message

    def test_timeout_default_value(self):
        """Testa timeout com valor default."""
        error = SyntheticError(
            reason=ErrorReason.TIMEOUT,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "30" in error.message

    def test_permission_denied_message(self):
        """Testa mensagem de permissão negada."""
        error = SyntheticError(
            reason=ErrorReason.PERMISSION_DENIED,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "🔒" in error.message
        assert "Permissão negada" in error.message

    def test_permission_denied_with_reason(self):
        """Testa mensagem de permissão negada com motivo."""
        error = SyntheticError(
            reason=ErrorReason.PERMISSION_DENIED,
            tool_id="tool-1",
            tool_name="TestTool",
            context={"reason": "Blocked by policy"},
        )
        assert "🔒" in error.message
        assert "Blocked by policy" in error.message

    def test_tool_not_found_message(self):
        """Testa mensagem de ferramenta não encontrada."""
        error = SyntheticError(
            reason=ErrorReason.TOOL_NOT_FOUND,
            tool_id="tool-1",
            tool_name="MissingTool",
        )
        assert "❓" in error.message
        assert "MissingTool" in error.message
        assert "não encontrada" in error.message

    def test_execution_aborted_message(self):
        """Testa mensagem de execução abortada."""
        error = SyntheticError(
            reason=ErrorReason.EXECUTION_ABORTED,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "🛑" in error.message
        assert "abortada" in error.message

    def test_invalid_input_message(self):
        """Testa mensagem de input inválido."""
        error = SyntheticError(
            reason=ErrorReason.INVALID_INPUT,
            tool_id="tool-1",
            tool_name="TestTool",
            original_error="Missing required field 'path'",
        )
        assert "📝" in error.message
        assert "Input inválido" in error.message
        assert "Missing required field 'path'" in error.message

    def test_invalid_input_without_error(self):
        """Testa mensagem de input inválido sem erro original."""
        error = SyntheticError(
            reason=ErrorReason.INVALID_INPUT,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "📝" in error.message
        assert "Input inválido" in error.message

    def test_result_too_large_message(self):
        """Testa mensagem de resultado muito grande."""
        error = SyntheticError(
            reason=ErrorReason.RESULT_TOO_LARGE,
            tool_id="tool-1",
            tool_name="TestTool",
            context={"size": 150_000, "max_size": 100_000},
        )
        assert "📊" in error.message
        assert "150" in error.message
        assert "100" in error.message

    def test_result_too_large_default_values(self):
        """Testa mensagem de resultado muito grande com defaults."""
        error = SyntheticError(
            reason=ErrorReason.RESULT_TOO_LARGE,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert "📊" in error.message

    def test_to_tool_result(self):
        """Testa conversão para ToolResult."""
        error = SyntheticError(
            reason=ErrorReason.USER_INTERRUPTED,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        result = error.to_tool_result()

        # ToolResult do MindFlow usa truncation para indicar erro
        assert result.truncation is not None
        assert result.truncation.reason == TruncationReason.SIZE_LIMIT
        assert "❌" in result.data
        assert result.mcp_meta["error_reason"] == "user_interrupted"
        assert result.mcp_meta["tool_id"] == "tool-1"
        assert result.mcp_meta["tool_name"] == "TestTool"
        assert result.mcp_meta["synthetic"] is True


class TestCreateErrorFunctions:
    """Testes para funções helper de criação de erros."""

    def test_create_user_interrupted_error(self):
        """Testa criação de erro de interrupção do usuário."""
        error = create_user_interrupted_error("tool-1", "TestTool")
        assert error.reason == ErrorReason.USER_INTERRUPTED
        assert error.tool_id == "tool-1"
        assert error.tool_name == "TestTool"

    def test_create_sibling_error(self):
        """Testa criação de erro de irmão."""
        error = create_sibling_error("tool-1", "Write", "Bash")
        assert error.reason == ErrorReason.SIBLING_ERROR
        assert error.tool_id == "tool-1"
        assert error.tool_name == "Write"
        assert error.context["failed_tool"] == "Bash"

    def test_create_streaming_fallback_error(self):
        """Testa criação de erro de streaming fallback."""
        error = create_streaming_fallback_error("tool-1", "TestTool")
        assert error.reason == ErrorReason.STREAMING_FALLBACK
        assert error.tool_id == "tool-1"
        assert error.tool_name == "TestTool"

    def test_create_timeout_error(self):
        """Testa criação de erro de timeout."""
        error = create_timeout_error("tool-1", "TestTool", 60.0)
        assert error.reason == ErrorReason.TIMEOUT
        assert error.tool_id == "tool-1"
        assert error.tool_name == "TestTool"
        assert error.context["timeout_seconds"] == 60.0

    def test_create_permission_denied_error(self):
        """Testa criação de erro de permissão negada."""
        error = create_permission_denied_error("tool-1", "TestTool", "Policy blocked")
        assert error.reason == ErrorReason.PERMISSION_DENIED
        assert error.tool_id == "tool-1"
        assert error.tool_name == "TestTool"
        assert error.context["reason"] == "Policy blocked"

    def test_create_permission_denied_error_without_reason(self):
        """Testa criação de erro de permissão negada sem motivo."""
        error = create_permission_denied_error("tool-1", "TestTool")
        assert error.reason == ErrorReason.PERMISSION_DENIED
        assert error.context["reason"] == ""

    def test_create_tool_not_found_error(self):
        """Testa criação de erro de ferramenta não encontrada."""
        error = create_tool_not_found_error("tool-1", "MissingTool")
        assert error.reason == ErrorReason.TOOL_NOT_FOUND
        assert error.tool_id == "tool-1"
        assert error.tool_name == "MissingTool"

    def test_create_execution_aborted_error(self):
        """Testa criação de erro de execução abortada."""
        error = create_execution_aborted_error("tool-1", "TestTool")
        assert error.reason == ErrorReason.EXECUTION_ABORTED
        assert error.tool_id == "tool-1"
        assert error.tool_name == "TestTool"

    def test_create_invalid_input_error(self):
        """Testa criação de erro de input inválido."""
        error = create_invalid_input_error("tool-1", "TestTool", "Missing field")
        assert error.reason == ErrorReason.INVALID_INPUT
        assert error.tool_id == "tool-1"
        assert error.tool_name == "TestTool"
        assert error.original_error == "Missing field"

    def test_create_result_too_large_error(self):
        """Testa criação de erro de resultado muito grande."""
        error = create_result_too_large_error("tool-1", "TestTool", 150_000, 100_000)
        assert error.reason == ErrorReason.RESULT_TOO_LARGE
        assert error.tool_id == "tool-1"
        assert error.tool_name == "TestTool"
        assert error.context["size"] == 150_000
        assert error.context["max_size"] == 100_000


class TestSyntheticErrorEdgeCases:
    """Testes para casos extremos de SyntheticError."""

    def test_error_with_none_context(self):
        """Testa erro com contexto None."""
        error = SyntheticError(
            reason=ErrorReason.TIMEOUT,
            tool_id="tool-1",
            tool_name="TestTool",
            context=None,
        )
        assert "30" in error.message  # Default timeout

    def test_error_with_empty_context(self):
        """Testa erro com contexto vazio."""
        error = SyntheticError(
            reason=ErrorReason.TIMEOUT,
            tool_id="tool-1",
            tool_name="TestTool",
            context={},
        )
        assert "30" in error.message  # Default timeout

    def test_error_with_none_original_error(self):
        """Testa erro com original_error None."""
        error = SyntheticError(
            reason=ErrorReason.INVALID_INPUT,
            tool_id="tool-1",
            tool_name="TestTool",
            original_error=None,
        )
        assert "Input inválido" in error.message

    def test_error_message_immutability(self):
        """Testa que mensagem é consistente."""
        error1 = SyntheticError(
            reason=ErrorReason.USER_INTERRUPTED,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        error2 = SyntheticError(
            reason=ErrorReason.USER_INTERRUPTED,
            tool_id="tool-1",
            tool_name="TestTool",
        )
        assert error1.message == error2.message

    def test_all_errors_have_emoji(self):
        """Testa que todos os erros têm emoji."""
        for reason in ErrorReason:
            error = SyntheticError(
                reason=reason,
                tool_id="tool-1",
                tool_name="TestTool",
                context={"timeout_seconds": 30, "size": 1000, "max_size": 500},
            )
            # Todos devem começar com emoji
            assert error.message[0] in "❌⚠️🔄⏱️🔒❓🛑📝📊"