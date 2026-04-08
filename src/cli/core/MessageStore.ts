/**
 * MessageStore - Advanced state management for MindFlow CLI
 * Zustand store with message lookups and indexes
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  Message,
  AppState,
  ToolUseMessage,
  ToolResultMessage,
  ProgressMessage,
  Agent,
  SessionState,
} from '../types/protocol.js';

// Initial session state
const initialSession: SessionState = {
  id: crypto.randomUUID(),
  status: 'idle',
  permission_mode: 'default',
};

// Initial app state
const initialState: AppState = {
  messages: [],
  visibleRange: { start: 0, end: 50 },
  inProgressToolUseIDs: new Set(),
  resolvedToolUseIDs: new Set(),
  erroredToolUseIDs: new Set(),
  progressMessagesByToolUseID: new Map(),
  agents: new Map(),
  session: initialSession,
  isLoading: false,
  expandedView: 'none',
  connectionStatus: 'disconnected',
  selectedMessageIndex: null,
  inputValue: '',
  inputHistory: [],
  historyIndex: -1,
};

// Type for store actions
export interface MessageStoreActions {
  // Message actions
  addMessage: (message: Message) => void;
  updateMessage: (uuid: string, updates: Partial<Message>) => void;
  setMessages: (messages: Message[]) => void;
  clearMessages: () => void;
  
  // Tool tracking actions
  startToolUse: (toolUse: ToolUseMessage) => void;
  completeToolUse: (result: ToolResultMessage) => void;
  failToolUse: (toolUseId: string, error: string) => void;
  addProgressMessage: (progress: ProgressMessage) => void;
  
  // Tool tracking getters
  isToolInProgress: (toolUseId: string) => boolean;
  isToolResolved: (toolUseId: string) => boolean;
  isToolErrored: (toolUseId: string) => boolean;
  getProgressMessages: (toolUseId: string) => ProgressMessage[];
  
  // Agent actions
  addAgent: (agent: Agent) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  removeAgent: (id: string) => void;
  
  // Session actions
  updateSession: (updates: Partial<SessionState>) => void;
  setSessionStatus: (status: SessionState['status']) => void;
  setPermissionMode: (mode: SessionState['permission_mode']) => void;
  
  // UI actions
  setLoading: (isLoading: boolean) => void;
  setExpandedView: (view: AppState['expandedView']) => void;
  setConnectionStatus: (status: AppState['connectionStatus']) => void;
  setSelectedMessageIndex: (index: number | null) => void;
  setVisibleRange: (range: { start: number; end: number }) => void;
  
  // Input actions
  setInputValue: (value: string) => void;
  submitInput: () => void;
  navigateInputHistory: (direction: 'up' | 'down') => string;
}

// Combined store type
export type MessageStore = AppState & MessageStoreActions;

// Create the store
export const useMessageStore = create<MessageStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Message actions
      addMessage: (message) => {
        set((state) => ({
          messages: [...state.messages, message],
        }));
      },

      updateMessage: (uuid: string, updates: Partial<Message>) => {
        set((state: MessageStore) => ({
          messages: state.messages.map((msg) =>
            msg.uuid === uuid ? { ...msg, ...updates } as Message : msg
          ),
        }));
      },

      setMessages: (messages: Message[]) => {
        set({ messages });
      },

      clearMessages: () => {
        set({
          messages: [],
          inProgressToolUseIDs: new Set(),
          resolvedToolUseIDs: new Set(),
          erroredToolUseIDs: new Set(),
          progressMessagesByToolUseID: new Map(),
        });
      },

      // Tool tracking actions
      startToolUse: (toolUse) => {
        set((state) => {
          const inProgressToolUseIDs = new Set(state.inProgressToolUseIDs);
          inProgressToolUseIDs.add(toolUse.tool_use_id);
          return { inProgressToolUseIDs };
        });
      },

      completeToolUse: (result) => {
        set((state) => {
          const inProgressToolUseIDs = new Set(state.inProgressToolUseIDs);
          const resolvedToolUseIDs = new Set(state.resolvedToolUseIDs);
          
          inProgressToolUseIDs.delete(result.tool_use_id);
          resolvedToolUseIDs.add(result.tool_use_id);

          // If error, track it
          const erroredToolUseIDs = new Set(state.erroredToolUseIDs);
          if (result.is_error) {
            erroredToolUseIDs.add(result.tool_use_id);
          }

          return {
            inProgressToolUseIDs,
            resolvedToolUseIDs,
            erroredToolUseIDs,
          };
        });
      },

      failToolUse: (toolUseId, _error) => {
        set((state) => {
          const inProgressToolUseIDs = new Set(state.inProgressToolUseIDs);
          const erroredToolUseIDs = new Set(state.erroredToolUseIDs);
          
          inProgressToolUseIDs.delete(toolUseId);
          erroredToolUseIDs.add(toolUseId);

          return {
            inProgressToolUseIDs,
            erroredToolUseIDs,
          };
        });
      },

      addProgressMessage: (progress) => {
        set((state) => {
          const progressMessagesByToolUseID = new Map(state.progressMessagesByToolUseID);
          const existing = progressMessagesByToolUseID.get(progress.tool_use_id) || [];
          progressMessagesByToolUseID.set(progress.tool_use_id, [...existing, progress]);
          return { progressMessagesByToolUseID };
        });
      },

      // Tool tracking getters
      isToolInProgress: (toolUseId) => {
        return get().inProgressToolUseIDs.has(toolUseId);
      },

      isToolResolved: (toolUseId) => {
        return get().resolvedToolUseIDs.has(toolUseId);
      },

      isToolErrored: (toolUseId) => {
        return get().erroredToolUseIDs.has(toolUseId);
      },

      getProgressMessages: (toolUseId) => {
        return get().progressMessagesByToolUseID.get(toolUseId) || [];
      },

      // Agent actions
      addAgent: (agent) => {
        set((state) => {
          const agents = new Map(state.agents);
          agents.set(agent.id, agent);
          return { agents };
        });
      },

      updateAgent: (id, updates) => {
        set((state) => {
          const agents = new Map(state.agents);
          const agent = agents.get(id);
          if (agent) {
            agents.set(id, { ...agent, ...updates });
          }
          return { agents };
        });
      },

      removeAgent: (id) => {
        set((state) => {
          const agents = new Map(state.agents);
          agents.delete(id);
          return { agents };
        });
      },

      // Session actions
      updateSession: (updates) => {
        set((state) => ({
          session: { ...state.session, ...updates },
        }));
      },

      setSessionStatus: (status) => {
        set((state) => ({
          session: { ...state.session, status },
        }));
      },

      setPermissionMode: (mode) => {
        set((state) => ({
          session: { ...state.session, permission_mode: mode },
        }));
      },

      // UI actions
      setLoading: (isLoading) => {
        set({ isLoading });
      },

      setExpandedView: (expandedView) => {
        set({ expandedView });
      },

      setConnectionStatus: (connectionStatus) => {
        set({ connectionStatus });
      },

      setSelectedMessageIndex: (selectedMessageIndex) => {
        set({ selectedMessageIndex });
      },

      setVisibleRange: (visibleRange) => {
        set({ visibleRange });
      },

      // Input actions
      setInputValue: (inputValue) => {
        set({ inputValue });
      },

      submitInput: () => {
        const { inputValue, inputHistory } = get();
        if (!inputValue.trim()) return;

        // Add to history if not duplicate of last entry
        const newHistory =
          inputHistory.length > 0 && inputHistory[inputHistory.length - 1] === inputValue
            ? inputHistory
            : [...inputHistory, inputValue];

        set({
          inputValue: '',
          inputHistory: newHistory,
          historyIndex: -1,
        });
      },

      navigateInputHistory: (direction) => {
        const { inputHistory, historyIndex, inputValue } = get();
        
        if (inputHistory.length === 0) return inputValue;

        let newIndex: number;
        if (direction === 'up') {
          newIndex = historyIndex === -1 ? inputHistory.length - 1 : Math.max(0, historyIndex - 1);
        } else {
          newIndex = historyIndex === -1 ? -1 : Math.min(inputHistory.length - 1, historyIndex + 1);
          if (newIndex === inputHistory.length - 1 && historyIndex === inputHistory.length - 1) {
            newIndex = -1;
          }
        }

        set({ historyIndex: newIndex });
        return newIndex === -1 ? '' : inputHistory[newIndex];
      },
    }),
    {
      name: 'mindflow-cli-store',
    }
  )
);

// Selectors for optimized subscriptions
export const useMessages = () => useMessageStore((state) => state.messages);
export const useVisibleRange = () => useMessageStore((state) => state.visibleRange);
export const useInProgressToolUseIDs = () => useMessageStore((state) => state.inProgressToolUseIDs);
export const useAgents = () => useMessageStore((state) => state.agents);
export const useSession = () => useMessageStore((state) => state.session);
export const useIsLoading = () => useMessageStore((state) => state.isLoading);
export const useExpandedView = () => useMessageStore((state) => state.expandedView);
export const useConnectionStatus = () => useMessageStore((state) => state.connectionStatus);
export const useSelectedMessageIndex = () => useMessageStore((state) => state.selectedMessageIndex);
export const useInputValue = () => useMessageStore((state) => state.inputValue);
