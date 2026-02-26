/**
 * Dynamic prompt builder para o OmniMind agent.
 *
 * Fornece duas funções:
 * - buildStaticSystemPrompt(): string — prompt completo para passar ao createDeepAgent
 * - buildDynamicPrompt(): BaseMessageLike[] — para uso futuro quando o runtime
 *   suportar uma `prompt` function nativa no createReactAgent
 */

import type { BaseMessageLike } from "@langchain/core/messages";
import type { RunnableConfig } from "@langchain/core/runnables";
import { MessagesAnnotation } from "@langchain/langgraph";
import { BASE_PROMPT } from "./base";
import { FILESYSTEM_PROMPT } from "./tools/filesystem";
import { WEB_SEARCH_PROMPT } from "./tools/web-search";
import { TASK_PLANNING_PROMPT } from "./tools/task-planning";
import { SHELL_PROMPT } from "./tools/shell";

/** Groups de tools mapeadas para seus prompts */
const TOOL_PROMPT_MODULES: Array<{
  toolNames: string[];
  prompt: string;
}> = [
  {
    toolNames: ["ls", "read_file", "write_file", "edit_file", "glob", "grep"],
    prompt: FILESYSTEM_PROMPT,
  },
  {
    toolNames: ["search_web"],
    prompt: WEB_SEARCH_PROMPT,
  },
  {
    toolNames: ["write_todos"],
    prompt: TASK_PLANNING_PROMPT,
  },
  {
    toolNames: ["execute"],
    prompt: SHELL_PROMPT,
  },
];

/** Extrai os nomes de tools invocadas nas mensagens do estado */
function extractRecentToolNames(
  messages: typeof MessagesAnnotation.State["messages"]
): Set<string> {
  const names = new Set<string>();

  for (const msg of messages) {
    // Suporta AIMessage com tool_calls array
    const toolCalls = (msg as { tool_calls?: Array<{ name: string }> }).tool_calls;
    if (Array.isArray(toolCalls)) {
      for (const tc of toolCalls) {
        if (tc.name) names.add(tc.name);
      }
    }

    // Suporta content blocks com type "tool_use"
    const content = (msg as { content?: unknown }).content;
    if (Array.isArray(content)) {
      for (const block of content) {
        if (
          typeof block === "object" &&
          block !== null &&
          "type" in block &&
          (block as { type: string }).type === "tool_use" &&
          "name" in block
        ) {
          names.add((block as { name: string }).name);
        }
      }
    }
  }

  return names;
}

/**
 * Retorna o system prompt completo (todos os módulos) como string.
 * Use isto com createDeepAgent({ systemPrompt: buildStaticSystemPrompt() }).
 */
export function buildStaticSystemPrompt(): string {
  return [BASE_PROMPT, FILESYSTEM_PROMPT, WEB_SEARCH_PROMPT, TASK_PLANNING_PROMPT, SHELL_PROMPT].join("\n\n");
}

/**
 * Constrói o prompt dinâmico baseado no estado atual.
 * Sempre inclui o BASE_PROMPT + sections dos tools que já foram usados
 * (ou todos os tools disponíveis na primeira mensagem).
 */
export function buildDynamicPrompt(
  state: typeof MessagesAnnotation.State,
  _config?: RunnableConfig
): BaseMessageLike[] {
  const usedTools = extractRecentToolNames(state.messages);

  // Coleta as seções de prompt dos tools relevantes (sem duplicatas)
  const sections: string[] = [BASE_PROMPT];
  const addedPrompts = new Set<string>();

  // Se nenhuma tool foi usada ainda, inclui TODOS os módulos
  // (contexto completo na primeira interação)
  const includeAll = usedTools.size === 0;

  for (const module of TOOL_PROMPT_MODULES) {
    const isRelevant = includeAll || module.toolNames.some((name) => usedTools.has(name));
    if (isRelevant && !addedPrompts.has(module.prompt)) {
      sections.push(module.prompt);
      addedPrompts.add(module.prompt);
    }
  }

  const systemContent = sections.join("\n\n");

  return [
    { role: "system", content: systemContent },
    ...state.messages,
  ];
}
