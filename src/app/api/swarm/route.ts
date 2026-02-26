/**
 * POST /api/swarm — Submit a new swarm task.
 *
 * Validates the request body, creates a new task session, starts the
 * swarm graph in the background, and returns the task ID + stream URL.
 */

import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import { v4 as uuidv4 } from "uuid";
import { swarmTaskSubmissionSchema } from "@server/schemas/swarm.schema";
import type { SwarmAgentId, SwarmEventType } from "@shared/types/swarm";
import { registerSession, updateSession } from "@server/swarm/registry";
import { NotifierService } from "@server/swarm/notifier";
import { createLogger } from "@server/utils/logger";

const logger = createLogger("api:swarm");

type SwarmRuntimeLine =
  | {
      kind: "event";
      event_type: SwarmEventType;
      agent_id: SwarmAgentId;
      payload: Record<string, unknown>;
    }
  | {
      kind: "status";
      status: "pending" | "planning" | "coding" | "reviewing" | "complete" | "error";
    }
  | {
      kind: "complete";
      status: "complete" | "error";
      stateSnapshot: {
        coder_plan: string | null;
        analyst_state: string;
        sandbox_display: string;
        reviewer_report_md: string;
      };
    }
  | {
      kind: "error";
      message: string;
    };

function buildPythonPath(): string {
  const localPythonPath = `${process.cwd()}/python`;
  return process.env.PYTHONPATH ? `${localPythonPath}:${process.env.PYTHONPATH}` : localPythonPath;
}

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

    const notifier = new NotifierService(taskId);

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

    // Start python runtime execution in background (non-blocking)
    (async () => {
      try {
        logger.info("Starting swarm python runtime execution", { taskId });
        updateSession(taskId, { status: "planning" });

        const pythonBin = process.env.OMNIMIND_PYTHON_BIN || "python3";
        const child = spawn(
          pythonBin,
          ["-m", "omnimind_agents.runtime.swarm_runner"],
          {
            cwd: process.cwd(),
            env: {
              ...process.env,
              PYTHONPATH: buildPythonPath(),
            },
            stdio: ["pipe", "pipe", "pipe"],
          }
        );

        child.stdin.write(
          JSON.stringify({
            taskId,
            description,
            provider,
            model,
            workingPath,
          })
        );
        child.stdin.end();

        let stdoutBuffer = "";
        let stderrBuffer = "";
        let runtimeStatus: "pending" | "planning" | "coding" | "reviewing" | "complete" | "error" = "planning";
        let runtimeCompleted = false;

        child.stdout.on("data", (chunk) => {
          stdoutBuffer += chunk.toString();
          const lines = stdoutBuffer.split("\n");
          stdoutBuffer = lines.pop() || "";

          for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) continue;

            try {
              const event = JSON.parse(line) as SwarmRuntimeLine;
              if (event.kind === "event") {
                notifier.emit(event.event_type, event.agent_id, event.payload);
                continue;
              }

              if (event.kind === "status") {
                runtimeStatus = event.status;
                updateSession(taskId, { status: event.status });
                continue;
              }

              if (event.kind === "complete") {
                runtimeCompleted = true;
                runtimeStatus = event.status;
                updateSession(taskId, {
                  status: event.status,
                  stateSnapshot: event.stateSnapshot,
                });
                continue;
              }

              if (event.kind === "error") {
                runtimeStatus = "error";
                updateSession(taskId, { status: "error" });
                notifier.emit("ERROR", "orchestrator", {
                  error_type: "PYTHON_RUNTIME_ERROR",
                  message: event.message,
                });
              }
            } catch {
              // ignore malformed runtime line
            }
          }
        });

        child.stderr.on("data", (chunk) => {
          stderrBuffer += chunk.toString();
        });

        const exitCode = await new Promise<number>((resolve) => {
          child.on("close", (code) => resolve(code ?? 1));
          child.on("error", () => resolve(1));
        });

        if (exitCode !== 0) {
          const message = stderrBuffer.trim() || "Python runtime exited with non-zero code";
          updateSession(taskId, { status: "error" });
          notifier.emit("ERROR", "orchestrator", {
            error_type: "PYTHON_RUNTIME_EXIT",
            message,
          });
          notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {
            old_state: "coding",
            new_state: "error",
            terminal: true,
            detail: message,
          });
          return;
        }

        if (runtimeStatus === "error") {
          notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {
            old_state: "coding",
            new_state: "error",
            terminal: true,
            detail: "Swarm python runtime signaled error",
          });
          return;
        }

        if (!runtimeCompleted) {
          updateSession(taskId, { status: "complete" });
        }

        notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {
          old_state: "reviewing",
          new_state: "complete",
          terminal: true,
          detail: "Swarm python runtime completed",
        });

        logger.info("Swarm python runtime execution completed", { taskId });
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : "Unknown error";
        logger.error("Swarm python runtime execution failed", { taskId, error: errMsg });

        updateSession(taskId, { status: "error" });
        notifier.emit("ERROR", "orchestrator", {
          error_type: "PYTHON_RUNTIME_EXCEPTION",
          message: errMsg,
        });
        notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {
          old_state: "coding",
          new_state: "error",
          terminal: true,
          detail: errMsg,
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
