"""Memory Types — defines the 4 types of MIND.md memory files.

Inspired by Claude Code's CLAUDE.md hierarchy:
- User Memory:     ~/.mindflow/MIND.md (personal preferences)
- Project Memory:  ./MIND.md or ./.mindflow/MIND.md (versioned project instructions)
- Local Memory:    ./MIND.local.md or ./.mindflow/MIND.local.md (gitignored local overrides)
- Managed Memory:  ~/.mindflow/managed/MIND.md (enterprise/admin instructions)
"""

from __future__ import annotations

from enum import StrEnum


class MemoryType(StrEnum):
    """Tipos de memória MIND.md — hierarquia inspirada no Claude Code.

    Ordem de prioridade (do mais alto para o mais baixo):
    1. MANAGED — Instruções de administradores/enterprise (não pode ser sobrescrito)
    2. LOCAL — Preferências locais do desenvolvedor (gitignored)
    3. PROJECT — Instruções do projeto (versionado, compartilhado)
    4. USER — Preferências pessoais globais do usuário
    """

    USER = "user"
    PROJECT = "project"
    LOCAL = "local"
    MANAGED = "managed"


# Priority order: higher number = higher priority (injected first in prompt)
MEMORY_TYPE_PRIORITY: dict[MemoryType, int] = {
    MemoryType.MANAGED: 95,
    MemoryType.LOCAL: 82,
    MemoryType.PROJECT: 85,
    MemoryType.USER: 90,
}

# Descriptive headers for each memory type in the assembled prompt
MEMORY_TYPE_HEADERS: dict[MemoryType, str] = {
    MemoryType.MANAGED: "## Managed Memory (Enterprise)",
    MemoryType.USER: "## User Memory",
    MemoryType.PROJECT: "## Project Memory",
    MemoryType.LOCAL: "## Local Memory",
}

# Default search paths for each memory type (relative to working_dir or home)
DEFAULT_SEARCH_PATHS: dict[MemoryType, list[str]] = {
    MemoryType.USER: [
        "~/.mindflow/MIND.md",
    ],
    MemoryType.PROJECT: [
        ".mindflow/MIND.md",
        "MIND.md",
    ],
    MemoryType.LOCAL: [
        ".mindflow/MIND.local.md",
        "MIND.local.md",
    ],
    MemoryType.MANAGED: [
        "~/.mindflow/managed/MIND.md",
        "/etc/mindflow/MIND.md",
    ],
}