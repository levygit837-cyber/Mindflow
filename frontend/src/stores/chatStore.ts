import { create } from 'zustand';
import {
  AgentType,
  ChatMessage,
  ChatSession,
  DelegationEvent,
  StreamEvent,
  ThinkingEvent,
  ToolCallEvent,
} from '../types/backend';

export interface ChatState {
  // Sessions
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;

  // Messages
  messages: ChatMessage[];

  // Events for UI components
  thinkingEvents: Map<string, ThinkingEvent>;
  toolCallEvents: Map<string, ToolCallEvent>;
  delegationEvents: Map<string, DelegationEvent>;
  activeStreamings: Map<AgentType, { text: string; progress?: number }>;
  thinkingStreamings: Set<AgentType>;

  // Streaming state
  isStreaming: boolean;
  currentAgent: AgentType | null;

  // Actions
  setSessions: (sessions: ChatSession[]) => void;
  setCurrentSession: (sessionId: string) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;

  // Event handlers
  handleStreamEvent: (event: StreamEvent) => void;
  addThinkingEvent: (event: ThinkingEvent) => void;
  updateThinkingEvent: (id: string, updates: Partial<ThinkingEvent>) => void;
  addToolCallEvent: (event: ToolCallEvent) => void;
  updateToolCallEvent: (id: string, updates: Partial<ToolCallEvent>) => void;
  addDelegationEvent: (event: DelegationEvent) => void;
  setStreamingState: (agentType: AgentType, text: string, progress?: number) => void;
  clearStreamingState: (agentType?: AgentType) => void;

  // State setters
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  setCurrentAgent: (agent: AgentType | null) => void;

  // Cleanup
  clearEvents: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  sessions: [],
  currentSessionId: null,
  isLoading: false,
  error: null,
  messages: [],
  thinkingEvents: new Map(),
  toolCallEvents: new Map(),
  delegationEvents: new Map(),
  activeStreamings: new Map(),
  thinkingStreamings: new Set(),
  isStreaming: false,
  currentAgent: null,

  // Session actions
  setSessions: (sessions) => set({ sessions }),

  setCurrentSession: (sessionId) =>
    set({
      currentSessionId: sessionId,
      messages: [],
      thinkingEvents: new Map(),
      toolCallEvents: new Map(),
      delegationEvents: new Map(),
      thinkingStreamings: new Set(),
    }),

  // Message actions
  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...updates } : msg
      ),
    })),

  // Stream event handler - routes events to appropriate handlers
  handleStreamEvent: (event) => {
    const state = get();
    const agentType = event.meta?.agent || 'orchestrator';

    // Stable key for accumulating thinking per agent within a turn
    const THINKING_KEY = `thinking-${agentType}`;

    switch (event.type) {
      // Thinking events — accumulate into one block per agent; skip empty signals
      case 'thought':
      case 'orchestrator_thinking_start':
      case 'orchestrator_thinking':
      case 'orchestrator_thinking_end':
      case 'specialist_thinking': {
        if (!event.data.trim()) break; // skip empty marker events

        // Add to thinking streamings when thinking starts
        if (event.type === 'orchestrator_thinking_start' || event.type === 'thought') {
          set((state) => {
            const newSet = new Set(state.thinkingStreamings);
            newSet.add(agentType as AgentType);
            return { thinkingStreamings: newSet };
          });
        }

        // Remove from thinking streamings when thinking ends
        if (event.type === 'orchestrator_thinking_end') {
          set((state) => {
            const newSet = new Set(state.thinkingStreamings);
            newSet.delete(agentType as AgentType);
            return { thinkingStreamings: newSet };
          });
        }

        const existing = get().thinkingEvents.get(THINKING_KEY);
        if (existing) {
          state.updateThinkingEvent(THINKING_KEY, {
            reasoning: existing.reasoning + '\n' + event.data,
            status: 'update',
          });
        } else {
          state.addThinkingEvent({
            id: THINKING_KEY,
            agentType: agentType as AgentType,
            reasoning: event.data,
            isExpanded: true,
            timestamp: new Date(),
            status: 'update',
          });
        }
        break;
      }

      // Tool call events
      case 'tool_call':
      case 'tool_operation_start': {
        try {
          const toolData = JSON.parse(event.data);
          // Use toolCallId from parsed data as the stable key so results can match
          const toolId = toolData.id || event.meta?.toolCallId || event.id;
          state.addToolCallEvent({
            id: toolId,
            agentType: agentType as AgentType,
            toolName: toolData.name || toolData.tool || 'unknown',
            status: 'running',
            input: toolData.args || {},
            timestamp: new Date(),
          });
        } catch {
          state.addToolCallEvent({
            id: event.id,
            agentType: agentType as AgentType,
            toolName: event.data || 'unknown',
            status: 'running',
            input: {},
            timestamp: new Date(),
          });
        }
        break;
      }

      case 'tool_result':
      case 'tool_operation_complete': {
        try {
          const resultData = JSON.parse(event.data);
          // Match by toolCallId from data, fallback to event.id
          const toolId = resultData.id || event.meta?.toolCallId || event.id;
          state.updateToolCallEvent(toolId, {
            status: resultData.error ? 'error' : 'success',
            output: resultData.result,
            error: resultData.error,
          });
        } catch {
          state.updateToolCallEvent(event.id, {
            status: 'success',
            output: event.data,
          });
        }
        break;
      }

      // Delegation events
      case 'agent_delegation_start':
        try {
          const delegationData = JSON.parse(event.data);
          state.addDelegationEvent({
            id: event.id,
            fromAgent: (delegationData.from_agent || agentType) as AgentType,
            toAgent: delegationData.to_agent as AgentType,
            strategy: delegationData.strategy || 'single',
            tools: delegationData.tools || [],
            context: delegationData.context || '',
            timestamp: new Date(),
          });
        } catch {
          // Simple delegation without full data
          state.addDelegationEvent({
            id: event.id,
            fromAgent: agentType as AgentType,
            toAgent: 'coder',
            strategy: 'single',
            tools: [],
            context: event.data,
            timestamp: new Date(),
          });
        }
        break;

      case 'agent_delegation_complete':
        // Could update a delegation status here
        break;

      // Streaming/coding events
      case 'agent_execution_start':
        set({ isStreaming: true, currentAgent: agentType as AgentType });
        break;

      case 'initialization':
        // Visual feedback for initialization (cold starts)
        console.log('Agent initialization:', event.data);
        break;

      case 'response':
        if (state.isStreaming) {
          state.setStreamingState(
            agentType as AgentType,
            event.data,
            event.meta?.status === 'end' ? 100 : undefined
          );
        }
        break;

      case 'done':
        set({ isStreaming: false, currentAgent: null });
        state.clearStreamingState();
        break;

      case 'error':
        set({ isStreaming: false, error: event.data });
        break;

      default:
        // Handle other event types or log unhandled
        console.log('Unhandled event type:', event.type, event);
    }
  },

  // Event actions
  addThinkingEvent: (event) =>
    set((state) => {
      const newMap = new Map(state.thinkingEvents);
      newMap.set(event.id, event);
      return { thinkingEvents: newMap };
    }),

  updateThinkingEvent: (id, updates) =>
    set((state) => {
      const newMap = new Map(state.thinkingEvents);
      const existing = newMap.get(id);
      if (existing) {
        newMap.set(id, { ...existing, ...updates });
      }
      return { thinkingEvents: newMap };
    }),

  addToolCallEvent: (event) =>
    set((state) => {
      const newMap = new Map(state.toolCallEvents);
      newMap.set(event.id, event);
      return { toolCallEvents: newMap };
    }),

  updateToolCallEvent: (id, updates) =>
    set((state) => {
      const newMap = new Map(state.toolCallEvents);
      const existing = newMap.get(id);
      if (existing) {
        newMap.set(id, { ...existing, ...updates });
      }
      return { toolCallEvents: newMap };
    }),

  addDelegationEvent: (event) =>
    set((state) => {
      const newMap = new Map(state.delegationEvents);
      newMap.set(event.id, event);
      return { delegationEvents: newMap };
    }),

  // Streaming actions
  setStreamingState: (agentType, text, progress) =>
    set((state) => {
      const newMap = new Map(state.activeStreamings);
      newMap.set(agentType, { text, progress });
      return { activeStreamings: newMap };
    }),

  clearStreamingState: (agentType) =>
    set((state) => {
      if (agentType) {
        const newMap = new Map(state.activeStreamings);
        newMap.delete(agentType);
        return { activeStreamings: newMap };
      }
      return { activeStreamings: new Map() };
    }),

  // State setters
  setIsLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setCurrentAgent: (currentAgent) => set({ currentAgent }),

  // Cleanup
  clearEvents: () =>
    set({
      thinkingEvents: new Map(),
      toolCallEvents: new Map(),
      delegationEvents: new Map(),
      activeStreamings: new Map(),
      thinkingStreamings: new Set(),
    }),
}));

export default useChatStore;
