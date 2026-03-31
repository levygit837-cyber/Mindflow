"""Builtin Hooks — Hooks pré-construídos para MindFlow.

Adaptados de src/hooks/ do Claude Code:
- format_hook.py: Auto-formatação de código
- lint_hook.py: Execução de linter
- test_hook.py: Execução de testes pós-tool
- git_hook.py: Git safety (bloqueia comandos perigosos)
"""

from __future__ import annotations

from mindflow_backend.hooks.builtin.format_hook import FormatHook
from mindflow_backend.hooks.builtin.lint_hook import LintHook
from mindflow_backend.hooks.builtin.test_hook import TestHook
from mindflow_backend.hooks.builtin.git_hook import GitSafetyHook

__all__ = [
    "FormatHook",
    "LintHook",
    "TestHook",
    "GitSafetyHook",
]