import { create } from 'zustand';
import { useShallow } from 'zustand/react/shallow';
import { devtools, persist } from 'zustand/middleware';
import { DEFAULT_PROVIDER, getDefaultModelForProvider } from '../utils/llm';
import type { 
  AppState, 
  Agent, 
  AgentType, 
  AgentStatus, 
  Session, 
  Message, 
  StreamEvent,
  AppSettings
} from '../types';

interface AppStore extends AppState {
  // Session refresh tick (incremented to trigger sidebar re-fetch)
  sessionRefreshTick: number;
  bumpSessionRefresh: () => void;

  // Agent actions
  setAgents: (agents: Agent[]) => void;
  setActiveAgent: (agentType: AgentType | null) => void;
  setAgentStatus: (agentType: AgentType, status: AgentStatus) => void;
  updateAgentStats: (agentType: AgentType, stats: Partial<Agent['stats']>) => void;
  
  // Session actions
  setSessions: (sessions: Session[]) => void;
  setCurrentSession: (session: Session | null) => void;
  addSession: (session: Session) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  deleteSession: (sessionId: string) => void;
  
  // Message actions
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;
  deleteMessage: (messageId: string) => void;
  
  // Streaming actions
  setStreaming: (isStreaming: boolean) => void;
  addStreamEvent: (event: StreamEvent) => void;
  clearStreamEvents: () => void;
  
  // UI actions
  setSidebarOpen: (open: boolean) => void;
  setReasoningPanelOpen: (open: boolean) => void;
  setSettingsPanelOpen: (open: boolean) => void;
  setTheme: (theme: 'dark' | 'light') => void;
  
  // Settings actions
  setSettings: (settings: Partial<AppSettings>) => void;
  
  // Reset actions
  resetCurrentSession: () => void;
  resetStore: () => void;
}

const defaultSettings: AppSettings = {
  provider: DEFAULT_PROVIDER,
  model: getDefaultModelForProvider(DEFAULT_PROVIDER),
  orchestrationMode: 'auto_route',
  autoSaveSessions: true,
  showReasoning: true,
  enableNotifications: true,
  fontSize: 'large',
  language: 'en',
};

const initialState: Omit<AppState, 'settings'> = {
  agents: [],
  activeAgent: null,
  agentStatus: {
    coder: 'offline',
    analyst: 'offline',
    researcher: 'offline',
    arch_tech: 'offline',
    critic: 'offline',
    creative: 'offline',
    security_guard: 'offline',
  },
  
  sessions: [],
  currentSession: null,
  messages: [],
  isStreaming: false,
  streamingEvents: [],
  
  sidebarOpen: true,
  reasoningPanelOpen: false,
  settingsPanelOpen: false,
  theme: 'dark',
};

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set) => ({
        ...initialState,
        settings: defaultSettings,
        sessionRefreshTick: 0,
        bumpSessionRefresh: () => set((state) => ({ sessionRefreshTick: state.sessionRefreshTick + 1 })),

        // Agent actions
        setAgents: (agents) => set({ agents }),
        
        setActiveAgent: (agentType) => set({ activeAgent: agentType }),
        
        setAgentStatus: (agentType, status) => 
          set((state) => ({
            agentStatus: {
              ...state.agentStatus,
              [agentType]: status,
            },
          })),
          
        updateAgentStats: (agentType, stats) =>
          set((state) => ({
            agents: state.agents.map((agent) =>
              agent.id === agentType
                ? {
                    ...agent,
                    stats: {
                      successRate: agent.stats?.successRate || 0,
                      avgResponseTime: agent.stats?.avgResponseTime || 0,
                      totalTasks: agent.stats?.totalTasks || 0,
                      lastActive: agent.stats?.lastActive || '',
                      ...stats,
                    },
                  }
                : agent
            ),
          })),
        
        // Session actions
        setSessions: (sessions) => set({ sessions }),
        
        setCurrentSession: (session) => 
          set({ 
            currentSession: session,
            messages: session?.messages || [],
          }),
          
        addSession: (session) =>
          set((state) => ({
            sessions: [session, ...state.sessions],
          })),
          
        updateSession: (sessionId, updates) =>
          set((state) => ({
            sessions: state.sessions.map((session) =>
              session.id === sessionId
                ? { ...session, ...updates, updatedAt: new Date().toISOString() }
                : session
            ),
            currentSession:
              state.currentSession?.id === sessionId
                ? { ...state.currentSession, ...updates, updatedAt: new Date().toISOString() }
                : state.currentSession,
          })),
          
        deleteSession: (sessionId) =>
          set((state) => ({
            sessions: state.sessions.filter((session) => session.id !== sessionId),
            currentSession:
              state.currentSession?.id === sessionId ? null : state.currentSession,
          })),
        
        // Message actions
        setMessages: (messages) => set({ messages }),
        
        addMessage: (message) =>
          set((state) => ({
            messages: [...state.messages, message],
            currentSession: state.currentSession
              ? {
                  ...state.currentSession,
                  messages: [...state.currentSession.messages, message],
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),
          
        updateMessage: (messageId, updates) =>
          set((state) => ({
            messages: state.messages.map((message) =>
              message.id === messageId ? { ...message, ...updates } : message
            ),
            currentSession: state.currentSession
              ? {
                  ...state.currentSession,
                  messages: state.currentSession.messages.map((message) =>
                    message.id === messageId ? { ...message, ...updates } : message
                  ),
                }
              : null,
          })),
          
        deleteMessage: (messageId) =>
          set((state) => ({
            messages: state.messages.filter((message) => message.id !== messageId),
            currentSession: state.currentSession
              ? {
                  ...state.currentSession,
                  messages: state.currentSession.messages.filter(
                    (message) => message.id !== messageId
                  ),
                }
              : null,
          })),
        
        // Streaming actions
        setStreaming: (isStreaming) => set({ isStreaming }),
        
        addStreamEvent: (event) =>
          set((state) => ({
            streamingEvents: [...state.streamingEvents, event],
          })),
          
        clearStreamEvents: () => set({ streamingEvents: [] }),
        
        // UI actions
        setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
        
        setReasoningPanelOpen: (reasoningPanelOpen) => set({ reasoningPanelOpen }),
        
        setSettingsPanelOpen: (settingsPanelOpen) => set({ settingsPanelOpen }),
        
        setTheme: (theme) =>
          set((state) => ({
            theme,
            settings: {
              ...state.settings,
              theme,
            },
          })),
        
        // Settings actions
        setSettings: (newSettings) =>
          set((state) => ({
            settings: { ...state.settings, ...newSettings },
          })),
        
        // Reset actions
        resetCurrentSession: () =>
          set({
            currentSession: null,
            messages: [],
            streamingEvents: [],
            isStreaming: false,
          }),
          
        resetStore: () =>
          set({
            ...initialState,
            settings: defaultSettings,
          }),
      }),
      {
        name: 'mindflow-store',
        partialize: (state) => ({
          settings: state.settings,
          theme: state.theme,
          sidebarOpen: state.sidebarOpen,
          reasoningPanelOpen: state.reasoningPanelOpen,
          // Don't persist sessions, messages, or streaming state
        }),
      }
    ),
    {
      name: 'mindflow-store',
    }
  )
);

// Selectors for optimized re-renders
export const useAgents = () => useAppStore((state) => state.agents);
export const useActiveAgent = () => useAppStore((state) => state.activeAgent);
export const useAgentStatus = () => useAppStore((state) => state.agentStatus);
export const useSessions = () => useAppStore((state) => state.sessions);
export const useCurrentSession = () => useAppStore((state) => state.currentSession);
export const useMessages = () => useAppStore((state) => state.messages);
export const useStreamingState = () => useAppStore(useShallow((state) => ({
  isStreaming: state.isStreaming,
  streamingEvents: state.streamingEvents,
})));
export const useUIState = () => useAppStore(useShallow((state) => ({
  sidebarOpen: state.sidebarOpen,
  reasoningPanelOpen: state.reasoningPanelOpen,
  settingsPanelOpen: state.settingsPanelOpen,
  theme: state.theme,
})));
export const useSettings = () => useAppStore((state) => state.settings);
