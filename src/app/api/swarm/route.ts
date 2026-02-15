/**
 * POST /api/swarm — Submit a new swarm task.
 *
 * Validates the request body, creates a new task session, starts the
 * swarm graph in the background, and returns the task ID + stream URL.
 */

import { NextRequest, NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { swarmTaskSubmissionSchema } from "@/types/swarm";
import type { LLMProvider } from "@/types/agent";
import { createSwarmGraph, buildInitialState } from "@/lib/swarm/graph";
import { registerSession, updateSession } from "@/lib/swarm/registry";
import { createLogger } from "@/utils/logger";

const logger = createLogger("api:swarm");

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = swarmTaskSubmissionSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: "Invalid request", details: parsed.error.flatten().fieldErrors },
        { status: 400 },
      );
    }

    const { description, provider, model, workingPath } = parsed.data;
    const taskId = uuidv4();

    // Create graph and notifier
    const { graph, notifier } = createSwarmGraph(taskId, description, {
      provider: (provider as LLMProvider) ?? undefined,
      model: model ?? undefined,
      context: workingPath ? { workingPath } : undefined,
    });

    // Register session before starting execution
    registerSession({
      taskId,
      notifier,
      status: "pending",
      stateSnapshot: {
        coder_plan: null,
        analyst_state: "IDLE",
        sandbox_display: "",
        reviewer_report_md: "",
      },
      startedAt: new Date().toISOString(),
    });

    // Start graph execution in background (non-blocking)
    const initialState = buildInitialState(taskId, description);

    (async () => {
      try {
        logger.info("Starting swarm graph execution", { taskId });
        updateSession(taskId, { status: "planning" });

        const finalState = await graph.invoke(initialState, {
          configurable: { thread_id: taskId },
        });

        // Update session with final state snapshot
        updateSession(taskId, {
          status: finalState.task_status ?? "complete",
          stateSnapshot: {
            coder_plan: finalState.coder_plan ?? null,
            analyst_state: finalState.analyst_state ?? "IDLE",
            sandbox_display: finalState.sandbox_display ?? "",
            reviewer_report_md: finalState.reviewer_report_md ?? "",
          },
        });

        logger.info("Swarm graph execution completed", {
          taskId,
          status: finalState.task_status,
        });
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : "Unknown error";
        logger.error("Swarm graph execution failed", { taskId, error: errMsg });

        updateSession(taskId, { status: "error" });
        notifier.emit("ERROR", "orchestrator", {
          error_type: "GRAPH_EXECUTION_FAILURE",
          message: errMsg,
        });
      }
    })();

    return NextResponse.json(
      {
        task_id: taskId,
        status: "pending",
        stream_url: `/api/swarm/${taskId}/stream`,
      },
      { status: 201 },
    );
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : "Unknown error";
    logger.error("Failed to create swarm task", { error: errMsg });
    return NextResponse.json(
      { error: "Internal server error", message: errMsg },
      { status: 500 },
    );
  }
}
