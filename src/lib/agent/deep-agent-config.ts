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
import type { BaseMessageLike } from "@langchain/core/messages";
import type { MessagesAnnotation } from "@langchain/langgraph";
import type { RunnableConfig } from "@langchain/core/runnables";

export interface DeepAgentOptions {
  model: BaseLanguageModel;
  /** System prompt estático. Use promptFn para prompts dinâmicos. */
  systemPrompt?: string;
  /**
   * Função de prompt dinâmico. Se fornecida, sobrepõe systemPrompt.
   * Recebe o estado atual e retorna BaseMessageLike[].
   * Compatível com a API de `prompt` function do createReactAgent.
   */
  promptFn?: (
    state: typeof MessagesAnnotation.State,
    config?: RunnableConfig
  ) => BaseMessageLike[];
}

export function createOmniMindDeepAgent(options: DeepAgentOptions) {
  const checkpointer = getCheckpointer();

  // Usa systemPrompt vazio se promptFn for fornecido (o route handler aplica o promptFn)
  const systemPrompt = options.systemPrompt ?? "";

  const agent = createDeepAgent({
    model: options.model,
    systemPrompt,
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

  return { agent, promptFn: options.promptFn };
}
