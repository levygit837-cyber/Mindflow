"""MemdirLayer — Persistent Long-Term Memory (Auto-Memory) Layer.

This layer instructs the agent on how to manage its own persistent memory
across sessions by reading and updating a central index (`MEMORY.md`) and
individual topic files in a dedicated `.mindflow/memory/` directory.

Based on Claude Code's `memdir.ts`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from mindflow_backend.agents.prompts.assembler import AssemblyContext, PromptLayer
from mindflow_backend.agents.prompts.layers.memdir_types import (
    ENTRYPOINT_NAME,
    MAX_ENTRYPOINT_BYTES,
    MAX_ENTRYPOINT_LINES,
    MEMORY_FRONTMATTER_EXAMPLE,
    TRUSTING_RECALL_SECTION,
    TYPES_SECTION_INDIVIDUAL,
    WHAT_NOT_TO_SAVE_SECTION,
    WHEN_TO_ACCESS_SECTION,
)

logger = logging.getLogger(__name__)


@dataclass
class EntrypointTruncation:
    """Result of truncating the memory entrypoint file."""
    content: str
    line_count: int
    byte_count: int
    was_line_truncated: bool
    was_byte_truncated: bool


def format_file_size(size_in_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    return f"{size_in_bytes / (1024 * 1024):.1f} MB"


def truncate_entrypoint_content(raw: str) -> EntrypointTruncation:
    """Truncate MEMORY.md content to line AND byte caps, appending a warning.
    
    Line-truncates first, then byte-truncates at the last newline before the cap.
    """
    trimmed = raw.strip()
    content_lines = trimmed.split("\n")
    line_count = len(content_lines)
    byte_count = len(trimmed.encode("utf-8"))

    was_line_truncated = line_count > MAX_ENTRYPOINT_LINES
    was_byte_truncated = byte_count > MAX_ENTRYPOINT_BYTES

    if not was_line_truncated and not was_byte_truncated:
        return EntrypointTruncation(
            content=trimmed,
            line_count=line_count,
            byte_count=byte_count,
            was_line_truncated=False,
            was_byte_truncated=False,
        )

    truncated = (
        "\n".join(content_lines[:MAX_ENTRYPOINT_LINES])
        if was_line_truncated
        else trimmed
    )

    truncated_bytes = truncated.encode("utf-8")
    if len(truncated_bytes) > MAX_ENTRYPOINT_BYTES:
        # Find the last newline within the byte limit
        allowed_bytes = truncated_bytes[:MAX_ENTRYPOINT_BYTES]
        cut_at = allowed_bytes.rfind(b"\n")
        
        if cut_at > 0:
            truncated = allowed_bytes[:cut_at].decode("utf-8", errors="ignore")
        else:
            truncated = allowed_bytes.decode("utf-8", errors="ignore")

    reason = ""
    if was_byte_truncated and not was_line_truncated:
        reason = f"{format_file_size(byte_count)} (limit: {format_file_size(MAX_ENTRYPOINT_BYTES)}) — index entries are too long"
    elif was_line_truncated and not was_byte_truncated:
        reason = f"{line_count} lines (limit: {MAX_ENTRYPOINT_LINES})"
    else:
        reason = f"{line_count} lines and {format_file_size(byte_count)}"

    warning = (
        f"\n\n> WARNING: {ENTRYPOINT_NAME} is {reason}. Only part of it was loaded. "
        "Keep index entries to one line under ~200 chars; move detail into topic files."
    )

    return EntrypointTruncation(
        content=truncated + warning,
        line_count=line_count,
        byte_count=byte_count,
        was_line_truncated=was_line_truncated,
        was_byte_truncated=was_byte_truncated,
    )


class MemdirLayer(PromptLayer):
    """Prompt layer for the auto-memory (Memdir) persistent system."""
    
    name = "memdir"
    priority = 84  # High priority, run just after static MemoryFileLayer

    def __init__(self, memory_dir_name: str = ".mindflow/memory"):
        self.memory_dir_name = memory_dir_name

    def _build_memory_lines(self, memory_dir: str) -> list[str]:
        """Build the behavioral instructions for the auto-memory system."""
        
        how_to_save = [
            "## How to save memories",
            "",
            "Saving a memory is a two-step process:",
            "",
            "**Step 1** — write the memory to its own file (e.g., `user_role.md`, `feedback_testing.md`) using this frontmatter format:",
            "",
            *MEMORY_FRONTMATTER_EXAMPLE,
            "",
            f"**Step 2** — add a pointer to that file in `{ENTRYPOINT_NAME}`. `{ENTRYPOINT_NAME}` is an index, not a memory — each entry should be one line, under ~150 characters: `- [Title](file.md) — one-line hook`. It has no frontmatter. Never write memory content directly into `{ENTRYPOINT_NAME}`.",
            "",
            f"- `{ENTRYPOINT_NAME}` is always loaded into your conversation context — lines after {MAX_ENTRYPOINT_LINES} will be truncated, so keep the index concise",
            "- Keep the name, description, and type fields in memory files up-to-date with the content",
            "- Organize memory semantically by topic, not chronologically",
            "- Update or remove memories that turn out to be wrong or outdated",
            "- Do not write duplicate memories. First check if there is an existing memory you can update before writing a new one.",
        ]

        lines = [
            "# auto memory",
            "",
            f"You have a persistent, file-based memory system at `{memory_dir}`. This directory exists — write to it directly with your file writing tools.",
            "",
            "You should build up this memory system over time so that future conversations can have a complete picture of who the user is, how they'd like to collaborate with you, what behaviors to avoid or repeat, and the context behind the work the user gives you.",
            "",
            "If the user explicitly asks you to remember something, save it immediately as whichever type fits best. If they ask you to forget something, find and remove the relevant entry.",
            "",
            *TYPES_SECTION_INDIVIDUAL,
            *WHAT_NOT_TO_SAVE_SECTION,
            "",
            *how_to_save,
            "",
            *WHEN_TO_ACCESS_SECTION,
            "",
            *TRUSTING_RECALL_SECTION,
            "",
            "## Memory and other forms of persistence",
            "Memory is one of several persistence mechanisms available to you as you assist the user in a given conversation. The distinction is often that memory can be recalled in future conversations and should not be used for persisting information that is only useful within the scope of the current conversation.",
            "- When to use or update a plan instead of memory: If you are about to start a non-trivial implementation task and would like to reach alignment with the user on your approach you should use a Plan rather than saving this information to memory. Similarly, if you already have a plan within the conversation and you have changed your approach persist that change by updating the plan rather than saving a memory.",
            "- When to use or update tasks instead of memory: When you need to break your work in current conversation into discrete steps or keep track of your progress use tasks instead of saving to memory. Tasks are great for persisting information about the work that needs to be done in the current conversation, but memory should be reserved for information that will be useful in future conversations.",
            "",
            "## Searching past context",
            "",
            "When looking for past context, search topic files in your memory directory using your search tools (e.g., `codebase_search` or `grep`).",
            "Use narrow search terms (error messages, file paths, function names) rather than broad keywords.",
            "",
        ]
        
        return lines

    async def render(self, context: AssemblyContext) -> str | None:
        working_dir = context.working_directory or os.getcwd()
        memory_dir_path = Path(working_dir) / self.memory_dir_name
        
        # Ensure memory directory exists conceptually, we don't strictly need to create it
        # unless we want to guarantee it's there. The prompt tells the agent it exists.
        try:
            memory_dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.debug(f"Failed to create memory directory {memory_dir_path}: {e}")

        entrypoint_path = memory_dir_path / ENTRYPOINT_NAME
        entrypoint_content = ""

        if entrypoint_path.exists():
            try:
                entrypoint_content = entrypoint_path.read_text(encoding="utf-8")
            except OSError as e:
                logger.debug(f"Failed to read {entrypoint_path}: {e}")

        lines = self._build_memory_lines(str(memory_dir_path))

        if entrypoint_content.strip():
            truncation = truncate_entrypoint_content(entrypoint_content)
            lines.extend([
                f"## {ENTRYPOINT_NAME}",
                "",
                truncation.content
            ])
        else:
            lines.extend([
                f"## {ENTRYPOINT_NAME}",
                "",
                f"Your {ENTRYPOINT_NAME} is currently empty. When you save new memories, they will appear here."
            ])

        return "\n".join(lines)
