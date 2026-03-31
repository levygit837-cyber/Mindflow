"""Test Hook — Executa testes após tool edits."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Padrões de detecção de arquivos de teste
_TEST_PATTERNS = ["/tests/", "test_", "_test.", "test.", "spec."]


class TestHook:
    """Executa testes relacionados ao arquivo editado."""

    @staticmethod
    async def execute(context: HookContext) -> HookResult:
        """Roda testes relacionados ao arquivo editado."""
        if not context.tool_input:
            return HookResult(
                event=context.hook_event_name,
                command="test_hook",
                status="success",
            )

        file_path = context.tool_input.get("file_path", "")
        if not file_path:
            return HookResult(
                event=context.hook_event_name,
                command="test_hook",
                status="success",
            )

        # Só executar testes se o arquivo editado é um arquivo de teste
        # ou se o usuário configurou test_pós_tool=True
        if not any(p in file_path for p in _TEST_PATTERNS):
            return HookResult(
                event=context.hook_event_name,
                command="test_hook",
                status="success",
            )

        _, ext = os.path.splitext(file_path)

        if ext == ".py":
            test_cmd = ["python", "-m", "pytest", file_path, "-v", "--tb=short"]
        elif ext in (".ts", ".tsx"):
            test_cmd = ["npx", "vitest", "run", file_path]
        elif ext in (".js", ".jsx"):
            test_cmd = ["npx", "jest", file_path]
        elif ext == ".go":
            test_cmd = ["go", "test", "-v", "./..."]
        elif ext == ".rs":
            test_cmd = ["cargo", "test", "--", "--nocapture"]
        else:
            return HookResult(
                event=context.hook_event_name,
                command="test_hook",
                status="success",
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                *test_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)

            output = (stdout.decode() + stderr.decode()).strip()

            if proc.returncode != 0:
                return HookResult(
                    event=context.hook_event_name,
                    command="test_hook",
                    status="success",
                    add_context=f"Tests failed for {file_path}:\n{output[:2000]}",
                    hook_specific_output={
                        "hookEventName": "PostToolUse",
                        "additionalContext": f"Tests failed for {file_path}:\n{output[:2000]}",
                    },
                )

            return HookResult(
                event=context.hook_event_name,
                command="test_hook",
                status="success",
            )
        except FileNotFoundError:
            return HookResult(
                event=context.hook_event_name,
                command="test_hook",
                status="success",
            )
        except Exception as exc:
            _logger.warning("test_hook_error", file=file_path, error=str(exc))
            return HookResult(
                event=context.hook_event_name,
                command="test_hook",
                status="success",
                error=str(exc),
            )