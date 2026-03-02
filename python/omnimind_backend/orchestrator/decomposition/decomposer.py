from __future__ import annotations

import json
import uuid
from typing import Any

from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.decomposition import DTSession, DTStatus, DTTask
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class Decomposer:
    """Break complex tasks into a Directed Acyclic Graph (DAG) of sub-tasks."""

    SYSTEM_PROMPT = """
You are the OmniMind Decomposer. Your goal is to break down a complex engineering request into a set of discrete, atomic sub-tasks.

## Output Format
Return ONLY a JSON array of objects with the following schema:
[
  {
    "id": "task_1",
    "title": "Short title",
    "description": "Detailed implementation steps",
    "agent_type": "coder|analyst|researcher|arch_tech|critic",
    "dependencies": []
  }
]

## Rules
- Ensure tasks form a Directed Acyclic Graph (DAG) with no cycles.
- Assign the best agent personality for each task.
- Be specific in descriptions (mention files, patterns, tools).
"""

    async def decompose(
        self, 
        message: str, 
        session_id: str,
        complexity_score: float,
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> DTSession:
        """Analyze message and return a DTSession with sub-tasks."""
        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model
        
        try:
            llm = get_model_for_provider(p, m)
            
            prompt = (
                f"{self.SYSTEM_PROMPT}\n\n"
                f"Memory Context (if available):\n{memory_context}\n\n"
                f"Request: {message}"
            )
            
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # Clean JSON from response (strip markdown blocks if present)
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()

            tasks_data = json.loads(json_str)
            
            tasks = []
            for t in tasks_data:
                tasks.append(DTTask(
                    id=t["id"],
                    title=t["title"],
                    description=t["description"],
                    agent_type=t.get("agent_type"),
                    dependencies=t.get("dependencies", []),
                    status=DTStatus.PENDING
                ))
            
            return DTSession(
                id=str(uuid.uuid4()),
                session_id=session_id,
                original_task=message,
                tasks=tasks,
                status=DTStatus.PLANNING,
                complexity_score=complexity_score
            )
            
        except Exception as e:
            _logger.error("decomposition_error", error=str(e))
            # Fallback: create a single task session
            return DTSession(
                id=str(uuid.uuid4()),
                session_id=session_id,
                original_task=message,
                tasks=[DTTask(
                    id="task_fallback",
                    title="Process request",
                    description=message,
                    status=DTStatus.PENDING
                )],
                status=DTStatus.PLANNING,
                complexity_score=complexity_score
            )
