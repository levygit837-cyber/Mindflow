import "server-only";
import { createOmniMindDeepAgent } from "./deep-agent-config";
import { getModelForProvider, DEFAULT_PROVIDER, DEFAULT_MODEL } from "./providers";
import { buildStaticSystemPrompt } from "./prompts/dynamic-prompt";
import type { LLMProvider } from "@shared/types/agent";

export function createOmniMindAgent(
  provider: LLMProvider = DEFAULT_PROVIDER,
  model: string = DEFAULT_MODEL,
  options: { apiKey?: string; baseUrl?: string } = {}
) {
  const llm = getModelForProvider(provider, model, options);

  return createOmniMindDeepAgent({
    model: llm,
    systemPrompt: buildStaticSystemPrompt(),
  });
}

export { DEFAULT_PROVIDER, DEFAULT_MODEL };
