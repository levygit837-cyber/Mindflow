"use client";

import { useCallback } from "react";
import { useAgentStore } from "@/stores/agent-store";
import type { StreamEvent } from "@/types/agent";

export function useAgentChat() {
  const store = useAgentStore();

  const sendMessage = useCallback(
    async (message: string) => {
      store.addUserMessage(message);
      store.setLoading(true);
      const assistantId = store.startAssistantMessage();

      try {
        const res = await fetch("/api/agent/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            provider: store.provider,
            model: store.model,
            conversationId: store.conversationId,
            noteContext: store.noteContext,
          }),
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event: StreamEvent = JSON.parse(line.slice(6));

              switch (event.type) {
                case "response":
                  store.appendToAssistant(assistantId, event.data);
                  break;
                case "thought":
                  store.appendThought(assistantId, event.data);
                  break;
                case "tool_call":
                  try {
                    const tc = JSON.parse(event.data);
                    store.addToolCall(assistantId, { name: tc.name, args: tc.args });
                  } catch {
                    // ignore parse errors
                  }
                  break;
                case "tool_result":
                  try {
                    const tr = JSON.parse(event.data);
                    const toolCalls = useAgentStore.getState().messages.find((m) => m.id === assistantId)?.toolCalls;
                    if (toolCalls && toolCalls.length > 0) {
                      const lastTc = toolCalls[toolCalls.length - 1];
                      lastTc.result = tr.result;
                    }
                  } catch {
                    // ignore
                  }
                  break;
                case "error":
                  store.appendToAssistant(assistantId, `\n\nError: ${event.data}`);
                  break;
                case "done":
                  break;
              }
            } catch {
              // ignore malformed events
            }
          }
        }
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : "Unknown error";
        store.appendToAssistant(assistantId, `\n\nError: ${errMsg}`);
      } finally {
        store.finishAssistant(assistantId);
        store.setLoading(false);
      }
    },
    [store]
  );

  return {
    messages: store.messages,
    isLoading: store.isLoading,
    provider: store.provider,
    model: store.model,
    sendMessage,
    setProvider: store.setProvider,
    setModel: store.setModel,
    setNoteContext: store.setNoteContext,
    clearMessages: store.clearMessages,
  };
}
