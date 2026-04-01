import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { AppState, Message, AgentState, ToolCall, ExpandedView } from '../types';

export const useAppStore = create<AppState>()(
  devtools(
    (set) => ({
      // Initial state
      messages: [],
      agents: {},
      toolCalls: {},
      isLoading: false,
      expandedView: 'none',
      connectionStatus: 'disconnected',

      // Message actions
      addMessage: (message: Message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      // Agent actions
      updateAgent: (agentId: string, updates: Partial<AgentState>) =>
        set((state) => ({
          agents: {
            ...state.agents,
            [agentId]: {
              ...state.agents[agentId],
              ...updates,
            } as AgentState,
          },
        })),

      // Tool actions
      startToolCall: (toolCall: ToolCall) =>
        set((state) => ({
          toolCalls: {
            ...state.toolCalls,
            [toolCall.id]: toolCall,
          },
        })),

      completeToolCall: (toolCallId: string, output?: string, error?: string) =>
        set((state) => {
          const toolCall = state.toolCalls[toolCallId];
          if (!toolCall) return state;

          const endTime = Date.now();
          return {
            toolCalls: {
              ...state.toolCalls,
              [toolCallId]: {
                ...toolCall,
                status: error ? 'failed' : 'completed',
                endTime,
                duration: endTime - toolCall.startTime,
                output,
                error,
              },
            },
          };
        }),

      // UI actions
      setExpandedView: (view: ExpandedView) =>
        set({ expandedView: view }),

      setConnectionStatus: (status) =>
        set({ connectionStatus: status }),

      clearMessages: () =>
        set({ messages: [] }),
    }),
    {
      name: 'mindflow-cli-store',
    }
  )
);

// Selectors for optimized subscriptions
export const useMessages = () => useAppStore((state) => state.messages);
export const useAgents = () => useAppStore((state) => state.agents);
export const useToolCalls = () => useAppStore((state) => state.toolCalls);
export const useConnectionStatus = () => useAppStore((state) => state.connectionStatus);
