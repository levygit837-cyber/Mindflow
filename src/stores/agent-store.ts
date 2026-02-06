import { create } from "zustand";
import type { LLMProvider, ToolCallInfo } from "@/types/agent";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thoughts: string;
  toolCalls: ToolCallInfo[];
  isStreaming: boolean;
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
  startAssistantMessage: () => string;
  appendToAssistant: (id: string, text: string) => void;
  appendThought: (id: string, thought: string) => void;
  addToolCall: (id: string, toolCall: ToolCallInfo) => void;
  finishAssistant: (id: string) => void;
  setLoading: (loading: boolean) => void;
  clearMessages: () => void;
}

let msgCounter = 0;

export const useAgentStore = create<AgentStore>((set) => ({
  messages: [],
  isLoading: false,
  provider: "anthropic",
  model: "claude-sonnet-4-20250514",
  conversationId: "default",
  noteContext: [],

  setProvider: (provider) => set({ provider }),
  setModel: (model) => set({ model }),
  setNoteContext: (noteIds) => set({ noteContext: noteIds }),

  addUserMessage: (content) => {
    const id = `msg-${++msgCounter}`;
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: "user", content, thoughts: "", toolCalls: [], isStreaming: false },
      ],
    }));
    return id;
  },

  startAssistantMessage: () => {
    const id = `msg-${++msgCounter}`;
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: "assistant", content: "", thoughts: "", toolCalls: [], isStreaming: true },
      ],
    }));
    return id;
  },

  appendToAssistant: (id, text) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + text } : m
      ),
    }));
  },

  appendThought: (id, thought) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, thoughts: m.thoughts + thought } : m
      ),
    }));
  },

  addToolCall: (id, toolCall) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, toolCalls: [...m.toolCalls, toolCall] } : m
      ),
    }));
  },

  finishAssistant: (id) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m
      ),
    }));
  },

  setLoading: (loading) => set({ isLoading: loading }),
  clearMessages: () => set({ messages: [] }),
}));
