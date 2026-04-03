"""Hook result processing pipeline.

Inspirado na lógica de processamento de hooks do Claude Code.
Processa resultados de hooks e aplica transformações (updated_input, updated_output, etc.).
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookPermissionBehavior


class HookResultProcessor:
    """Processa resultados de hooks e aplica transformações.

    Equivalente da lógica de processamento em executePreToolHooks() e
    executePostToolHooks() do Claude Code.
    """

    @staticmethod
    def process_pre_tool_results(
        results: list[HookResult],
        original_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Processa resultados de PreToolUse hooks.

        Aplica transformações na ordem:
        1. Verifica permissões (deny tem precedência)
        2. Aplica updated_input sequencialmente
        3. Coleta additional_context

        Args:
            results: Lista de HookResult de PreToolUse hooks
            original_input: Input original da ferramenta

        Returns:
            dict com:
            - "allowed": bool - Se a execução é permitida
            - "reason": str | None - Razão da negação (se denied)
            - "updated_input": dict[str, Any] - Input modificado
            - "additional_context": list[str] - Contextos adicionais

        Examples:
            >>> results = [
            ...     HookResult(event="PreToolUse", command="hook1", status="success",
            ...                behavior="allow", updated_input={"file": "new.py"}),
            ...     HookResult(event="PreToolUse", command="hook2", status="success",
            ...                add_context="Lint passed"),
            ... ]
            >>> processed = HookResultProcessor.process_pre_tool_results(
            ...     results, {"file": "old.py"}
            ... )
            >>> processed["allowed"]
            True
            >>> processed["updated_input"]["file"]
            'new.py'
        """
        allowed = True
        deny_reason = None
        updated_input = original_input.copy()
        additional_context = []

        for result in results:
            # Check permission behavior (deny > ask > allow)
            if result.behavior == HookPermissionBehavior.DENY:
                allowed = False
                deny_reason = result.reason or "Blocked by hook"
                break  # Deny tem precedência — para processamento

            # Apply updated_input (sequencial — cada hook pode modificar)
            if result.updated_input:
                updated_input.update(result.updated_input)

            # Collect additional context
            if result.add_context:
                additional_context.append(result.add_context)

        return {
            "allowed": allowed,
            "reason": deny_reason,
            "updated_input": updated_input,
            "additional_context": additional_context,
        }

    @staticmethod
    def process_post_tool_results(
        results: list[HookResult],
        original_output: Any,
    ) -> dict[str, Any]:
        """Processa resultados de PostToolUse hooks.

        Aplica transformações na ordem:
        1. Aplica updated_mcp_tool_output (último vence)
        2. Coleta additional_context
        3. Coleta watch_paths

        Args:
            results: Lista de HookResult de PostToolUse hooks
            original_output: Output original da ferramenta

        Returns:
            dict com:
            - "updated_output": Any - Output modificado (ou original)
            - "additional_context": list[str] - Contextos adicionais
            - "watch_paths": list[str] - Paths para watch

        Examples:
            >>> results = [
            ...     HookResult(event="PostToolUse", command="hook1", status="success",
            ...                updated_mcp_tool_output={"formatted": True}),
            ...     HookResult(event="PostToolUse", command="hook2", status="success",
            ...                add_context="Formatting applied"),
            ... ]
            >>> processed = HookResultProcessor.process_post_tool_results(
            ...     results, {"formatted": False}
            ... )
            >>> processed["updated_output"]["formatted"]
            True
        """
        updated_output = original_output
        additional_context = []
        watch_paths = []

        for result in results:
            # Apply updated_mcp_tool_output (último vence)
            if result.updated_mcp_tool_output:
                updated_output = result.updated_mcp_tool_output

            # Collect additional context
            if result.add_context:
                additional_context.append(result.add_context)

            # Collect watch paths
            if result.watch_paths:
                watch_paths.extend(result.watch_paths)

        return {
            "updated_output": updated_output,
            "additional_context": additional_context,
            "watch_paths": watch_paths,
        }

    @staticmethod
    def should_block_execution(results: list[HookResult]) -> tuple[bool, str | None]:
        """Verifica se algum hook bloqueou a execução.

        Args:
            results: Lista de HookResult

        Returns:
            Tupla (should_block, reason)
            - should_block: True se deve bloquear
            - reason: Razão do bloqueio (se bloqueado)

        Examples:
            >>> results = [
            ...     HookResult(event="PreToolUse", command="hook1", status="success",
            ...                behavior="deny", reason="Dangerous command"),
            ... ]
            >>> blocked, reason = HookResultProcessor.should_block_execution(results)
            >>> blocked
            True
            >>> reason
            'Dangerous command'
        """
        for result in results:
            if result.behavior == HookPermissionBehavior.DENY:
                return True, result.reason or "Blocked by hook"

            if result.prevent_continuation:
                return True, result.stop_reason or "Hook requested stop"

        return False, None

    @staticmethod
    def merge_additional_contexts(contexts: list[str]) -> str | None:
        """Merge múltiplos contextos adicionais em um único string.

        Args:
            contexts: Lista de strings de contexto

        Returns:
            String merged ou None se lista vazia

        Examples:
            >>> contexts = ["Lint passed", "Tests passed", "Format applied"]
            >>> HookResultProcessor.merge_additional_contexts(contexts)
            'Lint passed\\nTests passed\\nFormat applied'
        """
        if not contexts:
            return None

        return "\n".join(contexts)
