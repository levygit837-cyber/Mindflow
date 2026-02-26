// backend/config/index.ts
import "server-only";
import { z } from "zod";

const configSchema = z.object({
  // Server
  nodeEnv: z.enum(["development", "production", "test"]).default("development"),
  port: z.coerce.number().int().min(1).max(65535).default(3000),

  // Database
  databaseUrl: z.string().url().optional(),

  // Default LLM
  defaultProvider: z
    .enum(["anthropic", "openai", "ollama", "google", "vertexai"])
    .default("vertexai"),
  defaultModel: z.string().default("gemini-3-flash-preview"),
  defaultTemperature: z.coerce.number().min(0).max(2).default(0.7),
  maxTokens: z.coerce.number().int().positive().default(8192),
  enableStreaming: z.boolean().default(true),

  // LLM API Keys (optional — user can provide via Settings UI)
  anthropicApiKey: z.string().optional(),
  openaiApiKey: z.string().optional(),
  googleApiKey: z.string().optional(),
  ollamaBaseUrl: z.string().url().default("http://localhost:11434"),

  // Vertex AI
  vertexCredentialsPath: z.string().optional(),
  googleCloudProject: z.string().optional(),

  // Logging
  logLevel: z.enum(["error", "warn", "info", "debug"]).default("info"),

  // Search
  tavilyApiKey: z.string().optional(),
  searxngUrl: z.string().url().optional(),
});

function buildConfig() {
  try {
    return configSchema.parse({
      nodeEnv: process.env.NODE_ENV,
      port: process.env.PORT,
      databaseUrl: process.env.DATABASE_URL,
      defaultProvider: process.env.DEFAULT_PROVIDER,
      defaultModel: process.env.DEFAULT_MODEL,
      defaultTemperature: process.env.DEFAULT_TEMPERATURE,
      maxTokens: process.env.MAX_TOKENS,
      enableStreaming: process.env.ENABLE_STREAMING !== "false",
      anthropicApiKey: process.env.ANTHROPIC_API_KEY,
      openaiApiKey: process.env.OPENAI_API_KEY,
      googleApiKey: process.env.GOOGLE_API_KEY,
      ollamaBaseUrl: process.env.OLLAMA_BASE_URL,
      vertexCredentialsPath:
        process.env.GOOGLE_APPLICATION_CREDENTIALS ||
        process.env.VERTEXAI_CREDENTIALS_PATH,
      googleCloudProject:
        process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT,
      logLevel: process.env.LOG_LEVEL,
      tavilyApiKey: process.env.TAVILY_API_KEY,
      searxngUrl: process.env.SEARXNG_URL,
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
