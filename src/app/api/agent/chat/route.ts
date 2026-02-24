import { NextRequest } from "next/server";
import { createOmniMindAgent, DEFAULT_PROVIDER, DEFAULT_MODEL } from "@/lib/agent";
import { ensureDbInitialized } from "@/lib/db/postgres";
import { createSSEStream } from "@/lib/agent/stream";
import { createAgentChatStreamNormalizer } from "@/lib/agent/chat-stream-normalizer";
import type { LLMProvider, StreamEvent, StreamEventType, StreamModeName } from "@/types/agent";
import { HumanMessage } from "@langchain/core/messages";
import { logBus } from "@/lib/agent/log-bus";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const debugStepsRequested = body?.debugSteps === true;
  const {
    message,
    provider = DEFAULT_PROVIDER,
    model = DEFAULT_MODEL,
    conversationId,
  } = body as {
    message: string;
    provider?: LLMProvider;
    model?: string;
    conversationId?: string;
  };

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
