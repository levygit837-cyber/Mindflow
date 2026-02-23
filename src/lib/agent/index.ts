import { createOmniMindDeepAgent } from "./deep-agent-config";
import { getModelForProvider, DEFAULT_PROVIDER, DEFAULT_MODEL } from "./providers";
import { buildDynamicPrompt } from "./prompts/dynamic-prompt";
import type { LLMProvider } from "@/types/agent";

export function createOmniMindAgent(
  provider: LLMProvider = DEFAULT_PROVIDER,
  model: string = DEFAULT_MODEL,
  options: { apiKey?: string; baseUrl?: string } = {}
) {
  const llm = getModelForProvider(provider, model, options);

  return createOmniMindDeepAgent({
    model: llm,
    promptFn: buildDynamicPrompt,
    // systemPrompt omitido — buildDynamicPrompt é a fonte de verdade
  });
}

export { DEFAULT_PROVIDER, DEFAULT_MODEL };
