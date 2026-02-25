import {
  createDeepAgent,
  CompositeBackend,
  StateBackend,
  FilesystemBackend,
} from "deepagents";
import { SafeBackend } from "./safe-backend";
import type { BaseLanguageModel } from "@langchain/core/language_models/base";
import { getCheckpointer } from "@/lib/db/postgres";
import { searchWebTool } from "./tools/search-web";

export interface DeepAgentOptions {
  model: BaseLanguageModel;
  systemPrompt: string;
}

export function createOmniMindDeepAgent(options: DeepAgentOptions) {
  const checkpointer = getCheckpointer();

  const agent = createDeepAgent({
    model: options.model,
    systemPrompt: options.systemPrompt,
    name: "omnimind-agent",
    checkpointer,
    tools: [searchWebTool],
    backend: new SafeBackend(
      new CompositeBackend(
        new FilesystemBackend({ rootDir: process.cwd() }),
        {
          "/memories/": new StateBackend({ state: {}, store: undefined }),
        }
      )
    ) as unknown as CompositeBackend,
  });

  return agent;
}
