// backend/schemas/agent.schema.ts
import "server-only";
import { z } from "zod";

export const llmProviderSchema = z.enum([
  "anthropic",
  "openai",
  "ollama",
  "google",
  "vertexai",
]);

export const agentChatRequestSchema = z.object({
  message: z
    .string()
    .min(1, "Message cannot be empty")
    .max(100_000, "Message too long"),
  provider: llmProviderSchema.optional(),
  model: z.string().optional(),
  conversationId: z.string().optional(),
  debugSteps: z.boolean().optional().default(false),
});

export const conversationCreateSchema = z.object({
  title: z.string().min(1).max(200).optional(),
});

export type AgentChatRequest = z.infer<typeof agentChatRequestSchema>;
export type ConversationCreate = z.infer<typeof conversationCreateSchema>;
