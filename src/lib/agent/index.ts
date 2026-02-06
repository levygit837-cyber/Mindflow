import { createDeepAgent } from "deepagents";
import { getModelForProvider } from "./providers";
import { noteTools } from "./tools/note-tools";
import type { LLMProvider } from "@/types/agent";

const SYSTEM_PROMPT = `You are OmniMind, a personal AI assistant with deep knowledge management capabilities.

You have access to the user's personal notes system. You can:
- Read and search through their notes
- Find connections between notes
- Link related notes together in the knowledge graph
- Answer questions using the context from their notes

When answering questions about the user's notes:
1. First search or list relevant notes
2. Read the full content of relevant notes
3. Synthesize information across multiple notes when needed
4. Be specific about which notes you're referencing

You also have filesystem tools to browse the notes directory at data/notes/ where each note is stored as a JSON file.

Be concise, helpful, and reference specific notes when possible.`;

export function createOmniMindAgent(
  provider: LLMProvider = "anthropic",
  model: string = "claude-sonnet-4-20250514",
  options: { apiKey?: string; baseUrl?: string } = {}
) {
  const llm = getModelForProvider(provider, model, options);

  const agent = createDeepAgent({
    model: llm,
    tools: [...noteTools],
    systemPrompt: SYSTEM_PROMPT,
  });

  return agent;
}
