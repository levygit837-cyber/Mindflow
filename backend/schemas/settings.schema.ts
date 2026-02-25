// backend/schemas/settings.schema.ts
import "server-only";
import { z } from "zod";
import { llmProviderSchema } from "./agent.schema";

export const appSettingsSchema = z.object({
  defaultProvider: llmProviderSchema,
  defaultModel: z.string().min(1),
  anthropicApiKey: z.string().default(""),
  openaiApiKey: z.string().default(""),
  googleApiKey: z.string().default(""),
  ollamaBaseUrl: z
    .string()
    .url("Must be a valid URL")
    .default("http://localhost:11434"),
});

export const settingsUpdateSchema = appSettingsSchema.partial();

export type AppSettingsInput = z.infer<typeof appSettingsSchema>;
export type SettingsUpdate = z.infer<typeof settingsUpdateSchema>;
