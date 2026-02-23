"use client";

import { useCallback } from "react";
import { useAgentStore } from "@/stores/agent-store";
import type { StreamEvent } from "@/types/agent";
import type { NotifierType } from "@/types/agent";

function parseToolCallPayload(raw: string): { id?: string; name: string; args: Record<string, unknown> } | null {
  try {
    const parsed = JSON.parse(raw) as {
      id?: string;
      name?: string;
      args?: Record<string, unknown>;
    };
    if (!parsed?.name) return null;
    return {
      id: parsed.id,
      name: parsed.name,
      args: parsed.args ?? {},
    };
  } catch {
    return null;
  }
}

function parseToolResultPayload(raw: string): { id?: string; name?: string; result: string } | null {
  try {
    const parsed = JSON.parse(raw) as { id?: string; name?: string; result?: string };
    if (typeof parsed?.result !== "string") return null;
    return {
      id: parsed.id,
      name: parsed.name,
      result: parsed.result,
    };
  } catch {
    return null;
  }
}

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
              const event = JSON.parse(line.slice(6)) as StreamEvent;

              switch (event.type) {
                case "response":
                  store.cancelEmptyThinking(assistantId);
                  store.appendToAssistant(assistantId, event.data);
                  break;

                case "thought":
                  store.appendThought(assistantId, event.data);
                  break;

                case "tool_call": {
                  store.cancelEmptyThinking(assistantId);
                  const tc = parseToolCallPayload(event.data);
                  if (!tc) break;
                  store.addToolCall(assistantId, {
                    id: tc.id || event.meta?.toolCallId,
                    name: tc.name,
                    args: tc.args,
                  });
                  break;
                }

                case "tool_result": {
                  const tr = parseToolResultPayload(event.data);
                  if (!tr) break;
                  store.updateToolResult(
                    assistantId,
                    tr.id || event.meta?.toolCallId || "",
                    tr.result,
                    tr.name
                  );
                  break;
                }

                case "step":
                  store.addNotifier(
                    assistantId,
                    "state_change",
                    event.data,
                    event.meta?.node || event.mode
                  );
                  break;

                case "agent_step": {
                  try {
                    const stepData = JSON.parse(event.data) as {
                      stepName: string;
                      detail: string;
                      action?: "start" | "update" | "complete";
                      subStep?: string;
                      stepId?: string;
                    };
                    // Filtra nodes INTERNAL antes de exibir
                    if (stepData.detail?.includes("[INTERNAL]")) break;

                    if (stepData.action === "update" && stepData.stepId && stepData.subStep) {
                      store.updateAgentStep(assistantId, stepData.stepId, stepData.subStep);
                    } else if (stepData.action === "complete" && stepData.stepId) {
                      store.completeAgentStep(assistantId, stepData.stepId);
                    } else {
                      store.addAgentStep(assistantId, stepData.stepName, stepData.detail);
                    }
                  } catch {
                    // ignore malformed agent_step events
                  }
                  break;
                }

                case "notifier":
                  try {
                    const nd = JSON.parse(event.data) as {
                      notifierType: NotifierType;
                      label: string;
                      detail?: string;
                    };
                    store.addNotifier(assistantId, nd.notifierType, nd.label, nd.detail);
                  } catch {
                    // ignore malformed notifier events
                  }
                  break;

                case "error":
                  store.appendToAssistant(assistantId, `\n\nError: ${event.data}`);
                  break;

                case "done":
                  store.completeAllAgentSteps(assistantId);
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
