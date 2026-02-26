import { describe, expect, it } from "vitest";
import { AIMessageChunk } from "@langchain/core/messages";
import type { LLMProvider, StreamEvent, StreamEventType, StreamModeName } from "@shared/types/agent";
import { createAgentChatStreamNormalizer } from "@server/agent/chat-stream-normalizer";

function collectEvents(provider: LLMProvider, items: unknown[]) {
  const events: Array<{
    type: StreamEventType;
    data: string;
    mode: StreamModeName;
    meta?: StreamEvent["meta"];
  }> = [];

  const normalizer = createAgentChatStreamNormalizer({
    provider,
    emit: (type, data, mode, meta) => {
      events.push({ type, data, mode, meta });
    },
  });

  for (const item of items) {
    normalizer.process(item);
  }

  normalizer.flush();
  return events;
}

describe("createAgentChatStreamNormalizer", () => {
  it("streams anthropic thought + response from messages mode", () => {
    const events = collectEvents("anthropic", [
      [
        ["root", "agent"],
        "messages",
        [
          {
            id: "run-1",
            type: "ai",
            content: [
              { type: "thinking", thinking: "analisando..." },
              { type: "text", text: "Resposta final" },
            ],
          },
          { langgraph_node: "agent", run_id: "run-1" },
        ],
      ],
    ]);
    expect(events.some((e) => e.type === "thought" && e.data.includes("analisando"))).toBe(true);
    expect(events.some((e) => e.type === "response" && e.data.includes("Resposta final"))).toBe(true);
  });

  it("streams response for openai and ollama from messages mode", () => {
    const providers: LLMProvider[] = ["openai", "ollama"];

    for (const provider of providers) {
      const events = collectEvents(provider, [
        [
          ["root", "agent"],
          "messages",
          [
            {
              id: `${provider}-run-1`,
              type: "ai",
              content: "Hello streamed tokens",
            },
            { langgraph_node: "agent", run_id: `${provider}-run-1` },
          ],
        ],
      ]);

      expect(events.some((e) => e.type === "response" && e.data.includes("Hello streamed"))).toBe(true);
    }
  });

  it("splits gemini think tags into separate thought and response events", () => {
    const providers: LLMProvider[] = ["google", "vertexai"];

    for (const provider of providers) {
      const events = collectEvents(provider, [
        [
          ["root", "agent"],
          "messages",
          [
            {
              id: `${provider}-run-1`,
              type: "ai",
              content: "<think>pensando em passos</think>Resposta pronta",
            },
            { langgraph_node: "agent", run_id: `${provider}-run-1` },
          ],
        ],
      ]);
      const totalThought = events.filter((e) => e.type === "thought").map((e) => e.data).join("");
      expect(totalThought.includes("pensando em passos")).toBe(true);
      const fullResponse = events
        .filter((e) => e.type === "response")
        .map((e) => e.data)
        .join("");
      expect(fullResponse.includes("Resposta pronta")).toBe(true);
    }
  });

  it("streams vertex reasoning from a real AIMessageChunk tuple [chunk, metadata]", () => {
    const chunk = new AIMessageChunk({
      id: "vertex-msg-1",
      content: [
        { type: "reasoning", reasoning: "pensando com vertex" },
        { type: "text", text: "resposta vertex" },
      ],
      additional_kwargs: {
        reasoning_content: { summary: [{ text: "resumo de raciocinio" }] },
      },
    });

    const events = collectEvents("vertexai", [[chunk, { langgraph_node: "agent", run_id: "run-vertex-1" }]]);
    const fullResponse = events
      .filter((e) => e.type === "response")
      .map((e) => e.data)
      .join("");

    expect(events.some((e) => e.type === "thought" && e.data.includes("pensando com vertex"))).toBe(true);
    expect(events.some((e) => e.type === "thought" && e.data.includes("resumo de raciocinio"))).toBe(true);
    expect(fullResponse.includes("resposta vertex")).toBe(true);
    expect(events.some((e) => e.type === "step")).toBe(false);
  });

  it("unwraps wrappers where chunk is inside .message", () => {
    const wrapped = {
      message: new AIMessageChunk({
        id: "vertex-wrap-1",
        content: [{ type: "reasoning", reasoning: "pensamento em wrapper" }],
      }),
    };

    const events = collectEvents("vertexai", [[wrapped, { langgraph_node: "agent", run_id: "run-wrap-1" }]]);

    expect(events.some((e) => e.type === "thought" && e.data.includes("pensamento em wrapper"))).toBe(true);
  });

  it("extracts content/additional_kwargs from lc_kwargs fallback", () => {
    const message = {
      type: "ai",
      content: "",
      lc_kwargs: {
        content: [
          { type: "reasoning", reasoning: "thought via lc_kwargs" },
          { type: "text", text: "answer via lc_kwargs" },
        ],
        additional_kwargs: {
          reasoningContent: { text: "kwargs reasoning content" },
        },
      },
    };

    const events = collectEvents("vertexai", [[message, { langgraph_node: "agent", run_id: "run-lc-1" }]]);
    const fullResponse = events
      .filter((e) => e.type === "response")
      .map((e) => e.data)
      .join("");

    expect(events.some((e) => e.type === "thought" && e.data.includes("thought via lc_kwargs"))).toBe(true);
    expect(events.some((e) => e.type === "thought" && e.data.includes("kwargs reasoning content"))).toBe(true);
    expect(fullResponse.includes("answer via lc_kwargs")).toBe(true);
  });

  it("extracts reasoning from nested additional_kwargs payloads", () => {
    const events = collectEvents("anthropic", [
      [
        ["root", "agent"],
        "messages",
        [
          {
            id: "ai-nested-1",
            type: "ai",
            content: "",
            additional_kwargs: {
              reasoning: {
                summary: [{ text: "raciocinio resumido" }],
              },
            },
          },
          { langgraph_node: "agent", run_id: "run-nested-1" },
        ],
      ],
    ]);

    expect(events.some((e) => e.type === "thought" && e.data.includes("raciocinio resumido"))).toBe(true);
  });

  it("treats reasoning_text blocks as thought (not response)", () => {
    const events = collectEvents("openai", [
      [
        ["root", "agent"],
        "messages",
        [
          {
            id: "ai-reasoning-1",
            type: "ai",
            content: [{ type: "reasoning_text", text: "pensando alto" }],
          },
          { langgraph_node: "agent", run_id: "run-reasoning-1" },
        ],
      ],
    ]);

    expect(events.some((e) => e.type === "thought" && e.data.includes("pensando alto"))).toBe(true);
    expect(events.some((e) => e.type === "response" && e.data.includes("pensando alto"))).toBe(false);
  });

  it("falls back to updates AI message when messages mode has no output", () => {
    const events = collectEvents("openai", [
      [
        ["root", "agent"],
        "updates",
        {
          agent: {
            messages: [
              {
                id: "ai-update-1",
                type: "ai",
                content: "Fallback output from updates",
              },
            ],
          },
        },
      ],
    ]);

    expect(events.some((e) => e.type === "step" && e.data.includes("Agent"))).toBe(true);
    expect(events.some((e) => e.type === "response" && e.data.includes("Fallback output from updates"))).toBe(true);
  });

  it("does not duplicate final updates AI text after messages stream already emitted output", () => {
    const events = collectEvents("openai", [
      [
        ["root", "agent"],
        "messages",
        [
          {
            id: "ai-dup-1",
            type: "ai",
            content: "hello",
          },
          { langgraph_node: "agent", run_id: "run-dup-1" },
        ],
      ],
      [
        ["root", "agent"],
        "updates",
        {
          agent: {
            messages: [
              {
                id: "ai-dup-1",
                type: "ai",
                content: "hello",
              },
            ],
          },
        },
      ],
    ]);

    const responseEvents = events.filter((e) => e.type === "response" && e.data.includes("hello"));
    expect(responseEvents).toHaveLength(1);
  });

  it("uses updates as thought fallback when messages stream has only response", () => {
    const events = collectEvents("vertexai", [
      [
        "messages",
        [
          {
            id: "ai-fallback-1",
            type: "ai",
            content: "resposta sem pensamento",
          },
          { langgraph_node: "agent", run_id: "run-fallback-1" },
        ],
      ],
      [
        "updates",
        {
          agent: {
            messages: [
              {
                id: "ai-fallback-1",
                type: "ai",
                content: [{ type: "reasoning", reasoning: "pensamento via updates" }],
              },
            ],
          },
        },
      ],
    ]);

    const fullResponse = events
      .filter((e) => e.type === "response")
      .map((e) => e.data)
      .join("");

    expect(fullResponse.includes("resposta sem pensamento")).toBe(true);
    expect(events.some((e) => e.type === "thought" && e.data.includes("pensamento via updates"))).toBe(true);
  });

  it("correlates tool_call and tool_result without unknown name", () => {
    const events = collectEvents("anthropic", [
      [
        ["root", "agent"],
        "updates",
        {
          agent: {
            messages: [
              {
                id: "ai-tools-1",
                type: "ai",
                tool_calls: [
                  {
                    id: "tc-1",
                    name: "read_note",
                    args: { noteId: "n-1" },
                  },
                ],
              },
            ],
          },
        },
      ],
      [
        ["root", "tools"],
        "updates",
        {
          tools: {
            messages: [
              {
                id: "tool-msg-1",
                type: "tool",
                tool_call_id: "tc-1",
                content: "{\"ok\":true}",
              },
            ],
          },
        },
      ],
    ]);

    const toolCall = events.find((e) => e.type === "tool_call");
    const toolResult = events.find((e) => e.type === "tool_result");

    expect(toolCall).toBeDefined();
    expect(toolResult).toBeDefined();
    expect(toolCall?.data).toContain("read_note");
    expect(toolResult?.data).toContain("read_note");
    expect(toolResult?.data).not.toContain("unknown");
    expect(toolResult?.data).toContain("tc-1");
  });

  it("emite thought tokens individualmente (token-a-token) sem acumular buffer", () => {
    const emitted: Array<{ type: StreamEventType; data: string }> = [];

    const normalizer = createAgentChatStreamNormalizer({
      provider: "vertexai",
      emit: (type, data) => emitted.push({ type, data }),
    });

    // Simula chegada de tokens individuais (1 char por vez)
    const tokens = ["<", "t", "h", "i", "n", "k", ">", "p", "e", "n", "s", "a", "<", "/", "t", "h", "i", "n", "k", ">", "o", "k"];
    for (const token of tokens) {
      normalizer.process([token, { langgraph_node: "agent" }]);
    }
    normalizer.flush();

    // Deve emitir "thought" com "pensa" progressivamente (não acumular tudo)
    const thoughtEvents = emitted.filter(e => e.type === "thought");
    const responseEvents = emitted.filter(e => e.type === "response");

    // Deve ter pelo menos 1 evento thought com conteúdo partial
    expect(thoughtEvents.length).toBeGreaterThan(0);
    // Conteúdo total pensado deve ser "pensa"
    const totalThought = thoughtEvents.map(e => e.data).join("");
    expect(totalThought).toBe("pensa");
    // Response deve ser "ok"
    const totalResponse = responseEvents.map(e => e.data).join("");
    expect(totalResponse).toBe("ok");
  });

  it("filters middleware update nodes and keeps only user-visible steps", () => {
    const events = collectEvents("openai", [
      [
        ["root", "agent"],
        "updates",
        {
          "patchToolCallsMiddleware.before_agent": {},
          "SummarizationMiddleware.before_model": {},
          model_request: {},
          tools: { messages: [] },
        },
      ],
    ]);

    const steps = events.filter((e) => e.type === "step").map((e) => e.data);
    expect(steps).not.toContain("Model request");
    expect(steps).toContain("Tools");
    expect(steps.some((s) => s.includes("Node update"))).toBe(false);
  });
});
