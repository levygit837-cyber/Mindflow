import { LLMProvider } from "./agent";

export interface AppSettings {
  defaultProvider: LLMProvider;
  defaultModel: string;
  anthropicApiKey: string;
  openaiApiKey: string;
  googleApiKey: string;
  ollamaBaseUrl: string;
}

export const DEFAULT_SETTINGS: AppSettings = {
  defaultProvider: "anthropic",
  defaultModel: "claude-sonnet-4-20250514",
  anthropicApiKey: "",
  openaiApiKey: "",
  googleApiKey: "",
  ollamaBaseUrl: "http://localhost:11434",
};

export const PROVIDER_MODELS: Record<LLMProvider, string[]> = {
  anthropic: [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-haiku-3-5-20241022",
  ],
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
  google: ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-flash"],
  ollama: ["llama3.1:8b", "qwen3:8b", "karan333/whisper:latest", "llama3.1", "mistral", "codellama"],
};
