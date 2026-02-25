/**
 * Swarm-specific TypeScript interfaces and union types.
 * Pure types only — no Zod schemas. Schemas live in backend/schemas/.
 */

// ============================================================================
// Core Union Types
// ============================================================================

/** All notification event types emitted by swarm agents */
export type SwarmEventType =
  | "AGENT_STATE_CHANGE"
  | "TOKEN_STREAM"
  | "TOOL_CALL"
  | "TOOL_RESULT"
  | "FILE_CHANGE"
  | "PLAN_UPDATE"
  | "ANALYST_FINDING"
  | "ANALYST_STATE_CHANGE"
  | "REVIEW_FINDING"
  | "SANDBOX_UPDATE"
  | "ERROR";

/** Agent identifiers within the swarm */
export type SwarmAgentId =
  | "orchestrator"
  | "coder"
  | "live_analyst"
  | "reviewer"
  | "sandbox_renderer";

/** Live Analyst alert levels */
export type AnalystAlertLevel =
  | "IDLE"
  | "MONITORING"
  | "ALERT_LOW"
  | "ALERT_MODERATE"
  | "ALERT_CRITICAL";

/** Task lifecycle status */
export type TaskStatus =
  | "pending"
  | "planning"
  | "coding"
  | "reviewing"
  | "complete"
  | "error";

/** Reviewer overall assessment */
export type ReviewAssessment =
  | "APPROVED"
  | "APPROVED_WITH_SUGGESTIONS"
  | "CHANGES_REQUESTED";

// ============================================================================
// Entry Interfaces (for state list fields)
// ============================================================================

export interface TokenStreamEntry {
  token: string;
  timestamp: string;
}

export interface ToolCallEntry {
  name: string;
  input: Record<string, unknown>;
  output: unknown;
  timestamp: string;
}

export interface FileChangeEntry {
  filepath: string;
  action: "create" | "modify" | "delete";
  diff_summary: string;
}

export interface InterruptionRequest {
  urgency: "CRITICAL";
  issue: string;
  file: string;
  suggested_action: string;
  evidence: string;
}

export interface ReviewImprovement {
  category: string;
  filepath: string;
  line_range: string;
  description: string;
  improvement: string;
}

// ============================================================================
// Notification Event
// ============================================================================

export interface NotificationEvent {
  event_id: string;
  event_type: SwarmEventType;
  agent_id: SwarmAgentId;
  timestamp: string;
  payload: Record<string, unknown>;
  metadata: {
    task_id: string;
    sequence_number: number;
  };
}

// ============================================================================
// API Interfaces
// ============================================================================

export interface SwarmTaskSubmission {
  description: string;
  provider?: string;
  model?: string;
  workingPath?: string;
}

export interface SwarmTaskStatus {
  task_id: string;
  task_status: TaskStatus;
  coder_plan: string | null;
  analyst_state: AnalystAlertLevel;
  sandbox_display: string;
  notifications_count: number;
}
