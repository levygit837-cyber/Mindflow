import { z } from "zod";

const configSchema = z.object({
  nodeEnv: z.enum(["development", "production", "test"]).default("development"),
  databaseUrl: z.string().optional(),
  defaultModel: z.string().default("gemini-3-flash-preview"),
  defaultTemperature: z.number().min(0).max(2).default(0.7),
  maxTokens: z.number().int().positive().default(8192),
  enableStreaming: z.boolean().default(true),
  logLevel: z.enum(["error", "warn", "info", "debug"]).default("info"),
});

function buildConfig() {
  try {
    return configSchema.parse({
      nodeEnv: process.env.NODE_ENV || "development",
      databaseUrl: process.env.DATABASE_URL,
      defaultModel: process.env.DEFAULT_MODEL || "gemini-3-flash-preview",
      defaultTemperature: process.env.DEFAULT_TEMPERATURE
        ? parseFloat(process.env.DEFAULT_TEMPERATURE)
        : 0.7,
      maxTokens: process.env.MAX_TOKENS
        ? parseInt(process.env.MAX_TOKENS, 10)
        : 8192,
      enableStreaming: process.env.ENABLE_STREAMING !== "false",
      logLevel: process.env.LOG_LEVEL || "info",
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error("Configuration validation error:", error.issues);
      throw new Error("Invalid configuration. Check environment variables.");
    }
    throw error;
  }
}

export const config = buildConfig();
export type Config = z.infer<typeof configSchema>;

export const isProduction = () => config.nodeEnv === "production";
export const isDevelopment = () => config.nodeEnv === "development";
export const isTest = () => config.nodeEnv === "test";

export default config;
