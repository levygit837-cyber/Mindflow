/**
 * Node Registry — classifica e rotula todos os tipos de nodes que o LangGraph pode emitir.
 *
 * O LangGraph emite updates para vários tipos de nodes. Este módulo centraliza
 * a lógica de categorização para que o normalizer e o frontend saibam o que exibir.
 */

export enum NodeCategory {
  /** Invocação direta do LLM (agent, model) */
  LLM_INVOKE = "LLM_INVOKE",
  /** Execução de tools (tools, tool_executor) */
  TOOL_EXECUTION = "TOOL_EXECUTION",
  /** Subgraph de outro agente (formato "agentName:nodeName") */
  SUBGRAPH = "SUBGRAPH",
  /** Nó interno/middleware — não deve aparecer no frontend */
  INTERNAL = "INTERNAL",
  /** Nó customizado desconhecido */
  UNKNOWN = "UNKNOWN",
}

/** Nomes de nós internos que nunca devem ser exibidos */
const INTERNAL_NODE_PATTERNS: RegExp[] = [
  /^__/,                          // __start__, __end__, __interrupt__
  /Middleware/i,                  // patchToolCallsMiddleware, SummarizationMiddleware
  /\.before_/,                    // .before_agent
  /\.after_/,                     // .after_agent
  /^model_request$/,
  /^model_response$/,
  /^patchToolCalls/,
];

/** Nomes canônicos de nodes LLM */
const LLM_NODES = new Set(["agent", "model", "llm", "generate", "chat"]);

/** Nomes canônicos de nodes de tools */
const TOOL_NODES = new Set(["tools", "tool_executor", "tool_node", "action"]);

export function classifyNode(nodeName: string): NodeCategory {
  if (!nodeName) return NodeCategory.INTERNAL;

  // Subgraph: contém ":" separando agente:nó
  if (nodeName.includes(":")) return NodeCategory.SUBGRAPH;

  // Interno
  for (const pattern of INTERNAL_NODE_PATTERNS) {
    if (pattern.test(nodeName)) return NodeCategory.INTERNAL;
  }

  if (LLM_NODES.has(nodeName)) return NodeCategory.LLM_INVOKE;
  if (TOOL_NODES.has(nodeName)) return NodeCategory.TOOL_EXECUTION;

  return NodeCategory.UNKNOWN;
}

export function getNodeLabel(nodeName: string): string {
  if (!nodeName) return "Node";

  // Subgraph: "coder:agent" → "Coder › Agent"
  if (nodeName.includes(":")) {
    const [parent, child] = nodeName.split(":", 2);
    return `${titleCase(parent)} › ${titleCase(child)}`;
  }

  const canonical: Record<string, string> = {
    agent: "Agent",
    tools: "Tools",
    model: "Model",
    llm: "LLM",
    generate: "Generate",
    chat: "Chat",
    tool_executor: "Tools",
    tool_node: "Tools",
    action: "Action",
  };

  return canonical[nodeName] ?? titleCase(nodeName);
}

/** Retorna true se este node deve ter seus eventos expostos ao frontend */
export function isStreamableNode(nodeName: string): boolean {
  const category = classifyNode(nodeName);
  return (
    category === NodeCategory.LLM_INVOKE ||
    category === NodeCategory.TOOL_EXECUTION ||
    category === NodeCategory.SUBGRAPH ||
    category === NodeCategory.UNKNOWN
  );
}

function titleCase(value: string): string {
  if (!value) return "";
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
