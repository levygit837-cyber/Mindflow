// backend/schemas/swarm.schema.ts
import "server-only";
import { z } from "zod";
import { llmProviderSchema } from "./agent.schema";

export const swarmTaskSubmissionSchema = z.object({
  description: z
    .string()
    .min(1, "Task description is required")
    .max(10_000, "Task description must be at most 10000 characters"),
  provider: llmProviderSchema.optional(),
  model: z.string().optional(),
  workingPath: z.string().optional(),
});

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

export type SwarmTaskSubmissionInput = z.infer<typeof swarmTaskSubmissionSchema>;
export type NotificationEventInput = z.infer<typeof notificationEventSchema>;
