"""Shared utilities for the decomposition pipeline."""

from __future__ import annotations

import re
from typing import Any


def extract_json_from_response(content: str) -> str:
    """Strip markdown code fences from an LLM response and return the JSON string."""
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


def validate_task_dependencies(tasks: list[Any]) -> list[str]:
    """DFS cycle detection on the task dependency graph.

    Returns a list of error messages; empty means no cycles.
    """
    graph: dict[str, list[str]] = {
        str(t.task_id): [str(d) for d in t.dependencies] for t in tasks
    }

    visited: set[str] = set()
    rec_stack: set[str] = set()
    errors: list[str] = []

    def _has_cycle(node: str) -> bool:
        if node in rec_stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if _has_cycle(neighbor):
                return True
        rec_stack.discard(node)
        return False

    for tid in graph:
        if tid not in visited and _has_cycle(tid):
            errors.append(f"Circular dependency detected at task {tid}")

    return errors


def clean_task_title(title: str) -> str:
    """Normalise a task title string."""
    title = re.sub(r"\s+", " ", title.strip())
    for prefix in ("task:", "step:", "action:"):
        if title.lower().startswith(prefix):
            title = title[len(prefix):].strip()
    return title[0].upper() + title[1:] if title else title


class DecompositionMetrics:
    """Lightweight metrics collector for the pipeline."""

    def __init__(self) -> None:
        self.tasks_decomposed = 0
        self.tasks_resolved = 0
        self.context_hits = 0
        self.semantic_searches = 0
        self.errors: list[str] = []
        self._start: float | None = None
        self._end: float | None = None

    def start(self) -> None:
        import time
        self._start = time.time()

    def stop(self) -> None:
        import time
        self._end = time.time()

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def summary(self) -> dict[str, Any]:
        duration = (self._end or 0.0) - (self._start or 0.0)
        return {
            "duration_seconds": duration,
            "tasks_decomposed": self.tasks_decomposed,
            "tasks_resolved": self.tasks_resolved,
            "context_hits": self.context_hits,
            "semantic_searches": self.semantic_searches,
            "error_count": len(self.errors),
            "success_rate": (
                self.tasks_resolved / max(self.tasks_decomposed, 1)
            )
            * 100,
            "errors": self.errors,
        }
