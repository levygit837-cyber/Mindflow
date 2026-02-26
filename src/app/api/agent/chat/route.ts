import { NextRequest } from "next/server";
import { spawn } from "node:child_process";
import { createSSEStream } from "@server/agent/stream";
import type { StreamEvent, StreamEventType, StreamModeName } from "@shared/types/agent";
import { logBus } from "@server/agent/log-bus";
import { agentChatRequestSchema } from "@server/schemas/agent.schema";

const DEFAULT_PROVIDER = "vertexai";
const DEFAULT_MODEL = "gemini-3-flash-preview";

interface RuntimeEvent {
  type: StreamEventType;
  data: string;
  mode: StreamModeName;
  meta?: StreamEvent["meta"];
}

function buildPythonPath(): string {
  const localPythonPath = `${process.cwd()}/python`;
  return process.env.PYTHONPATH ? `${localPythonPath}:${process.env.PYTHONPATH}` : localPythonPath;
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const parsed = agentChatRequestSchema.safeParse(body);
  if (!parsed.success) {
    return new Response(
      JSON.stringify({ error: "Invalid request", details: parsed.error.flatten().fieldErrors }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  const {
    message,
    provider = DEFAULT_PROVIDER,
    model = DEFAULT_MODEL,
    conversationId,
  } = parsed.data;

  const { stream, send, close } = createSSEStream();

  (async () => {
    let seq = 0;
    const sessionId = conversationId || `session-${Date.now()}`;

    const emit = (
      type: StreamEventType,
      data: string,
      mode: StreamModeName,
      meta: StreamEvent["meta"] = {}
    ) => {
      const event: StreamEvent = {
        id: `evt-${Date.now()}-${seq + 1}`,
        seq: ++seq,
        type,
        mode,
        data,
        meta: {
          provider,
          model,
          ...meta,
        },
      };
      send(event);
      logBus.publish(event, sessionId);
    };

    try {
      const pythonBin = process.env.OMNIMIND_PYTHON_BIN || "python3";
      const child = spawn(
        pythonBin,
        ["-m", "omnimind_agents.runtime.chat_runner"],
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
          message,
          provider,
          model,
          conversationId,
        })
      );
      child.stdin.end();

      let stdoutBuffer = "";
      let stderrBuffer = "";

      child.stdout.on("data", (chunk) => {
        stdoutBuffer += chunk.toString();
        const lines = stdoutBuffer.split("\n");
        stdoutBuffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const runtimeEvent = JSON.parse(trimmed) as RuntimeEvent;
            emit(
              runtimeEvent.type,
              runtimeEvent.data,
              runtimeEvent.mode,
              runtimeEvent.meta || {}
            );
          } catch {
            // ignore malformed stdout lines from runtime
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

      if (stdoutBuffer.trim().length > 0) {
        try {
          const runtimeEvent = JSON.parse(stdoutBuffer.trim()) as RuntimeEvent;
          emit(
            runtimeEvent.type,
            runtimeEvent.data,
            runtimeEvent.mode,
            runtimeEvent.meta || {}
          );
        } catch {
          // ignore trailing malformed line
        }
      }

      if (exitCode !== 0) {
        const errMsg = stderrBuffer.trim() || "Python runtime failed";
        emit("error", errMsg, "custom");
      }
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Unknown error";
      emit("error", errMsg, "custom");
    } finally {
      close();
    }
  })();

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
