import { createOmniMindDeepAgent } from "./deep-agent-config";
import { getModelForProvider, DEFAULT_PROVIDER, DEFAULT_MODEL } from "./providers";
import type { LLMProvider } from "@/types/agent";

const SYSTEM_PROMPT = `You are OmniMind, a powerful Deep Agent with planning, sub-agent delegation, filesystem access, and long-term memory capabilities.

You can:
- Plan complex tasks step-by-step using your todo list
- Delegate subtasks to specialized sub-agents
- Read, write, and search files in your workspace
- Remember important information across conversations
- Execute shell commands when needed

When reasoning through complex problems, think step by step. Your thinking process will be shown to the user in a collapsible section.

Be concise, helpful, and thorough.`;

export function createOmniMindAgent(
  provider: LLMProvider = DEFAULT_PROVIDER,
  model: string = DEFAULT_MODEL,
  options: { apiKey?: string; baseUrl?: string } = {}
) {
  const llm = getModelForProvider(provider, model, options);

  return createOmniMindDeepAgent({
    model: llm,
    systemPrompt: SYSTEM_PROMPT,
  });
}

export { DEFAULT_PROVIDER, DEFAULT_MODEL };
