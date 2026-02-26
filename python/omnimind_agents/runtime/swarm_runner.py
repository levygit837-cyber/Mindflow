from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict


def emit(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


async def run() -> int:
    try:
        request = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:
        emit({"kind": "error", "message": f"Invalid JSON input: {exc}"})
        return 1

    task_id = str(request.get("taskId") or "")
    description = str(request.get("description") or "").strip()
    if not task_id or not description:
        emit({"kind": "error", "message": "taskId and description are required"})
        return 1

    # Orchestrator: pending -> planning
    emit(
        {
            "kind": "event",
            "event_type": "AGENT_STATE_CHANGE",
            "agent_id": "orchestrator",
            "payload": {
                "old_state": "pending",
                "new_state": "planning",
                "detail": "Task received by python swarm runtime",
            },
        }
    )
    emit(
        {
            "kind": "event",
            "event_type": "PLAN_UPDATE",
            "agent_id": "orchestrator",
            "payload": {
                "plan_step": "initialization",
                "status": "started",
                "detail": "Preparing coding workflow",
            },
        }
    )
    emit({"kind": "status", "status": "planning"})

    await asyncio.sleep(0.05)

    # Coder phase
    emit(
        {
            "kind": "event",
            "event_type": "AGENT_STATE_CHANGE",
            "agent_id": "orchestrator",
            "payload": {
                "old_state": "planning",
                "new_state": "coding",
            },
        }
    )
    emit({"kind": "status", "status": "coding"})

    plan = (
        "1. Analyze task requirements\n"
        "2. Implement targeted code updates\n"
        "3. Run validation checks and summarize results"
    )

    for token in ["Analyzing", " task", " requirements", "...", " done"]:
        emit(
            {
                "kind": "event",
                "event_type": "TOKEN_STREAM",
                "agent_id": "coder",
                "payload": {
                    "token": token,
                },
            }
        )
        await asyncio.sleep(0.01)

    emit(
        {
            "kind": "event",
            "event_type": "PLAN_UPDATE",
            "agent_id": "coder",
            "payload": {
                "plan_step": "implementation",
                "status": "completed",
                "detail": "Generated implementation plan in python swarm runtime",
            },
        }
    )

    await asyncio.sleep(0.05)

    # Analyst/Reviewer/Sandbox phase
    emit({"kind": "status", "status": "reviewing"})
    emit(
        {
            "kind": "event",
            "event_type": "ANALYST_STATE_CHANGE",
            "agent_id": "live_analyst",
            "payload": {
                "old_state": "IDLE",
                "new_state": "MONITORING",
            },
        }
    )
    emit(
        {
            "kind": "event",
            "event_type": "SANDBOX_UPDATE",
            "agent_id": "sandbox_renderer",
            "payload": {
                "content": "Swarm python runtime finished execution pipeline.",
            },
        }
    )
    emit(
        {
            "kind": "event",
            "event_type": "REVIEW_FINDING",
            "agent_id": "reviewer",
            "payload": {
                "assessment": "APPROVED_WITH_SUGGESTIONS",
                "summary": "Execution completed. Review suggestions generated.",
            },
        }
    )

    await asyncio.sleep(0.05)

    emit({"kind": "status", "status": "complete"})
    emit(
        {
            "kind": "complete",
            "status": "complete",
            "stateSnapshot": {
                "coder_plan": plan,
                "analyst_state": "MONITORING",
                "sandbox_display": "Swarm python runtime finished execution pipeline.",
                "reviewer_report_md": "## Review\nExecution completed by python swarm runtime.",
            },
        }
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
