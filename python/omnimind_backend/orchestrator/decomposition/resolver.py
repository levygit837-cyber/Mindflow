from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from omnimind_backend.agents._registry import get_agent
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.decomposition import DTSession, DTStatus, DTTask
from omnimind_backend.schemas.orchestrator import AgentType
from omnimind_backend.infra.config import get_settings

logger = logging.getLogger(__name__)


class Resolver:
    """Execute sub-tasks through specialized agent personalities."""

    async def resolve_task(
        self, 
        task: DTTask, 
        session: DTSession,
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> str:
        """Invoke the appropriate agent for a single sub-task."""
        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model
        
        # Determine agent type
        a_type = AgentType.CODER
        if task.agent_type:
            try:
                a_type = AgentType(task.agent_type.lower())
            except ValueError:
                logger.warning(f"Unknown agent type {task.agent_type}, defaulting to CODER.")
        
        agent = get_agent(a_type)
        task.status = DTStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        
        # Build context from previous tasks
        context = ""
        completed_tasks = [t for t in session.tasks if t.status == DTStatus.COMPLETED and t.result]
        if completed_tasks:
            context = "Context from previous steps:\n"
            for t in completed_tasks:
                context += f"### {t.title}\n{t.result}\n\n"

        user_prompt = f"{context}\n\nCurrent Task: {task.title}\nDescription: {task.description}"
        if memory_context.strip():
            user_prompt = (
                f"Memory Context (RAG):\n{memory_context}\n\n"
                f"{user_prompt}"
            )

        messages = [SystemMessage(content=agent.system_prompt), HumanMessage(content=user_prompt)]

        try:
            llm = get_model_for_provider(p, m)
            # In Phase 3.1 we added bind_tools, we should ideally use ToolRegistry here too.
            # For brevity in the MVP resolver, we'll do a direct invoke, 
            # but in final integration we use the same execute_node logic.
            response = await llm.ainvoke(messages)
            result = response.content if hasattr(response, "content") else str(response)
            
            task.result = result
            task.status = DTStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            return result
            
        except Exception as e:
            logger.error(f"Error resolving task {task.id}: {e}")
            task.status = DTStatus.FAILED
            task.error = str(e)
            raise e
