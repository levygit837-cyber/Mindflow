"""Hook Result — Output from hook execution.

Adapted from Claude Code's HookResult, AggregatedHookResult, HookJSONOutput,
and related types in src/types/hooks.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mindflow_backend.hooks.types import HookEvent, HookPermissionBehavior


@dataclass(frozen=True)
class HookCommand:
    """Comando individual de hook.

    Equivalente de HookCommandSchema em src/schemas/hooks.ts do Claude Code.
    """
    type: str  # "command" | "prompt" | "agent" | "http"
    command: str | None = None
    timeout: int | None = None  # Timeout em segundos


@dataclass(frozen=True)
class HookMatcher:
    """Matcher para hooks — combina matcher pattern com lista de handlers.

    Equivalente de HookMatcherSchema em src/schemas/hooks.ts.
    """
    matcher: str | None  # None = "all", e.g. "read_file" para tool-specific
    hooks: list[HookCommand] = field(default_factory=list)


@dataclass
class HookResult:
    """Resultado de execução de um hook individual.

    Equivalente de HookResult em src/utils/hooks.ts do Claude Code.
    Contém tanto o resultado bruto quanto as decisões de comportamento.
    """

    # ── Identificação ──
    event: HookEvent | str
    command: str

    # ── Status ──
    status: str  # "success" | "error" | "timeout" | "blocked" | "cancelled"

    # ── Output bruto ──
    raw_output: str | None = None
    error: str | None = None

    # ── Decisão de comportamento (PreToolUse) ──
    behavior: HookPermissionBehavior | None = None  # "allow" | "deny" | "ask" | "passthrough"
    reason: str | None = None  # Reason for the behavior decision

    # ── Input atualizado (PreToolUse — quando behavior='allow') ──
    updated_input: dict[str, Any] | None = None

    # ── Contexto adicional ──
    add_context: str | None = None  # Additional context to inject into prompt

    # ── Hook-specific output ──
    hook_specific_output: dict[str, Any] | None = None

    # ── Tool output modification (PostToolUse) ──
    updated_mcp_tool_output: dict[str, Any] | None = None  # Modified tool output

    # ── Watch paths (FileChanged hooks) ──
    watch_paths: list[str] | None = None  # Paths to watch for changes

    # ── Initial user message (SessionStart) ──
    initial_user_message: str | None = None  # Message to inject at session start

    # ── Controle de fluxo ──
    prevent_continuation: bool = False  # If True, stop processing remaining hooks
    stop_reason: str | None = None  # Message shown when prevent_continuation=True

    # ── Resultado de permissão (PermissionRequest) ──
    permission_request_result: dict[str, Any] | None = None

    @classmethod
    def from_response(
        cls,
        event: str,
        command: str,
        response: dict[str, Any],
    ) -> HookResult:
        """Cria HookResult a partir da resposta JSON de um hook command.

        Equivalente da lógica de parsing em executeHooks do src/utils/hooks.ts.
        """
        status = "success"
        behavior = None
        reason = None
        updated_input = None
        add_context = None
        hook_specific_output = None
        updated_mcp_tool_output = None
        watch_paths = None
        initial_user_message = None
        prevent_continuation = False
        stop_reason = None
        permission_request_result = None

        # Parse behavior from response
        if "behavior" in response:
            behavior = HookPermissionBehavior(response["behavior"])
        if "reason" in response:
            reason = response["reason"]
        if "updated_input" in response:
            updated_input = response["updated_input"]

        # Parse hook-specific output
        if "hookSpecificOutput" in response:
            hook_specific_output = response["hookSpecificOutput"]
            hso = hook_specific_output

            # PreToolUse-specific: permissionDecision
            if hso.get("hookEventName") == "PreToolUse":
                if "permissionDecision" in hso:
                    behavior = HookPermissionBehavior(hso["permissionDecision"])
                if "permissionDecisionReason" in hso:
                    reason = hso["permissionDecisionReason"]
                if "updatedInput" in hso:
                    updated_input = hso["updatedInput"]
                if "additionalContext" in hso:
                    add_context = hso["additionalContext"]

            # PostToolUse-specific: additionalContext, updatedMCPToolOutput
            elif hso.get("hookEventName") == "PostToolUse":
                if "additionalContext" in hso:
                    add_context = hso["additionalContext"]
                if "updatedMCPToolOutput" in hso:
                    updated_mcp_tool_output = hso["updatedMCPToolOutput"]

            # UserPromptSubmit-specific: additionalContext
            elif hso.get("hookEventName") == "UserPromptSubmit":
                if "additionalContext" in hso:
                    add_context = hso["additionalContext"]

            # SessionStart-specific: additionalContext + initialUserMessage
            elif hso.get("hookEventName") == "SessionStart":
                if "additionalContext" in hso:
                    add_context = hso["additionalContext"]

            # PermissionRequest-specific: decision
            elif hso.get("hookEventName") == "PermissionRequest":
                if "decision" in hso:
                    permission_request_result = hso["decision"]

        # Parse control fields
        if "continue" in response and response["continue"] is False:
            prevent_continuation = True
            stop_reason = response.get("stopReason", "Hook requested stop")

        if "suppressOutput" in response and response["suppressOutput"]:
            status = "success"  # Still success, just suppressed

        if "systemMessage" in response:
            add_context = response["systemMessage"]

        return cls(
            event=event,
            command=command,
            status=status,
            raw_output=str(response) if response else None,
            behavior=behavior,
            reason=reason,
            updated_input=updated_input,
            add_context=add_context,
            hook_specific_output=hook_specific_output,
            updated_mcp_tool_output=updated_mcp_tool_output,
            watch_paths=watch_paths,
            initial_user_message=initial_user_message,
            prevent_continuation=prevent_continuation,
            stop_reason=stop_reason,
            permission_request_result=permission_request_result,
        )


@dataclass
class AggregatedHookResult:
    """Resultado agregado de múltiplos hooks para o mesmo evento.

    Equivalente de AggregatedHookResult em src/types/hooks.ts.
    O HookManager agrega resultados individuais em um resultado agregado.
    """

    event: HookEvent | str

    # ── Mensagens ──
    messages: list[Any] = field(default_factory=list)  # Mensagens para o modelo
    blocking_errors: list[dict[str, Any]] = field(default_factory=list)

    # ── Controle de fluxo ──
    prevent_continuation: bool = False
    stop_reason: str | None = None

    # ── Decisão de permissão agregada ──
    permission_behavior: HookPermissionBehavior | None = None
    permission_decision_reason: str | None = None
    updated_input: dict[str, Any] | None = None

    # ── Contexto adicional ──
    additional_contexts: list[str] = field(default_factory=list)

    # ── Resultado de permissão ──
    permission_request_result: dict[str, Any] | None = None

    # ── Retry flag ──
    retry: bool = False

    @classmethod
    def from_results(cls, event: HookEvent | str, results: list[HookResult]) -> AggregatedHookResult:
        """Agrega resultados individuais em um resultado agregado.

        Equivalente da lógica de agregação em executeHooks do src/utils/hooks.ts.
        """
        aggregated = cls(event=event)

        for result in results:
            # Blocking errors
            if result.status == "error":
                aggregated.blocking_errors.append({
                    "command": result.command,
                    "error": result.error or "Unknown error",
                })

            # Permission behavior — last non-passthrough wins
            if result.behavior and result.behavior != HookPermissionBehavior.PASSTHROUGH:
                aggregated.permission_behavior = result.behavior
                if result.reason:
                    aggregated.permission_decision_reason = result.reason
                if result.updated_input:
                    aggregated.updated_input = result.updated_input

            # Additional context
            if result.add_context:
                aggregated.additional_contexts.append(result.add_context)

            # Prevent continuation
            if result.prevent_continuation:
                aggregated.prevent_continuation = True
                if result.stop_reason:
                    aggregated.stop_reason = result.stop_reason

            # Permission request result
            if result.permission_request_result:
                aggregated.permission_request_result = result.permission_request_result

        return aggregated