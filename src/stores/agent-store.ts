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

interface NotifierFilters {
  state_change: boolean;
  graph_transition: boolean;
  sub_graph: boolean;
  agent_start: boolean;
  agent_end: boolean;
  error: boolean;
  warning: boolean;
}

interface AgentStore {
  messages: ChatMessage[];
  isLoading: boolean;
  provider: LLMProvider;
  model: string;
  conversationId: string;
  noteContext: string[];
  notifierFilters: NotifierFilters;
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
  finishAssistant: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setNotifierFilter: (type: NotifierType, enabled: boolean) => void;
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
  conversationId: "default",
  noteContext: [],
  notifierFilters: {
    state_change: true,
    graph_transition: true,
    sub_graph: true,
    agent_start: true,
    agent_end: true,
    error: true,
    warning: true,
  },

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
          contentParts: [],
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
        const lastPart = parts[parts.length - 1];

        if (lastPart && lastPart.type === "text") {
          parts[parts.length - 1] = {
            ...lastPart,
            content: lastPart.content + text,
          };
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
        const lastPart = parts[parts.length - 1];

        if (lastPart && lastPart.type === "thinking") {
          parts[parts.length - 1] = {
            ...lastPart,
            content: lastPart.content + thought,
          };
        } else {
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

  setNotifierFilter: (type, enabled) =>
    set((state) => ({
      notifierFilters: { ...state.notifierFilters, [type]: enabled },
    })),

  clearMessages: () => set({ messages: [] }),
}));
