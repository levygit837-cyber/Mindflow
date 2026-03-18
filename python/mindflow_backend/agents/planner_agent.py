"""Planner Agent for structured implementation planning.

This agent is activated by the Orchestrator when:
1. Context has been gathered (context_gathered=True)
2. Task requires planning (needs_planning=True)
3. Complexity is high enough to warrant explicit planning

The PlannerAgent uses the PLANNING_PROMPT from agents/prompts/specialized/planning.py
and produces a structured plan document.
"""

from __future__ import annotations

import json
from typing import Any

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.prompts.specialized.planning import PLANNING_PROMPT
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime import get_model_for_provider
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, SandboxMode, ThinkingLevel, ToolScope
from mindflow_backend.schemas.orchestration.planning import PlanningRequest, PlanningResponse
from mindflow_backend.schemas.orchestration.specialists import SpecialistType

_logger = get_logger(__name__)


class PlannerAgent:
    """Agent specialized in creating structured implementation plans.
    
    Unlike regular agents, the PlannerAgent:
    - Does NOT execute code or make changes
    - Produces a plan document (.md) for user confirmation
    - Uses the PLANNING_PROMPT for structured planning
    """

    def __init__(self) -> None:
        self.agent_role = AgentType.ANALYST
        self.specialist = SpecialistType.DEEP_ITERATION  # Uses deep analysis for planning
        self.system_prompt = PLANNING_PROMPT
        self.tools: list[ToolScope] = [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM]
        self.sandbox = SandboxMode.READ_ONLY
        self.thinking_level = ThinkingLevel.HIGH
        self.max_iterations = 3

    async def create_plan(
        self,
        request: PlanningRequest,
    ) -> PlanningResponse:
        """Create a structured plan from the request.
        
        This is the main entry point for planning. The agent:
        1. Uses the gathered context
        2. Applies the PLANNING_PROMPT
        3. Produces a structured plan document
        """
        from mindflow_backend.services.orchestration.planning_service import get_planning_service
        
        settings = get_settings()
        provider = settings.default_provider
        model = settings.default_model
        
        _logger.info(
            "planner_agent_started",
            session_id=request.session_id,
            goal=request.message[:100],
            has_context=bool(request.context),
        )
        
        # Build the planning prompt
        planning_messages = self._build_planning_messages(request)
        
        try:
            llm = get_model_for_provider(provider, model)
            response = await llm.ainvoke(planning_messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            
            # Parse the plan from the response
            plan_content = self._parse_plan_response(response_text, request)
            
            # Store the plan via PlanningService
            planning_service = get_planning_service()
            result = await planning_service.create_plan(request, plan_content)
            
            _logger.info(
                "planner_agent_completed",
                plan_id=result.plan.plan_id,
                tasks=len(result.plan.tasks),
            )
            
            return result
            
        except Exception as exc:
            _logger.error("planner_agent_failed", error=str(exc))
            # Return a minimal plan on failure
            return await self._create_fallback_plan(request, str(exc))

    def _build_planning_messages(self, request: PlanningRequest) -> list[dict[str, str]]:
        """Build the messages for the planning LLM call."""
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        # Add gathered context
        if request.context.strip():
            messages.append({
                "role": "system",
                "content": f"## Gathered Context\n\n{request.context}",
            })
        
        # Add workspace info
        if request.folder_path:
            messages.append({
                "role": "system",
                "content": f"## Workspace Root\n\nThe working directory is: {request.folder_path}\n\nUse this path as the base for all file references in the plan.",
            })
        
        # Add complexity indicator
        complexity_note = ""
        if request.complexity_score >= 0.7:
            complexity_note = "\n\n**Note**: This is a HIGH complexity task. Consider breaking it into more granular subtasks."
        elif request.complexity_score >= 0.5:
            complexity_note = "\n\n**Note**: This is a MEDIUM complexity task. Plan accordingly."
        
        # Add the planning request
        messages.append({
            "role": "user",
            "content": f"Create a structured implementation plan for:\n\n**{request.message}**{complexity_note}\n\nFollow the planning protocol strictly. Output the plan in markdown format.",
        })
        
        return messages

    def _parse_plan_response(self, response_text: str, request: PlanningRequest) -> dict[str, Any]:
        """Parse the LLM response into a structured plan."""
        # Try to extract structured data from the markdown response
        plan_content: dict[str, Any] = {
            "goal": request.message,
            "tasks": [],
            "file_impact_matrix": [],
            "risks": [],
            "open_questions": [],
        }
        
        # Extract goal/intent
        import re
        
        # Look for goal in headers
        goal_match = re.search(r"# Plan:\s*(.+?)(?:\n|$)", response_text)
        if goal_match:
            plan_content["goal"] = goal_match.group(1).strip()
        
        # Look for work type
        type_match = re.search(r"\*\*Type\*\*:\s*(.+?)(?:\n|$)", response_text)
        if type_match:
            plan_content["work_type"] = type_match.group(1).strip().lower().replace(" ", "_")
        
        # Look for scope
        scope_match = re.search(r"\*\*Scope\*\*:\s*(.+?)(?:\n|$)", response_text)
        if scope_match:
            plan_content["scope"] = scope_match.group(1).strip()
        
        # Extract tasks from markdown
        tasks = []
        task_pattern = r"### Task\s+(\d+):\s*(.+?)(?=\n###|\n##|$)"
        for match in re.finditer(task_pattern, response_text, re.DOTALL):
            task_num = match.group(1)
            task_content = match.group(2)
            
            # Extract task fields
            def get_field(name: str, text: str) -> str:
                m = re.search(rf"\*\*{name}\*\*:\s*(.+?)(?:\n|$)", text)
                return m.group(1).strip() if m else ""
            
            title = task_content.split("\n")[0].strip()
            description = get_field("Description", task_content)
            if not description:
                # Try to get description from the content after title
                desc_match = re.search(r"\n(.+?)(?:\n\*\*|\n###|\Z)", task_content, re.DOTALL)
                if desc_match:
                    description = desc_match.group(1).strip()[:200]
            
            task = {
                "task_id": f"task-{task_num}",
                "title": title,
                "description": description,
                "depends_on": [d.strip() for d in get_field("Depends on", task_content).split(",") 
                              if d.strip() and d.strip().lower() != "none"],
                "files": [f.strip() for f in get_field("Files", task_content).split(",") 
                         if f.strip() and f.strip().lower() != "n/a"],
                "action": get_field("Action", task_content) or "EDIT",
                "agent": get_field("Agent", task_content) or "analyst",
                "priority": get_field("Priority", task_content) or "medium",
                "verification": get_field("Verification", task_content),
            }
            tasks.append(task)
        
        plan_content["tasks"] = tasks
        
        # Extract file impact matrix
        matrix_pattern = r"\| (.+?) \| (.+?) \| (.+?) \|"
        matrix_entries = []
        for match in re.finditer(matrix_pattern, response_text):
            path, action, desc = match.groups()
            if path.lower() != "path" and path.strip():  # Skip header row
                matrix_entries.append({
                    "path": path.strip(),
                    "action": action.strip(),
                    "description": desc.strip(),
                })
        plan_content["file_impact_matrix"] = matrix_entries
        
        # Extract risks
        risks_section = re.search(r"## Risks.*?\n(.+?)(?:\n##|\Z)", response_text, re.DOTALL)
        if risks_section:
            risks_text = risks_section.group(1)
            plan_content["risks"] = [
                r.strip().lstrip("- ").lstrip("**Risk**: ")
                for r in risks_section.group(1).split("\n")
                if r.strip().startswith("-")
            ]
        
        # Extract open questions
        questions_section = re.search(r"## Open Questions.*?\n(.+?)(?:\n##|\Z)", response_text, re.DOTALL)
        if questions_section:
            plan_content["open_questions"] = [
                q.strip().lstrip("- ").lstrip("**Question**: ")
                for q in questions_section.group(1).split("\n")
                if q.strip().startswith("-")
            ]
        
        return plan_content

    async def _create_fallback_plan(self, request: PlanningRequest, error: str) -> PlanningResponse:
        """Create a minimal fallback plan when planning fails."""
        from mindflow_backend.services.orchestration.planning_service import get_planning_service
        
        plan_content = {
            "goal": request.message,
            "work_type": "new_feature",
            "scope": "To be determined",
            "tasks": [
                {
                    "task_id": "task-1",
                    "title": f"Implement: {request.message[:50]}",
                    "description": request.message,
                    "depends_on": [],
                    "files": [],
                    "action": "EDIT",
                    "agent": "analyst",
                    "priority": "medium",
                    "verification": "Manual review",
                }
            ],
            "risks": [f"Planning failed: {error}"],
            "open_questions": ["Review and refine the plan before proceeding"],
        }
        
        planning_service = get_planning_service()
        return await planning_service.create_plan(request, plan_content)


# Global planner agent instance
_planner_agent: PlannerAgent | None = None


def get_planner_agent() -> PlannerAgent:
    """Get the global planner agent instance."""
    global _planner_agent
    if _planner_agent is None:
        _planner_agent = PlannerAgent()
    return _planner_agent
