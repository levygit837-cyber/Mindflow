import { NextRequest } from "next/server";
import { createOmniMindAgent } from "@/lib/agent";
import { createSSEStream } from "@/lib/agent/stream";
import { ensureDbInitialized } from "@/lib/db/init";
import type { LLMProvider, StreamEvent } from "@/types/agent";
import { HumanMessage } from "@langchain/core/messages";

export async function POST(request: NextRequest) {
  ensureDbInitialized();

  const body = await request.json();
  const { message, provider = "anthropic", model = "claude-sonnet-4-20250514", conversationId, noteContext } = body as {
    message: string;
    provider?: LLMProvider;
    model?: string;
    conversationId?: string;
    noteContext?: string[];
  };

  const { stream, send, close } = createSSEStream();

  // Run agent in background
  (async () => {
    try {
      // Build the message with optional note context
      let fullMessage = message;
      if (noteContext && noteContext.length > 0) {
        fullMessage = `[The user has selected the following notes for context: ${noteContext.join(", ")}]\n\n${message}`;
      }

      const agent = createOmniMindAgent(provider, model);
      const config = { configurable: { thread_id: conversationId || "default" } };

      // Stream events from the agent
      const eventStream = agent.streamEvents(
        { messages: [new HumanMessage(fullMessage)] },
        { ...config, version: "v2" }
      );

      let currentResponse = "";

      for await (const event of eventStream) {
        const { event: eventType, data } = event as { event: string; data: Record<string, unknown> };

        if (eventType === "on_chat_model_stream") {
          const chunk = data?.chunk as Record<string, unknown> | undefined;
          const content = chunk?.content;
          if (content) {
            const text = typeof content === "string"
              ? content
              : Array.isArray(content)
                ? (content as Record<string, unknown>[])
                    .filter((c) => c.type === "text")
                    .map((c) => String(c.text || ""))
                    .join("")
                : "";

            if (text) {
              currentResponse += text;
              send({ type: "response", data: text });
            }
          }

          // Check for thinking/reasoning content
          const kwargs = chunk?.additional_kwargs as Record<string, unknown> | undefined;
          if (kwargs?.thinking) {
            send({ type: "thought", data: String(kwargs.thinking) });
          }
        }

        if (eventType === "on_tool_start") {
          send({
            type: "tool_call",
            data: JSON.stringify({ name: data?.name || "unknown", args: data?.input }),
          });
        }

        if (eventType === "on_tool_end") {
          const output = data?.output;
          send({
            type: "tool_result",
            data: JSON.stringify({ result: typeof output === "string" ? output.slice(0, 500) : "Done" }),
          });
        }
      }

      send({ type: "done", data: "" });
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Unknown error";
      send({ type: "error", data: errMsg });
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
