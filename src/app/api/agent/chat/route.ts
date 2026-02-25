import { NextRequest } from "next/server";
import { createOmniMindAgent, DEFAULT_PROVIDER, DEFAULT_MODEL } from "@backend/agent";
import { ensureDbInitialized } from "@backend/db/postgres";
import { createSSEStream } from "@backend/agent/stream";
import { createAgentChatStreamNormalizer } from "@backend/agent/chat-stream-normalizer";
import type { LLMProvider, StreamEvent, StreamEventType, StreamModeName } from "@shared/types/agent";
import { HumanMessage } from "@langchain/core/messages";
import { logBus } from "@backend/agent/log-bus";
import { agentChatRequestSchema } from "@backend/schemas/agent.schema";

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
    debugSteps: debugStepsRequested,
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
      await ensureDbInitialized();
      const agent = createOmniMindAgent(provider, model);
      const config = { configurable: { thread_id: conversationId || "default" } };

      const normalizer = createAgentChatStreamNormalizer({
        provider,
        emitUpdateSteps: true,
        emit,
      });

      const agentStream = await agent.stream(
        { messages: [new HumanMessage(message)] },
        {
          ...config,
          streamMode: ["messages", "updates", "values", "debug"],
        }
      );

      for await (const item of agentStream as AsyncIterable<unknown>) {
        normalizer.process(item);
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
