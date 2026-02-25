/**
 * GET /api/swarm/[taskId] — Get the current status of a swarm task.
 *
 * Returns a SwarmTaskStatus snapshot from the in-memory registry.
 */

import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@backend/swarm/registry";
import type { SwarmTaskStatus } from "@shared/types/swarm";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;
  const session = getSession(taskId);

  if (!session) {
    return NextResponse.json(
      { error: "Task not found", task_id: taskId },
      { status: 404 },
    );
  }

  const status: SwarmTaskStatus = {
    task_id: session.taskId,
    task_status: session.status,
    coder_plan: session.stateSnapshot.coder_plan,
    analyst_state: session.stateSnapshot.analyst_state as SwarmTaskStatus["analyst_state"],
    sandbox_display: session.stateSnapshot.sandbox_display,
    notifications_count: session.notifier.getSequence(),
  };

  return NextResponse.json(status);
}
