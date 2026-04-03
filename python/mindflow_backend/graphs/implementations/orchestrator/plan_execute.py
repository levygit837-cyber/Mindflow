"""Plan-and-Execute graph for complex multi-step tasks.

Implements a LangGraph StateGraph with three nodes:
  planner   → creates a structured plan of subtasks with agent assignments
  executor  → runs the next subtask using the appropriate agent + ReAct tools
  evaluator → decides whether to continue, or synthesise and end

Entry: planner
Loop:  executor → evaluator → executor (while tasks remain, up to 8 steps)
Exit:  evaluator emits final response and transitions to END
"""

from __future__ import annotations

import json
from typing import Any, TypedDict
from uuid import uuid4

from langchain_core.callbacks.manager import adispatch_custom_event
from langgraph.graph import END, StateGraph  # type: ignore[import]

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime import get_model_for_provider
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, SandboxMode, ToolScope
from mindflow_backend.services import get_todo_planning_service
from mindflow_backend.services.orchestration.todo_planning_service import build_todo_items_from_plan

_logger = get_logger(__name__)

_SAFETY_STEP_LIMIT = 8


class PlanExecuteState(TypedDict, total=False):
    """State flowing through the plan-execute graph."""

    message: str
    provider: str
    model: str
    session_id: str
    task_id: str
    folder_path: str | None
    memory_context: str
    plan: list[dict]          # [{item_id, task, agent, estimated_tools, ...}]
    full_plan: list[dict]
    past_steps: list[tuple]   # [(task_title, result)]
    response: str | None
    retry_count: int


def _normalize_plan(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(plan):
        task = str(raw.get("task") or raw.get("title") or "").strip()
        if not task:
            task = f"Step {index + 1}"
        entry = dict(raw)
        entry["item_id"] = str(raw.get("item_id") or raw.get("task_id") or f"plan-step-{index + 1}")
        entry["task"] = task
        entry["description"] = str(raw.get("description") or raw.get("scope") or task)
        entry["agent"] = str(raw.get("agent") or raw.get("owner_agent") or "analyst")
        entry["estimated_tools"] = list(raw.get("estimated_tools") or [])
        entry["dependencies"] = [str(dep) for dep in raw.get("dependencies", []) if dep is not None]
        entry["priority"] = str(raw.get("priority") or "medium")
        try:
            entry["complexity_score"] = min(max(float(raw.get("complexity_score", 0.0) or 0.0), 0.0), 1.0)
        except (TypeError, ValueError):
            entry["complexity_score"] = 0.0
        entry["complexity_reason"] = str(raw.get("complexity_reason") or "")
        normalized.append(entry)
    return normalized


def _render_focus_context(focused_items: list[dict[str, Any]] | list[Any]) -> str:
    if not focused_items:
        return ""
    lines = ["Open complex todo items:"]
    for item in focused_items:
        item_id = getattr(item, "item_id", None) or item.get("item_id")
        title = getattr(item, "title", None) or item.get("title")
        score = getattr(item, "complexity_score", None)
        if score is None and isinstance(item, dict):
            score = item.get("complexity_score", 0.0)
        status = getattr(item, "status", None) or item.get("status")
        lines.append(f"- [{item_id}] {title} (complexity={score}, status={status})")
    return "\n".join(lines)


async def _planner_node(state: PlanExecuteState) -> dict:
    """LLM creates a structured plan with subtasks and agent assignments."""
    settings = get_settings()
    provider = state.get("provider") or settings.default_provider
    model = state.get("model") or settings.default_model
    message = state.get("message", "")
    session_id = str(state.get("session_id") or "")
    task_id = str(state.get("task_id") or f"plan-{uuid4().hex[:12]}")

    await adispatch_custom_event(
        "agent_thought",
        {"thought": "Criando plano de execução para tarefa complexa..."},
    )

    llm = get_model_for_provider(provider, model)
    sandbox = MindFlowSandbox(
        root_dir=state.get("folder_path") or getattr(settings, "working_path", None),
        read_only=False,
    )
    tool_registry = create_default_registry(sandbox, session_id=session_id)
    planning_tools = tool_registry.get_tools_for_scopes([ToolScope.PLANNING])
    lc_tools = to_langchain_tools(planning_tools)

    planner_prompt = (
        "You are a planning agent. Given a user request, decompose it into 2-5 concrete subtasks. "
        "Each subtask must have: 'item_id', 'task', 'description', 'agent' (one of: analyst, coder, researcher), "
        "'estimated_tools' (list of tool names needed, or empty list), 'priority' (low|medium|high), "
        "'complexity_score' (0-1), 'complexity_reason', and optional 'dependencies'. "
        "If the request is complex or produces 3 or more steps, call write_todos once with the stable full plan. "
        "After tool use, return ONLY a JSON array of subtask objects, nothing else."
    )

    messages = [
        {"role": "system", "content": planner_prompt},
    ]
    if state.get("memory_context"):
        messages.append(
            {
                "role": "system",
                "content": f"Memory Context:\n{state['memory_context']}",
            }
        )
    messages.append(
        {
            "role": "user",
            "content": (
                f"Session ID: {session_id}\n"
                f"Task ID: {task_id}\n"
                f"Create a plan for: {message}"
            ),
        }
    )

    try:
        if lc_tools:
            raw = await invoke_with_tools(
                llm=llm.bind_tools(lc_tools),
                messages=messages,
                lc_tools=lc_tools,
                session_id=session_id,
            )
        else:
            response = await llm.ainvoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)

        # Extract JSON from the response
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            plan = _normalize_plan(json.loads(raw[start:end]))
        else:
            plan = _normalize_plan([{"task": message, "agent": "analyst", "estimated_tools": []}])

        _logger.info("planner_node_done", subtasks=len(plan))
        todo_service = get_todo_planning_service()
        if await todo_service.is_stale(session_id=session_id, task_id=task_id):
            await todo_service.replace_list(
                session_id=session_id,
                task_id=task_id,
                goal=message,
                items=build_todo_items_from_plan(plan),
                source="planner_recovery",
            )
        await adispatch_custom_event(
            "agent_thought",
            {"thought": f"Plano criado com {len(plan)} subtasks: {', '.join(s.get('task', '')[:40] for s in plan[:3])}"},
        )
        return {"task_id": task_id, "plan": plan, "full_plan": plan, "past_steps": []}
    except Exception as exc:
        _logger.error("planner_node_error", error=str(exc))
        fallback_plan = _normalize_plan([{"task": message, "agent": "analyst", "estimated_tools": []}])
        return {
            "task_id": task_id,
            "plan": fallback_plan,
            "full_plan": fallback_plan,
            "past_steps": [],
        }


async def _executor_node(state: PlanExecuteState) -> dict:
    """Executes the next subtask using the assigned agent + tools."""
    settings = get_settings()
    provider = state.get("provider") or settings.default_provider
    model = state.get("model") or settings.default_model
    session_id = str(state.get("session_id") or "")
    task_id = str(state.get("task_id") or "")
    folder_path = state.get("folder_path")
    plan: list[dict] = list(state.get("plan") or [])
    full_plan: list[dict] = list(state.get("full_plan") or plan)
    past_steps: list[tuple] = list(state.get("past_steps") or [])

    if not plan:
        return {}

    next_task = plan[0]
    remaining_plan = plan[1:]
    task_description = next_task.get("task", "")
    agent_name = next_task.get("agent", "analyst")
    item_id = str(next_task.get("item_id") or task_description)
    memory_context = str(state.get("memory_context") or "")

    _logger.info("executor_node_start", task=task_description[:80], agent=agent_name)
    await adispatch_custom_event(
        "agent_thought",
        {"thought": f"Executando subtask: **{task_description[:80]}** (agente: {agent_name})"},
    )

    # Resolve agent type
    agent_type_map = {
        "analyst": AgentType.ANALYST,
        "coder": AgentType.CODER,
        "researcher": AgentType.RESEARCHER,
    }
    agent_type = agent_type_map.get(agent_name.lower(), AgentType.ANALYST)

    try:
        agent = get_agent(agent_type)
    except Exception as exc:
        _logger.error("executor_node_agent_lookup_failed", error=str(exc))
        past_steps.append((task_description, f"Error: agent not found ({exc})"))
        todo_service = get_todo_planning_service()
        if task_id:
            with_context = build_todo_items_from_plan(full_plan)
            await todo_service.replace_list(
                session_id=session_id,
                task_id=task_id,
                goal=state.get("message", ""),
                items=with_context,
                source="runtime_recovery",
            )
            await todo_service.update_item_status(
                session_id=session_id,
                task_id=task_id,
                item_id=item_id,
                status="failed",
                notes=f"Agent not found: {exc}",
            )
        return {"plan": remaining_plan, "full_plan": full_plan, "past_steps": past_steps}

    # Build context from prior results
    prior_context = ""
    if past_steps:
        prior_context = "Prior completed steps:\n" + "\n".join(
            f"- {title}: {result[:300]}" for title, result in past_steps[-3:]
        )

    focus_context = ""
    todo_service = get_todo_planning_service()
    if task_id:
        if await todo_service.is_stale(session_id=session_id, task_id=task_id):
            await todo_service.replace_list(
                session_id=session_id,
                task_id=task_id,
                goal=state.get("message", ""),
                items=build_todo_items_from_plan(full_plan),
                source="runtime_recovery",
            )
        focused = await todo_service.focus_complex_items(
            session_id=session_id,
            task_id=task_id,
            limit=3,
        )
        focus_context = _render_focus_context(focused.items)
        await todo_service.update_item_status(
            session_id=session_id,
            task_id=task_id,
            item_id=item_id,
            status="in_progress",
            notes=f"Executing with {agent_name}",
        )

    messages = [{"role": "system", "content": agent.system_prompt}]
    if memory_context:
        messages.append({"role": "system", "content": f"Memory Context:\n{memory_context}"})
    if prior_context:
        messages.append({"role": "system", "content": prior_context})
    if focus_context:
        messages.append({"role": "system", "content": focus_context})
    messages.append({"role": "user", "content": task_description})

    # Setup sandbox + tools
    sandbox_root = folder_path or (settings.working_path if hasattr(settings, "working_path") else None)
    sandbox = MindFlowSandbox(
        root_dir=sandbox_root,
        read_only=(agent.sandbox == SandboxMode.READ_ONLY),
    )
    tool_registry = create_default_registry(sandbox, session_id=session_id)
    tools = [] if agent.sandbox == SandboxMode.NONE else tool_registry.get_tools_for_agent(agent)

    llm = get_model_for_provider(provider, model)

    try:
        if tools:
            lc_tools = to_langchain_tools(tools)
            if lc_tools:
                llm_with_tools = llm.bind_tools(lc_tools)
                result_text = await invoke_with_tools(
                    llm=llm_with_tools,
                    messages=messages,
                    lc_tools=lc_tools,
                    session_id=session_id,
                )
            else:
                response = await llm.ainvoke(messages)
                result_text = response.content if hasattr(response, "content") else str(response)
        else:
            response = await llm.ainvoke(messages)
            result_text = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        _logger.error("executor_node_failed", error=str(exc))
        result_text = f"Error executing task: {exc}"

    past_steps.append((task_description, result_text))
    if task_id:
        status = "completed"
        lowered = result_text.lower()
        if lowered.startswith("error"):
            status = "failed"
        elif "blocked" in lowered:
            status = "blocked"
        await todo_service.update_item_status(
            session_id=session_id,
            task_id=task_id,
            item_id=item_id,
            status=status,
            notes=result_text[:400],
        )
    _logger.info("executor_node_done", task=task_description[:60], result_len=len(result_text))

    return {"plan": remaining_plan, "full_plan": full_plan, "past_steps": past_steps}


async def _evaluator_node(state: PlanExecuteState) -> dict:
    """Decides whether to continue executing or synthesize a final response."""
    settings = get_settings()
    provider = state.get("provider") or settings.default_provider
    model = state.get("model") or settings.default_model
    session_id = str(state.get("session_id") or "")
    task_id = str(state.get("task_id") or "")
    plan: list[dict] = state.get("plan") or []
    past_steps: list[tuple] = state.get("past_steps") or []
    message = state.get("message", "")

    # If there are more tasks and we haven't hit the safety limit, continue
    if plan and len(past_steps) < _SAFETY_STEP_LIMIT:
        return {}

    # All tasks done (or safety limit hit) — synthesize a final answer
    _logger.info("evaluator_node_synthesizing", steps=len(past_steps))
    await adispatch_custom_event(
        "agent_thought",
        {"thought": f"Sintetizando resultados de {len(past_steps)} subtasks..."},
    )

    steps_summary = "\n\n".join(
        f"**{title}:**\n{result[:800]}" for title, result in past_steps
    )

    llm = get_model_for_provider(provider, model)
    synth_messages = [
        {
            "role": "system",
            "content": (
                "You are a synthesis agent. Given the results of multiple subtasks, "
                "produce a coherent, complete final answer to the original user request. "
                "Be concise but thorough. Do not repeat the subtask structure — write a unified response."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original request: {message}\n\n"
                f"Completed subtasks:\n{steps_summary}"
            ),
        },
    ]

    try:
        response = await llm.ainvoke(synth_messages)
        final_text = response.content if hasattr(response, "content") else str(response)
        if task_id:
            try:
                await get_todo_planning_service().close_list(session_id=session_id, task_id=task_id)
            except Exception:
                _logger.warning("todo_list_close_failed", session_id=session_id, task_id=task_id)
        # Stream the final answer
        await adispatch_custom_event("agent_response", {"chunk": final_text})
        return {"response": final_text}
    except Exception as exc:
        _logger.error("evaluator_synthesis_failed", error=str(exc))
        fallback = "\n\n".join(f"**{t}:** {r}" for t, r in past_steps)
        if task_id:
            try:
                await get_todo_planning_service().close_list(session_id=session_id, task_id=task_id)
            except Exception:
                _logger.warning("todo_list_close_failed", session_id=session_id, task_id=task_id)
        await adispatch_custom_event("agent_response", {"chunk": fallback})
        return {"response": fallback}


def _should_continue(state: PlanExecuteState) -> str:
    if state.get("response"):
        return "end"
    plan = state.get("plan") or []
    past_steps = state.get("past_steps") or []
    if not plan or len(past_steps) >= _SAFETY_STEP_LIMIT:
        return "end"
    return "execute"


def build_plan_execute_flow() -> Any:
    """Build and compile the plan-execute LangGraph."""
    workflow: Any = StateGraph(dict)
    workflow.add_node("planner", _planner_node)
    workflow.add_node("executor", _executor_node)
    workflow.add_node("evaluator", _evaluator_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "evaluator")
    workflow.add_conditional_edges(
        "evaluator",
        _should_continue,
        {
            "execute": "executor",
            "end": END,
        },
    )

    return workflow.compile()
