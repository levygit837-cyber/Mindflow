import { create } from "zustand";
import type {
  LLMProvider,
  ToolCallInfo,
  ContentPart,
  NotifierType,
} from "@/types/agent";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thoughts: string;
  toolCalls: ToolCallInfo[];
  isStreaming: boolean;
  contentParts: ContentPart[];
  agentId?: string;
  agentColor?: string;
}

interface AgentStore {
  messages: ChatMessage[];
  isLoading: boolean;
  provider: LLMProvider;
  model: string;
  conversationId: string;
  noteContext: string[];
  setProvider: (provider: LLMProvider) => void;
  setModel: (model: string) => void;
  setNoteContext: (noteIds: string[]) => void;
  addUserMessage: (content: string) => string;
  startAssistantMessage: (agentId?: string, agentColor?: string) => string;
  appendToAssistant: (id: string, text: string) => void;
  appendThought: (id: string, thought: string) => void;
  addToolCall: (id: string, toolCall: ToolCallInfo) => void;
  updateToolResult: (messageId: string, toolCallId: string, result: string, toolName?: string) => void;
  addNotifier: (messageId: string, notifierType: NotifierType, label: string, detail?: string) => void;
  addAgentStep: (messageId: string, stepName: string, detail: string) => void;
  updateAgentStep: (messageId: string, stepId: string, subStep: string) => void;
  completeAgentStep: (messageId: string, stepId: string) => void;
  completeAllAgentSteps: (messageId: string) => void;
  cancelEmptyThinking: (messageId: string) => void;
  finishAssistant: (id: string) => void;
  setLoading: (loading: boolean) => void;
  clearMessages: () => void;
}

let msgCounter = 0;
let partCounter = 0;
let toolCallCounter = 0;

function nextPartId(): string {
  return `part-${++partCounter}`;
}

function nextToolCallId(): string {
  return `tool-${++toolCallCounter}`;
}

export const useAgentStore = create<AgentStore>((set) => ({
  messages: [],
  isLoading: false,
  provider: "vertexai",
  model: "gemini-3-flash-preview",
  conversationId: `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
  noteContext: [],

  setProvider: (provider) => set({ provider }),
  setModel: (model) => set({ model }),
  setNoteContext: (noteIds) => set({ noteContext: noteIds }),

  addUserMessage: (content) => {
    const id = `msg-${++msgCounter}`;
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "user",
          content,
          thoughts: "",
          toolCalls: [],
          isStreaming: false,
          contentParts: [{ type: "text", id: nextPartId(), content }],
        },
      ],
    }));
    return id;
  },

  startAssistantMessage: (agentId?: string, agentColor?: string) => {
    const id = `msg-${++msgCounter}`;
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "assistant",
          content: "",
          thoughts: "",
          toolCalls: [],
          isStreaming: true,
          contentParts: [
            {
              type: "thinking" as const,
              id: nextPartId(),
              content: "",
              isStreaming: true,
            },
          ],
          agentId,
          agentColor,
        },
      ],
    }));
    return id;
  },

  appendToAssistant: (id, text) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== id) return m;

        const parts = [...m.contentParts];

        // Find the last text part anywhere in the array
        let lastTextIdx = -1;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === "text") {
            lastTextIdx = i;
            break;
          }
        }

        if (lastTextIdx >= 0) {
          // Append to the existing text part
          const existing = parts[lastTextIdx];
          if (existing.type === "text") {
            parts[lastTextIdx] = {
              ...existing,
              content: existing.content + text,
            };
          }
        } else {
          parts.push({ type: "text", id: nextPartId(), content: text });
        }

        return {
          ...m,
          content: m.content + text,
          contentParts: parts,
        };
      }),
    }));
  },

  appendThought: (id, thought) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== id) return m;

        const parts = [...m.contentParts];

        // Find the last thinking part anywhere in the array (not just the very last part)
        let lastThinkingIdx = -1;
        for (let i = parts.length - 1; i >= 0; i--) {
          const p = parts[i];
          if (p.type === "thinking" && p.isStreaming) {
            lastThinkingIdx = i;
            break;
          }
        }

        if (lastThinkingIdx >= 0) {
          // Append to the existing streaming thinking part
          const existing = parts[lastThinkingIdx];
          if (existing.type === "thinking") {
            parts[lastThinkingIdx] = {
              ...existing,
              content: existing.content + thought,
            };
          }
        } else {
          // Check if the last part is a finished thinking block — start a new one
          parts.push({
            type: "thinking",
            id: nextPartId(),
            content: thought,
            isStreaming: true,
          });
        }

        return {
          ...m,
          thoughts: m.thoughts + thought,
          contentParts: parts,
        };
      }),
    }));
  },

  addToolCall: (id, toolCall) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== id) return m;

        const parts = [...m.contentParts];

        const lastPart = parts[parts.length - 1];
        if (lastPart && lastPart.type === "thinking" && lastPart.isStreaming) {
          parts[parts.length - 1] = { ...lastPart, isStreaming: false };
        }

        const toolCallId = toolCall.id || nextToolCallId();

        parts.push({
          type: "tool_call",
          id: nextPartId(),
          toolCallId,
          name: toolCall.name,
          args: toolCall.args,
          result: toolCall.result,
          status: "running",
          startedAt: new Date().toISOString(),
        });

        return {
          ...m,
          toolCalls: [...m.toolCalls, { ...toolCall, id: toolCallId }],
          contentParts: parts,
        };
      }),
    }));
  },

  updateToolResult: (messageId, toolCallId, result, toolName) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;

        const updatedToolCalls = m.toolCalls.map((tc, i, arr) => {
          if (toolCallId && tc.id === toolCallId && !tc.result) {
            return { ...tc, result };
          }

          if (!toolCallId && toolName && tc.name === toolName && !tc.result) {
            const isLast = arr
              .slice(i + 1)
              .every((t) => t.name !== toolName || t.result !== undefined);
            if (isLast) return { ...tc, result };
          }

          return tc;
        });

        const parts = [...m.contentParts];
        for (let i = parts.length - 1; i >= 0; i--) {
          const part = parts[i];
          if (part.type !== "tool_call" || part.status !== "running") continue;

          const byId = Boolean(toolCallId) && part.toolCallId === toolCallId;
          const byName = !toolCallId && toolName && part.name === toolName;
          if (!byId && !byName) continue;

          parts[i] = {
            ...part,
            result,
            status: "success",
            completedAt: new Date().toISOString(),
          };
          break;
        }

        return {
          ...m,
          toolCalls: updatedToolCalls,
          contentParts: parts,
        };
      }),
    }));
  },

  addNotifier: (messageId, notifierType, label, detail) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;

        const parts = [...m.contentParts];
        parts.push({
          type: "notifier",
          id: nextPartId(),
          notifierType,
          label,
          detail,
          timestamp: new Date().toISOString(),
        });

        return { ...m, contentParts: parts };
      }),
    }));
  },

  cancelEmptyThinking: (messageId) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;

        const parts = m.contentParts.map((part) => {
          if (part.type === "thinking" && part.isStreaming && !part.content) {
            return { ...part, isStreaming: false };
          }
          return part;
        });

        return { ...m, contentParts: parts };
      }),
    }));
  },

  addAgentStep: (messageId, stepName, detail) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;

        const parts = [...m.contentParts];
        parts.push({
          type: "agent_step",
          id: nextPartId(),
          stepName,
          detail,
          status: "running",
          startedAt: new Date().toISOString(),
          subSteps: [],
        });

        return { ...m, contentParts: parts };
      }),
    }));
  },

  updateAgentStep: (messageId, stepId, subStep) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;

        const parts = m.contentParts.map((part) => {
          if (part.type === "agent_step" && part.id === stepId) {
            return { ...part, subSteps: [...part.subSteps, subStep] };
          }
          return part;
        });

        return { ...m, contentParts: parts };
      }),
    }));
  },

  completeAgentStep: (messageId, stepId) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;

        const parts = m.contentParts.map((part) => {
          if (part.type === "agent_step" && part.id === stepId) {
            return {
              ...part,
              status: "completed" as const,
              completedAt: new Date().toISOString(),
            };
          }
          return part;
        });

        return { ...m, contentParts: parts };
      }),
    }));
  },

  completeAllAgentSteps: (messageId) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;

        const now = new Date().toISOString();
        const parts = m.contentParts.map((part) => {
          if (part.type === "agent_step" && part.status === "running") {
            return { ...part, status: "completed" as const, completedAt: now };
          }
          return part;
        });

        return { ...m, contentParts: parts };
      }),
    }));
  },

  finishAssistant: (id) => {
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== id) return m;

        const parts = m.contentParts.map((part) => {
          if (part.type === "thinking" && part.isStreaming) {
            return { ...part, isStreaming: false };
          }
          return part;
        });

        return { ...m, isStreaming: false, contentParts: parts };
      }),
    }));
  },

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [] }),
}));
