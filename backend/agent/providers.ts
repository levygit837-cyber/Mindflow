import "server-only";
import { ChatVertexAI } from "@langchain/google-vertexai";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { ChatAnthropic } from "@langchain/anthropic";
import { ChatOpenAI } from "@langchain/openai";
import { ChatOllama } from "@langchain/ollama";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import type { LLMProvider } from "@shared/types/agent";
import fs from "fs";

function getVertexProjectId(): string | undefined {
  const credentialsPath =
    process.env.VERTEXAI_CREDENTIALS_PATH ||
    process.env.GOOGLE_APPLICATION_CREDENTIALS;

  if (!credentialsPath) return undefined;

  try {
    const raw = fs.readFileSync(credentialsPath, "utf8");
    const parsed = JSON.parse(raw) as { project_id?: string };
    return parsed.project_id;
  } catch {
    return undefined;
  }
}

function getVertexLocation(model: string): string {
  if (model.startsWith("gemini-3")) return "global";
  return "us-central1";
}

function ensureVertexEnv(): void {
  const credentialsPath =
    process.env.VERTEXAI_CREDENTIALS_PATH ||
    process.env.GOOGLE_APPLICATION_CREDENTIALS;

  if (credentialsPath && !process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    if (fs.existsSync(credentialsPath)) {
      process.env.GOOGLE_APPLICATION_CREDENTIALS = credentialsPath;
    }
  }

  const projectId = getVertexProjectId();
  if (projectId) {
    process.env.GOOGLE_CLOUD_PROJECT ??= projectId;
    process.env.GCLOUD_PROJECT ??= projectId;
  }
}

export const DEFAULT_PROVIDER: LLMProvider = "vertexai";
export const DEFAULT_MODEL = "gemini-3-flash-preview";

export function getModelForProvider(
  provider: LLMProvider,
  model: string,
  options: { apiKey?: string; baseUrl?: string } = {}
): BaseChatModel {
  switch (provider) {
    case "vertexai": {
      ensureVertexEnv();
      return new ChatVertexAI({
        model,
        location: getVertexLocation(model),
        reasoningEffort: "high",
        apiKey: options.apiKey || process.env.API_KEY || process.env.GOOGLE_API_KEY,
      });
    }

    case "google":
      return new ChatGoogleGenerativeAI({
        model,
        apiKey: options.apiKey || process.env.GOOGLE_API_KEY,
        thinkingConfig: {
          includeThoughts: true,
          thinkingLevel: "HIGH",
        },
      });

    case "anthropic": {
      const config: ConstructorParameters<typeof ChatAnthropic>[0] = {
        model,
        anthropicApiKey: options.apiKey || process.env.ANTHROPIC_API_KEY,
      };
      const m = model.toLowerCase();
      if (m.includes("claude-sonnet-4") || m.includes("claude-opus-4")) {
        config.thinking = { type: "adaptive" };
      }
      return new ChatAnthropic(config);
    }

    case "openai":
      return new ChatOpenAI({
        model,
        openAIApiKey: options.apiKey || process.env.OPENAI_API_KEY,
      });

    case "ollama":
      return new ChatOllama({
        model,
        baseUrl: options.baseUrl || process.env.OLLAMA_BASE_URL || "http://localhost:11434",
      });

    default:
      throw new Error(`Unknown provider: ${provider}`);
  }
}
