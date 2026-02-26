import { create } from "zustand";
import type {
  SwarmAgentId,
  SwarmEventType,
  TaskStatus,
  AnalystAlertLevel,
  NotificationEvent,
} from "@shared/types/swarm";
import type { LLMProvider } from "@shared/types/agent";

interface SwarmStore {
  // Connection state
  taskId: string | null;
  isConnected: boolean;

  // Task state (driven by SSE events)
  taskStatus: TaskStatus;
  coderPlan: string;
  coderTokens: string;
  analystState: AnalystAlertLevel;
  analystReport: string;
  sandboxDisplay: string;
  reviewerReport: string;
  notifications: NotificationEvent[];

  // Model selection
  provider: LLMProvider;
  model: string;
  workingPath: string;

  // Filters
  agentFilter: SwarmAgentId | null;
  eventTypeFilter: SwarmEventType | null;

  // Actions
  submitTask: (
    description: string,
    provider?: string,
    model?: string,
    workingPath?: string
  ) => Promise<string | null>;
  setTaskId: (taskId: string | null) => void;
  setConnected: (connected: boolean) => void;
  updateFromEvent: (event: NotificationEvent) => void;
  disconnect: () => void;
  setAgentFilter: (filter: SwarmAgentId | null) => void;
  setEventTypeFilter: (filter: SwarmEventType | null) => void;
  clearState: () => void;
  setProvider: (provider: LLMProvider) => void;
  setModel: (model: string) => void;
  setWorkingPath: (path: string) => void;

  // Computed
  filteredNotifications: () => NotificationEvent[];
}

const MAX_NOTIFICATIONS = 500;

const initialState = {
  taskId: null as string | null,
  isConnected: false,
  taskStatus: "pending" as TaskStatus,
  coderPlan: "",
  coderTokens: "",
  analystState: "IDLE" as AnalystAlertLevel,
  analystReport: "",
  sandboxDisplay: "",
  reviewerReport: "",
  notifications: [] as NotificationEvent[],
  provider: "anthropic" as LLMProvider,
  model: "claude-sonnet-4-20250514",
  workingPath: "",
  agentFilter: null as SwarmAgentId | null,
  eventTypeFilter: null as SwarmEventType | null,
};

export const useSwarmStore = create<SwarmStore>((set, get) => ({
  ...initialState,

  submitTask: async (description, provider, model, workingPath) => {
    try {
      const res = await fetch("/api/swarm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description, provider, model, workingPath }),
      });

      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`HTTP ${res.status}: ${errBody}`);
      }

      const data = await res.json();
      const taskId = data.task_id as string;
      set({ taskId, taskStatus: "pending" });
      return taskId;
    } catch {
      return null;
    }
  },

  setTaskId: (taskId) => set({ taskId }),
  setConnected: (connected) => set({ isConnected: connected }),

  updateFromEvent: (event) => {
    set((state) => {
      const updates: Partial<SwarmStore> = {};

      // Append to notifications (capped)
      const next = [...state.notifications, event];
      updates.notifications = next.length > MAX_NOTIFICATIONS
        ? next.slice(next.length - MAX_NOTIFICATIONS)
        : next;

      // Route event to the appropriate field
      switch (event.event_type) {
        case "TOKEN_STREAM": {
          const token = (event.payload.token as string) ?? "";
          updates.coderTokens = state.coderTokens + token;
          break;
        }

        case "AGENT_STATE_CHANGE": {
          const newState = event.payload.new_state as string | undefined;
          if (newState) {
            // Map agent state changes to task status
            if (newState === "planning") updates.taskStatus = "planning";
            else if (newState === "coding") updates.taskStatus = "coding";
            else if (newState === "reviewing") updates.taskStatus = "reviewing";
            else if (newState === "complete") updates.taskStatus = "complete";
            else if (newState === "error") updates.taskStatus = "error";
          }
          // Reviewer includes report_md in its final state change event
          if (event.agent_id === "reviewer") {
            const report = event.payload.report_md as string | undefined;
            if (report) {
              updates.reviewerReport = report;
            }
          }
          break;
        }

        case "PLAN_UPDATE": {
          const detail = event.payload.detail as string | undefined;
          if (detail) {
            updates.coderPlan = detail;
          }
          break;
        }

        case "ANALYST_FINDING":
        case "ANALYST_STATE_CHANGE": {
          if (event.event_type === "ANALYST_STATE_CHANGE") {
            const newLevel = event.payload.new_state as AnalystAlertLevel | undefined;
            if (newLevel) {
              updates.analystState = newLevel;
            }
          }
          // Both event types may carry report content
          const report = event.payload.report_md as string | undefined;
          if (report) {
            updates.analystReport = report;
          }
          break;
        }

        case "SANDBOX_UPDATE": {
          const content = event.payload.content as string | undefined;
          if (content) {
            updates.sandboxDisplay = content;
          }
          break;
        }

        case "REVIEW_FINDING": {
          // Individual findings are tracked in notifications; full report
          // comes via AGENT_STATE_CHANGE from the reviewer with report_md.
          break;
        }

        case "ERROR": {
          updates.taskStatus = "error";
          break;
        }
      }

      return updates;
    });
  },

  disconnect: () => set({ isConnected: false }),

  setAgentFilter: (filter) => set({ agentFilter: filter }),
  setEventTypeFilter: (filter) => set({ eventTypeFilter: filter }),

  clearState: () => set((state) => ({
    ...initialState,
    provider: state.provider,
    model: state.model,
    workingPath: state.workingPath,
  })),
  setProvider: (provider) => set({ provider }),
  setModel: (model) => set({ model }),
  setWorkingPath: (workingPath) => set({ workingPath }),

  filteredNotifications: () => {
    const { notifications, agentFilter, eventTypeFilter } = get();
    return notifications.filter((n) => {
      if (agentFilter && n.agent_id !== agentFilter) return false;
      if (eventTypeFilter && n.event_type !== eventTypeFilter) return false;
      return true;
    });
  },
}));
