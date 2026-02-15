import { beforeEach, describe, expect, it } from "vitest";
import { useAgentStore } from "@/stores/agent-store";

function resetStore() {
  useAgentStore.setState((state) => ({
    ...state,
    messages: [],
    isLoading: false,
    noteContext: [],
  }));
}

describe("agent-store tool sequencing", () => {
  beforeEach(() => {
    resetStore();
  });

  it("updates the correct tool call by toolCallId when names repeat", () => {
    const store = useAgentStore.getState();
    const assistantId = store.startAssistantMessage();

    store.addToolCall(assistantId, {
      id: "tc-1",
      name: "read_note",
      args: { noteId: "a" },
    });

    store.addToolCall(assistantId, {
      id: "tc-2",
      name: "read_note",
      args: { noteId: "b" },
    });

    store.updateToolResult(assistantId, "tc-2", "result-b", "read_note");

    const message = useAgentStore.getState().messages.find((m) => m.id === assistantId);
    expect(message).toBeDefined();

    const toolParts = message?.contentParts.filter((p) => p.type === "tool_call") ?? [];
    expect(toolParts).toHaveLength(2);

    const first = toolParts[0];
    const second = toolParts[1];

    if (first?.type !== "tool_call" || second?.type !== "tool_call") {
      throw new Error("Expected tool_call parts");
    }

    expect(first.toolCallId).toBe("tc-1");
    expect(first.status).toBe("running");
    expect(first.result).toBeUndefined();

    expect(second.toolCallId).toBe("tc-2");
    expect(second.status).toBe("success");
    expect(second.result).toBe("result-b");
  });

  it("keeps timeline order: thinking then tool call, and closes streaming thinking", () => {
    const store = useAgentStore.getState();
    const assistantId = store.startAssistantMessage();

    store.appendThought(assistantId, "planejando...");
    store.addToolCall(assistantId, {
      id: "tc-3",
      name: "search_notes",
      args: { query: "arquitetura" },
    });

    const message = useAgentStore.getState().messages.find((m) => m.id === assistantId);
    expect(message).toBeDefined();

    const parts = message?.contentParts ?? [];
    expect(parts[0]?.type).toBe("thinking");
    expect(parts[1]?.type).toBe("tool_call");

    const thinking = parts[0];
    if (thinking?.type !== "thinking") {
      throw new Error("Expected first part to be thinking");
    }

    expect(thinking.isStreaming).toBe(false);
  });
});
