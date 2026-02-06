import { ChatAnthropic } from "@langchain/anthropic";
import { ChatOpenAI } from "@langchain/openai";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { ChatOllama } from "@langchain/ollama";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import type { LLMProvider } from "@/types/agent";

export function getModelForProvider(
  provider: LLMProvider,
  model: string,
  options: { apiKey?: string; baseUrl?: string } = {}
): BaseChatModel {
  switch (provider) {
    case "anthropic":
      return new ChatAnthropic({
        model,
        anthropicApiKey: options.apiKey || process.env.ANTHROPIC_API_KEY,
      });
    case "openai":
      return new ChatOpenAI({
        model,
        openAIApiKey: options.apiKey || process.env.OPENAI_API_KEY,
      });
    case "google":
      return new ChatGoogleGenerativeAI({
        model,
        apiKey: options.apiKey || process.env.GOOGLE_API_KEY,
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
