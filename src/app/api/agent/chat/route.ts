import { NextRequest } from "next/server";
import { spawn } from "node:child_process";
import { createSSEStream } from "@server/agent/stream";
import type { StreamEvent, StreamEventType, StreamModeName, LLMProvider } from "@shared/types/agent";
import { logBus } from "@server/agent/log-bus";
import { agentChatRequestSchema } from "@server/schemas/agent.schema";
import { createOmniMindAgent } from "@server/agent";
import { createAgentChatStreamNormalizer } from "@server/agent/chat-stream-normalizer";

const DEFAULT_PROVIDER = "vertexai";
const DEFAULT_MODEL = "gemini-3-flash-preview";



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
      const agent = createOmniMindAgent(
        provider as LLMProvider,
        model
      );

      const normalizer = createAgentChatStreamNormalizer({
        provider: provider as LLMProvider,
        emitUpdateSteps: true,
        emit,
        currentTurnRunId: sessionId,
      });

      const responseStream = await agent.stream(
        { messages: [{ role: "user", content: message }] },
        {
          configurable: {
            thread_id: sessionId,
          },
          streamMode: ["messages", "updates"],
        }
      );

      for await (const chunk of responseStream) {
        normalizer.process(chunk);
      }

      normalizer.flush();
      emit("done", "", "messages");

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
