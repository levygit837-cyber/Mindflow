"""Planning-aware execution flow for the Orchestrator.

This module implements the planning layer integration:
1. Orchestrator gathers context
2. Orchestrator activates PlannerAgent when needed
3. PlannerAgent creates a plan (.md)
4. User confirms/rejects the plan
5. System converts plan to todo-list
6. Execution loop continues until todo-list is complete

The flow integrates with the existing simple_flow.py architecture.
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langchain_core.callbacks.manager import adispatch_custom_event

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.step_runner import run_workflow_step
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from mindflow_backend.schemas.orchestration.planning import PlanningRequest, PlanStatus
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep
from mindflow_backend.schemas.tools.planning import TodoItemStatus

_logger = get_logger(__name__)

# Safety limit for execution iterations
_SAFETY_ITERATION_LIMIT = 20


class PlanningFlowState(TypedDict, total=False):
    """State for the planning-aware execution flow."""
    message: str
    provider: str
    model: str
    session_id: str
    plan_id: str | None
    plan_status: PlanStatus | None
    todo_task_id: str | None
    current_iteration: int
    execution_complete: bool
    response: str | None
    error: str | None
    folder_path: str | None
    memory_context: str
    conversation_history: list[dict[str, str]]


async def should_trigger_planning(
    message: str,
    complexity_score: float,
    session_context: dict[str, Any],
) -> bool:
    """Determine if planning should be triggered (LEGACY - keyword-based).
    
    DEPRECATED: This function uses keyword matching. Use should_trigger_planning_v2
    for LLM-based semantic analysis when ENABLE_LLM_PLANNING_TRIGGER is enabled.
    
    Planning is triggered when:
    1. Complexity is high (>= 0.6)
    2. Task involves multiple files or components
    3. User explicitly requests planning
    4. No existing plan is in progress
    """
    # Check for planning keywords
    planning_keywords = [
        "planejar", "plano", "plan", "planejamento",
        "implementar", "refatorar", "migrar", "arquitetura",
        "estruturar", "organizar", "decompor",
        "implement", "refactor", "migrate", "architecture", 
        "structure", "organize", "decompose", "design", "build", "create",
        "planear", "diseñar", "construir", "crear", "arquitectura", 
        "estructurar", "organizar", "descomponer",
    ]
    message_lower = message.lower()
    has_planning_intent = any(kw in message_lower for kw in planning_keywords)
    
    # Check for existing plan
    from mindflow_backend.services.orchestration.planning_service import get_planning_service
    planning_service = get_planning_service()
    session_id = session_context.get("session_id", "")
    
    # Check for existing confirmed plan in execution
    plans = await planning_service.get_session_plans(session_id)
    has_active_plan = any(
        p.status in (PlanStatus.CONFIRMED, PlanStatus.IN_EXECUTION)
        for p in plans
    )
    
    # Decision logic
    if has_active_plan:
        return False  # Don't create new plan if one is already in execution
    
    if has_planning_intent:
        return True
    
    if complexity_score >= 0.6:
        return True
    
    # Check for multi-component indicators
    multi_component_keywords = [
        "sistema", "módulo", "componente", "feature", "funcionalidade",
        "integração", "api", "service", "layer", "camada",
    ]
    if any(kw in message_lower for kw in multi_component_keywords):
        return complexity_score >= 0.4
    
    return False


async def should_trigger_planning_v2(
    message: str,
    session_context: dict[str, Any],
    folder_path: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[bool, Any]:
    """Determine if planning should be triggered using LLM semantic analysis.
    
    This is the new intelligent planning trigger that uses LLM to understand
    semantic intent rather than keyword matching.
    
    Returns:
        (should_trigger, decision): Boolean trigger + full PlanningDecision object
    """
    from mindflow_backend.orchestrator.planning.analyzer import get_planning_analyzer
    from mindflow_backend.schemas.orchestration.planning import PlanningAnalysisRequest
    from mindflow_backend.services.orchestration.planning_service import get_planning_service
    
    # Check for existing active plan
    planning_service = get_planning_service()
    session_id = session_context.get("session_id", "")
    
    plans = await planning_service.get_session_plans(session_id)
    has_active_plan = any(
        p.status in (PlanStatus.CONFIRMED, PlanStatus.IN_EXECUTION)
        for p in plans
    )
    
    if has_active_plan:
        # Don't create new plan if one is already in execution
        from mindflow_backend.schemas.orchestration.planning import PlanningDecision
        return False, PlanningDecision(
            requires_planning=False,
            confidence=1.0,
            reasoning="Active plan already in execution",
            estimated_subtasks=0,
            complexity_factors=["active_plan_exists"],
        )
    
    # Use LLM to analyze
    analyzer = get_planning_analyzer()
    request = PlanningAnalysisRequest(
        message=message,
        session_context=str(session_context),
        folder_path=folder_path,
        conversation_history=conversation_history or [],
    )
    
    decision = await analyzer.should_trigger_planning(request)
    
    # Emit reasoning to user
    if decision.requires_planning:
        await adispatch_custom_event(
            "agent_thought",
            {
                "thought": f"🤔 **Análise de Planejamento**\n\n"
                           f"{decision.reasoning}\n\n"
                           f"Estimativa: {decision.estimated_subtasks} subtarefas\n"
                           f"Confiança: {decision.confidence:.0%}"
            },
        )
    
    return decision.requires_planning, decision


async def should_trigger_planning_hybrid(
    message: str,
    complexity_score: float,
    session_context: dict[str, Any],
    folder_path: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> bool:
    """Hybrid planning trigger with feature flag support.
    
    Uses LLM-based analysis if ENABLE_LLM_PLANNING_TRIGGER is enabled,
    otherwise falls back to keyword-based matching.
    
    This function also logs comparison between old and new methods for A/B testing.
    """
    from mindflow_backend.orchestrator.planning.metrics import get_metrics_collector
    
    settings = get_settings()
    metrics = get_metrics_collector()
    session_id = session_context.get("session_id", "")
    
    start_time = time.time()
    
    if settings.enable_llm_planning_trigger:
        should_trigger, decision = await should_trigger_planning_v2(
            message=message,
            session_context=session_context,
            folder_path=folder_path,
            conversation_history=conversation_history,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        method_used = "fallback" if "fallback" in decision.reasoning.lower() else "llm"
        
        # Track metrics
        await metrics.track_trigger_decision(
            session_id=session_id,
            trigger_decision=should_trigger,
            confidence=decision.confidence,
            latency_ms=latency_ms,
            method_used=method_used,
        )
        
        # Log comparison with old method for A/B testing
        old_result = await should_trigger_planning(message, complexity_score, session_context)
        if old_result != should_trigger:
            _logger.warning(
                "planning_trigger_mismatch",
                old_method=old_result,
                new_method=should_trigger,
                confidence=decision.confidence,
                reasoning=decision.reasoning[:100],
            )
        
        return should_trigger
    else:
        result = await should_trigger_planning(message, complexity_score, session_context)
        latency_ms = (time.time() - start_time) * 1000
        
        # Track legacy metrics
        await metrics.track_trigger_decision(
            session_id=session_id,
            trigger_decision=result,
            confidence=1.0 if result else 0.0,
            latency_ms=latency_ms,
            method_used="legacy",
        )
        
        return result


async def run_planning_phase(
    state: PlanningFlowState,
    context: str,
) -> dict[str, Any]:
    """Run the planning phase: create plan and await confirmation.
    
    Returns a state update with the plan status.
    """
    from mindflow_backend.agents.planner_agent import get_planner_agent
    
    session_id = state.get("session_id", "")
    message = state.get("message", "")
    folder_path = state.get("folder_path")
    
    await adispatch_custom_event(
        "agent_thought",
        {"thought": "📊 Analisando complexidade e reunindo contexto para planejamento..."},
    )
    
    planner = get_planner_agent()
    request = PlanningRequest(
        session_id=session_id,
        message=message,
        folder_path=folder_path,
        context=context,
        complexity_score=0.5,  # Default, could be computed
    )
    
    result = await planner.create_plan(request)
    
    # Emit plan summary to user
    await adispatch_custom_event(
        "agent_thought",
        {"thought": f"📋 **Plano criado** ({result.plan.plan_id})\n\n{result.summary}"},
    )
    
    return {
        "plan_id": result.plan.plan_id,
        "plan_status": result.plan.status,
        "response": result.summary,
    }


async def check_plan_confirmation(
    session_id: str,
    plan_id: str,
) -> dict[str, Any]:
    """Check if a plan has been confirmed.
    
    This is called by the Orchestrator to check plan status
    before proceeding with execution.
    """
    from mindflow_backend.services.orchestration.planning_service import get_planning_service
    
    planning_service = get_planning_service()
    plan = await planning_service.get_plan(session_id, plan_id)
    
    if plan is None:
        return {"status": "not_found", "ready": False}
    
    if plan.status == PlanStatus.CONFIRMED:
        return {
            "status": "confirmed",
            "ready": True,
            "todo_task_id": plan.plan_id,
        }
    
    if plan.status == PlanStatus.REJECTED:
        return {"status": "rejected", "ready": False}
    
    return {"status": plan.status.value, "ready": False}


async def run_execution_loop(
    state: PlanningFlowState,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Run the execution loop for a confirmed plan.
    
    This loop:
    1. Gets the next pending todo item
    2. Executes it with the appropriate agent
    3. Updates the todo status
    4. Continues until all items are complete
    """
    from mindflow_backend.services import get_todo_planning_service
    
    session_id = state.get("session_id", "")
    plan_id = state.get("plan_id", "")
    folder_path = state.get("folder_path")
    memory_context = state.get("memory_context", "")
    conversation_history = state.get("conversation_history", [])
    
    todo_service = get_todo_planning_service()
    
    # Update plan status to in_execution
    from mindflow_backend.services.orchestration.planning_service import get_planning_service
    planning_service = get_planning_service()
    await planning_service.update_plan_status(session_id, plan_id, PlanStatus.IN_EXECUTION)
    
    iteration = 0
    all_results: list[dict[str, Any]] = []
    
    # Pre-fetch the list to determine dynamic safety limit and prevent infinite conversion loop
    try:
        todo_response = await todo_service.get_list(session_id, plan_id)
        todo_list = todo_response.todo_list
    except ValueError:
        plan = await planning_service.get_plan(session_id, plan_id)
        if plan:
            await planning_service._convert_plan_to_todo(plan)
            try:
                todo_response = await todo_service.get_list(session_id, plan_id)
                todo_list = todo_response.todo_list
            except ValueError as exc:
                raise RuntimeError(f"Failed to create or retrieve todo list for plan {plan_id}") from exc
        else:
            return {"execution_complete": True, "error": "Plan not found."}

    # Dynamic limit: Max 5 iterations per task (to allow for retries/recovery)
    dynamic_limit = max(20, len(todo_list.items) * 5)
    
    while iteration < dynamic_limit:
        iteration += 1
        
        # Get the latest state of the todo list
        try:
            todo_response = await todo_service.get_list(session_id, plan_id)
            todo_list = todo_response.todo_list
        except ValueError:
            break
        
        # Find next pending item
        pending_items = [
            item for item in todo_list.items
            if item.status == TodoItemStatus.PENDING
        ]
        
        if not pending_items:
            # Check for blocked items
            blocked_items = [
                item for item in todo_list.items
                if item.status == TodoItemStatus.BLOCKED
            ]
            if blocked_items:
                await adispatch_custom_event(
                    "agent_thought",
                    {"thought": f"⚠️ {len(blocked_items)} tarefas bloqueadas. Aguardando resolução."},
                )
                break
            
            # All done!
            await adispatch_custom_event(
                "agent_thought",
                {"thought": f"✅ Todas as {len(todo_list.items)} tarefas concluídas!"},
            )
            await planning_service.update_plan_status(session_id, plan_id, PlanStatus.COMPLETED)
            
            # Track execution completion
            from mindflow_backend.orchestrator.planning.metrics import get_metrics_collector
            metrics = get_metrics_collector()
            await metrics.track_execution_completion(
                session_id=session_id,
                plan_id=plan_id,
                completed=True,
            )
            
            break
        
        # Get the next item (respecting dependencies)
        next_item = None
        for item in pending_items:
            # Check if dependencies are met
            deps_met = all(
                any(
                    dep_item.item_id == dep and dep_item.status == TodoItemStatus.COMPLETED
                    for dep_item in todo_list.items
                )
                for dep in item.dependencies
            )
            if deps_met:
                next_item = item
                break
        
        if next_item is None:
            # No item with met dependencies - take first pending
            next_item = pending_items[0]
        
        # Execute the item
        await adispatch_custom_event(
            "agent_thought",
            {"thought": f"🔄 Executando: **{next_item.title}** (iteração {iteration})"},
        )
        
        # Build workflow step
        agent_role = AgentType.ANALYST
        if next_item.owner_agent:
            if "coder" in next_item.owner_agent.lower():
                agent_role = AgentType.CODER
            elif "researcher" in next_item.owner_agent.lower():
                agent_role = AgentType.RESEARCHER
        
        step = WorkflowStep(
            step_id=next_item.item_id,
            agent_id=next_item.owner_agent or "analyst",
            agent_role=agent_role,
            specialist=None,
            objective=next_item.title,
            tools=[],
            sandbox="read_only" if agent_role == AgentType.ANALYST else "full",
            context_strategy="carry_summary",
            depends_on=next_item.dependencies,
        )
        
        # Update status to in_progress
        await todo_service.update_item_status(
            session_id=session_id,
            task_id=plan_id,
            item_id=next_item.item_id,
            status="in_progress",
        )
        
        # Run the step
        try:
            result = await run_workflow_step(
                step=step,
                user_message=next_item.description or next_item.title,
                provider=provider,
                model=model,
                session_id=session_id,
                folder_path=folder_path,
                memory_context=memory_context,
                conversation_history=conversation_history,
            )
            
            # Update status based on result
            new_status = "completed"
            if result.get("error"):
                new_status = "failed"
            
            await todo_service.update_item_status(
                session_id=session_id,
                task_id=plan_id,
                item_id=next_item.item_id,
                status=new_status,
                notes=result.get("key_findings", "")[:400],
            )
            
            all_results.append({
                "item_id": next_item.item_id,
                "title": next_item.title,
                "status": new_status,
                "result": result,
            })
            
        except Exception as exc:
            _logger.error("execution_loop_step_failed", item_id=next_item.item_id, error=str(exc))
            await todo_service.update_item_status(
                session_id=session_id,
                task_id=plan_id,
                item_id=next_item.item_id,
                status="failed",
                notes=str(exc)[:400],
            )
    
    # Build final response
    completed = sum(1 for r in all_results if r["status"] == "completed")
    failed = sum(1 for r in all_results if r["status"] == "failed")
    
    summary = f"Execução concluída: {completed} tarefas completas, {failed} falhas."
    
    return {
        "execution_complete": True,
        "response": summary,
        "results": all_results,
        "iterations": iteration,
    }


async def synthesize_final_response(
    state: PlanningFlowState,
    results: list[dict[str, Any]],
) -> str:
    """Synthesize a final response from all execution results."""
    from mindflow_backend.runtime import get_model_for_provider
    
    settings = get_settings()
    provider = state.get("provider") or settings.default_provider
    model = state.get("model") or settings.default_model
    
    # Build summary of results
    results_summary = "\n\n".join(
        f"**{r['title']}**:\n{r.get('result', {}).get('key_findings', 'Sem resultado')[:500]}"
        for r in results
        if r["status"] == "completed"
    )
    
    if not results_summary:
        return "Nenhuma tarefa foi completada com sucesso."
    
    # Use LLM to synthesize
    llm = get_model_for_provider(provider, model)
    messages = [
        {
            "role": "system",
            "content": (
                "Você é um agente de síntese. Dado os resultados de múltiplas tarefas "
                "executadas, produza uma resposta coesa e completa para o usuário. "
                "Seja conciso mas completo."
            ),
        },
        {
            "role": "user",
            "content": f"Resultados das tarefas:\n\n{results_summary}",
        },
    ]
    
    try:
        response = await llm.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        return results_summary
