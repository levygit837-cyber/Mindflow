/**
 * Swarm-specific types and Zod schemas for ZenCoder Multi-Agent Swarm
 *
 * Defines all event types, agent identifiers, state types, and validation
 * schemas used throughout the swarm orchestration system.
 */

import { z } from "zod";

// ============================================================================
// Core Union Types
// ============================================================================

/**
 * All notification event types emitted by swarm agents
 */
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

/**
 * Agent identifiers within the swarm
 */
export type SwarmAgentId =
  | "orchestrator"
  | "coder"
  | "live_analyst"
  | "reviewer"
  | "sandbox_renderer";

/**
 * Live Analyst alert levels (stealth monitoring state machine)
 */
export type AnalystAlertLevel =
  | "IDLE"
  | "MONITORING"
  | "ALERT_LEVE"
  | "ALERT_MODERADO"
  | "ALERT_CRITICO";

/**
 * Task lifecycle status
 */
export type TaskStatus =
  | "pending"
  | "planning"
  | "coding"
  | "reviewing"
  | "complete"
  | "error";

/**
 * Reviewer overall assessment
 */
export type ReviewAssessment =
  | "APPROVED"
  | "APPROVED_WITH_SUGGESTIONS"
  | "CHANGES_REQUESTED";

// ============================================================================
// Entry Interfaces (for state list fields)
// ============================================================================

/**
 * A single token in the coder's stream buffer
 */
export interface TokenStreamEntry {
  token: string;
  timestamp: string;
}

/**
 * A recorded tool call with its result
 */
export interface ToolCallEntry {
  name: string;
  input: Record<string, unknown>;
  output: unknown;
  timestamp: string;
}

/**
 * A file modification made by the coder
 */
export interface FileChangeEntry {
  filepath: string;
  action: "create" | "modify" | "delete";
  diff_summary: string;
}

/**
 * An interruption request raised by the analyst (CRITICAL severity)
 */
export interface InterruptionRequest {
  urgency: "CRITICAL";
  issue: string;
  file: string;
  suggested_action: string;
  evidence: string;
}

/**
 * A structured improvement from the reviewer
 */
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

/**
 * Structured notification event emitted by any swarm agent
 */
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

/**
 * Payload for submitting a new swarm task
 */
export interface SwarmTaskSubmission {
  description: string;
  provider?: string;
  model?: string;
  workingPath?: string;
}

/**
 * Status snapshot returned by the GET /api/swarm/[taskId] endpoint
 */
export interface SwarmTaskStatus {
  task_id: string;
  task_status: TaskStatus;
  coder_plan: string | null;
  analyst_state: AnalystAlertLevel;
  sandbox_display: string;
  notifications_count: number;
}

// ============================================================================
// Zod Schemas
// ============================================================================

/**
 * Validates incoming swarm task submissions
 */
export const swarmTaskSubmissionSchema = z.object({
  description: z
    .string()
    .min(1, "Task description is required")
    .max(10000, "Task description must be at most 10000 characters"),
  provider: z.string().optional(),
  model: z.string().optional(),
  workingPath: z.string().optional(),
});

/**
 * Validates the structure of a notification event
 */
export const notificationEventSchema = z.object({
  event_id: z.string().uuid(),
  event_type: z.enum([
    "AGENT_STATE_CHANGE",
    "TOKEN_STREAM",
    "TOOL_CALL",
    "TOOL_RESULT",
    "FILE_CHANGE",
    "PLAN_UPDATE",
    "ANALYST_FINDING",
    "ANALYST_STATE_CHANGE",
    "REVIEW_FINDING",
    "SANDBOX_UPDATE",
    "ERROR",
  ]),
  agent_id: z.enum([
    "orchestrator",
    "coder",
    "live_analyst",
    "reviewer",
    "sandbox_renderer",
  ]),
  timestamp: z.string().datetime(),
  payload: z.record(z.string(), z.unknown()),
  metadata: z.object({
    task_id: z.string(),
    sequence_number: z.number().int().nonnegative(),
  }),
});
