import dotenv from 'dotenv';
import { z } from 'zod';

// Load environment variables
dotenv.config();

// Define configuration schema with Zod for validation
const configSchema = z.object({
  // Server Configuration
  server: z.object({
    nodeEnv: z.enum(['development', 'production', 'test']).default('development'),
    port: z.number().int().positive().default(8000),
    host: z.string().default('localhost'),
  }),

  // API Keys
  apiKeys: z.object({
    openai: z.string().optional(),
    anthropic: z.string().optional(),
    cohere: z.string().optional(),
    deep: z.string().optional(),
    huggingface: z.string().optional(),
  }),

  // Database
  database: z.object({
    url: z.string().optional(),
  }),

  // Security
  security: z.object({
    jwtSecret: z.string().min(32),
    jwtExpiration: z.string().default('24h'),
    encryptionKey: z.string().optional(),
    sessionSecret: z.string().optional(),
  }),

  // CORS
  cors: z.object({
    origin: z.string().or(z.array(z.string())).default('http://localhost:3000'),
  }),

  // Logging
  logging: z.object({
    level: z.enum(['error', 'warn', 'info', 'http', 'verbose', 'debug', 'silly']).default('info'),
  }),

  // Rate Limiting
  rateLimit: z.object({
    windowMs: z.number().int().positive().default(900000), // 15 minutes
    maxRequests: z.number().int().positive().default(100),
  }),

  // External APIs
  externalApis: z.object({
    serpApi: z.string().optional(),
    tavilyApi: z.string().optional(),
  }),

  // LangSmith (for monitoring)
  langsmith: z.object({
    tracingEnabled: z.boolean().default(false),
    endpoint: z.string().default('https://api.smith.langchain.com'),
    apiKey: z.string().optional(),
    project: z.string().default('omnimind'),
  }),

  // Redis
  redis: z.object({
    url: z.string().optional(),
  }),

  // File Upload
  fileUpload: z.object({
    maxFileSize: z.number().int().positive().default(10485760), // 10MB
  }),

  // Agent Configuration
  agent: z.object({
    defaultModel: z.string().default('chat-deepseek'),
    defaultTemperature: z.number().min(0).max(2).default(0.7),
    maxTokens: z.number().int().positive().default(4096),
  }),

  // Feature Flags
  features: z.object({
    enableStreaming: z.boolean().default(true),
    enableMemory: z.boolean().default(true),
    enableTools: z.boolean().default(true),
  }),
});

// Parse CORS origin (can be comma-separated string)
const parseCorsOrigin = (origin: string | undefined): string | string[] => {
  if (!origin) return 'http://localhost:3000';
  if (origin.includes(',')) {
    return origin.split(',').map((o) => o.trim());
  }
  return origin;
};

// Parse boolean from string
const parseBoolean = (value: string | undefined, defaultValue: boolean): boolean => {
  if (!value) return defaultValue;
  return value.toLowerCase() === 'true';
};

// Build configuration object from environment variables
const buildConfig = () => {
  try {
    return configSchema.parse({
      server: {
        nodeEnv: process.env.NODE_ENV || 'development',
        port: process.env.PORT ? parseInt(process.env.PORT, 10) : 8000,
        host: process.env.HOST || 'localhost',
      },
      apiKeys: {
        openai: process.env.OPENAI_API_KEY,
        anthropic: process.env.ANTHROPIC_API_KEY,
        cohere: process.env.COHERE_API_KEY,
        huggingface: process.env.HUGGINGFACE_API_KEY,
        deeekseek: process.env.DEEP_API_KEY,
      },
      database: {
        url: process.env.DATABASE_URL,
      },
      security: {
        jwtSecret: process.env.JWT_SECRET || 'your_super_secret_jwt_key_change_this_in_production',
        jwtExpiration: process.env.JWT_EXPIRATION || '24h',
        encryptionKey: process.env.ENCRYPTION_KEY,
        sessionSecret: process.env.SESSION_SECRET,
      },
      cors: {
        origin: parseCorsOrigin(process.env.CORS_ORIGIN),
      },
      logging: {
        level: (process.env.LOG_LEVEL || 'info') as any,
      },
      rateLimit: {
        windowMs: process.env.RATE_LIMIT_WINDOW_MS
          ? parseInt(process.env.RATE_LIMIT_WINDOW_MS, 10)
          : 900000,
        maxRequests: process.env.RATE_LIMIT_MAX_REQUESTS
          ? parseInt(process.env.RATE_LIMIT_MAX_REQUESTS, 10)
          : 100,
      },
      externalApis: {
        serpApi: process.env.SERP_API_KEY,
        tavilyApi: process.env.TAVILY_API_KEY,
      },
      langsmith: {
        tracingEnabled: parseBoolean(process.env.LANGCHAIN_TRACING_V2, false),
        endpoint: process.env.LANGCHAIN_ENDPOINT || 'https://api.smith.langchain.com',
        apiKey: process.env.LANGCHAIN_API_KEY,
        project: process.env.LANGCHAIN_PROJECT || 'omnimind',
      },
      redis: {
        url: process.env.REDIS_URL,
      },
      fileUpload: {
        maxFileSize: process.env.MAX_FILE_SIZE ? parseInt(process.env.MAX_FILE_SIZE, 10) : 10485760,
      },
      agent: {
        defaultModel: process.env.DEFAULT_MODEL || 'gpt-4-turbo-preview',
        defaultTemperature: process.env.DEFAULT_TEMPERATURE
          ? parseFloat(process.env.DEFAULT_TEMPERATURE)
          : 0.7,
        maxTokens: process.env.MAX_TOKENS ? parseInt(process.env.MAX_TOKENS, 10) : 4096,
      },
      features: {
        enableStreaming: parseBoolean(process.env.ENABLE_STREAMING, true),
        enableMemory: parseBoolean(process.env.ENABLE_MEMORY, true),
        enableTools: parseBoolean(process.env.ENABLE_TOOLS, true),
      },
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('Configuration validation error:', error.errors);
      throw new Error('Invalid configuration. Please check your environment variables.');
    }
    throw error;
  }
};

// Export the configuration
export const config = buildConfig();

// Export type for TypeScript
export type Config = z.infer<typeof configSchema>;

// Helper function to check if we're in production
export const isProduction = () => config.server.nodeEnv === 'production';

// Helper function to check if we're in development
export const isDevelopment = () => config.server.nodeEnv === 'development';

// Helper function to check if we're in test
export const isTest = () => config.server.nodeEnv === 'test';

// Validate required environment variables
export const validateRequiredEnvVars = () => {
  const missing: string[] = [];

  // Check for at least one LLM API key in production
  if (isProduction()) {
    const hasApiKey =
      config.apiKeys.deep ||
      config.apiKeys.anthropic ||
      config.apiKeys.cohere ||
      config.apiKeys.huggingface;

    if (!hasApiKey) {
      missing.push('At least one LLM API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)');
    }

    if (config.security.jwtSecret === 'your_super_secret_jwt_key_change_this_in_production') {
      missing.push('JWT_SECRET (must be changed from default in production)');
    }
  }

  if (missing.length > 0) {
    throw new Error(`Missing required environment variables:\n- ${missing.join('\n- ')}`);
  }
};

// Export default
export default config;
