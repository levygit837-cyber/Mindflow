import { beforeEach, describe, expect, it, vi } from "vitest";
import { AIMessageChunk } from "@langchain/core/messages";

const { ensureDbInitialized, streamMock } = vi.hoisted(() => ({
  ensureDbInitialized: vi.fn(),
  streamMock: vi.fn(),
}));

vi.mock("@backend/db/postgres", () => ({
  ensureDbInitialized,
}));

vi.mock("@backend/agent", () => ({
  createOmniMindAgent: vi.fn(() => ({
    stream: streamMock,
  })),
}));

import { POST } from "@/app/api/agent/chat/route";

function makeStream(items: unknown[]) {
  return (async function* generate() {
    for (const item of items) {
      yield item;
    }
  })();
}

async function readSSEEvents(response: Response) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Response missing body reader");

  const decoder = new TextDecoder();
  const events: Array<Record<string, unknown>> = [];
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      events.push(JSON.parse(line.slice(6)) as Record<string, unknown>);
    }
  }

  return events;
}

describe("POST /api/agent/chat", () => {
  beforeEach(() => {
    ensureDbInitialized.mockReset();
    streamMock.mockReset();
  });

  it("streams thought/response/tool events with done", async () => {
    streamMock.mockResolvedValue(
      makeStream([
        [
          {
            id: "ai-1",
            type: "ai",
            content: [
              { type: "thinking", thinking: "analisando" },
              { type: "text", text: "resposta" },
            ],
            tool_calls: [{ id: "tc-9", name: "read_note", args: { noteId: "n1" } }],
          },
          { langgraph_node: "agent", run_id: "run-1" },
        ],
        [
          {
            id: "tool-2",
            type: "tool",
            tool_call_id: "tc-9",
            content: "OK",
          },
          { langgraph_node: "tools", run_id: "run-2" },
        ],
      ])
    );

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "oi", provider: "anthropic", model: "claude-sonnet-4-20250514" }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);

    const types = events.map((e) => e.type);
    expect(types).toContain("thought");
    expect(types).toContain("response");
    expect(types).toContain("tool_call");
    expect(types).toContain("tool_result");
    expect(types).toContain("done");
    expect(types).not.toContain("step");

    const seqs = events
      .map((e) => e.seq)
      .filter((x): x is number => typeof x === "number");
    expect(seqs.length).toBeGreaterThan(0);
    expect(seqs).toEqual([...seqs].sort((a, b) => a - b));

    const hasUnknownTool = events.some(
      (e) => e.type === "tool_result" && typeof e.data === "string" && e.data.includes("unknown")
    );
    expect(hasUnknownTool).toBe(false);
    expect(streamMock.mock.calls[0]?.[1]?.streamMode).toEqual(["messages", "updates"]);
  });

  it("supports debugSteps mode with updates stream when requested", async () => {
    streamMock.mockResolvedValue(
      makeStream([
        [
          ["root", "agent"],
          "updates",
          {
            agent: {
              messages: [{ id: "ai-only-updates", type: "ai", content: "texto via updates" }],
            },
          },
        ],
      ])
    );

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "teste",
        provider: "openai",
        model: "gpt-4o",
        debugSteps: true,
      }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);

    expect(events.some((e) => e.type === "response" && String(e.data).includes("texto via updates"))).toBe(true);
    expect(events.some((e) => e.type === "done")).toBe(true);
    expect(streamMock.mock.calls[0]?.[1]?.streamMode).toEqual(["messages", "updates"]);
  });

  it("supports wrappers that yield ['messages', [chunk, metadata]]", async () => {
    streamMock.mockResolvedValue(
      makeStream([
        [
          "messages",
          [
            {
              id: "ai-wrapper-1",
              type: "ai",
              content: [{ type: "reasoning_text", text: "pensando wrapper" }, { type: "text", text: "ok" }],
            },
            { langgraph_node: "agent", run_id: "run-wrapper-1" },
          ],
        ],
      ])
    );

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "teste", provider: "openai", model: "gpt-4o" }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);

    expect(events.some((e) => e.type === "thought" && String(e.data).includes("pensando wrapper"))).toBe(true);
    expect(events.some((e) => e.type === "response" && String(e.data).includes("ok"))).toBe(true);
  });

  it("does not enable updates when debugSteps comes as string 'false'", async () => {
    streamMock.mockResolvedValue(
      makeStream([
        [
          {
            id: "vertex-msg-1",
            type: "ai",
            content: "ok",
          },
          { langgraph_node: "agent", run_id: "run-vertex-1" },
        ],
      ])
    );

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "teste",
        provider: "vertexai",
        model: "gemini-2.5-pro",
        debugSteps: "false",
      }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);

    expect(events.some((e) => e.type === "response" && String(e.data).includes("ok"))).toBe(true);
    expect(streamMock.mock.calls[0]?.[1]?.streamMode).toEqual(["messages", "updates"]);
  });

  it("streams vertex reasoning from real AIMessageChunk in messages mode", async () => {
    streamMock.mockResolvedValue(
      makeStream([
        [
          new AIMessageChunk({
            id: "ai-vertex-real",
            content: [
              { type: "reasoning", reasoning: "planejando com vertex" },
              { type: "text", text: "resposta final vertex" },
            ],
          }),
          { langgraph_node: "agent", run_id: "run-vertex-real" },
        ],
      ])
    );

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "teste",
        provider: "vertexai",
        model: "gemini-2.5-pro",
      }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);
    const fullResponse = events
      .filter((e) => e.type === "response")
      .map((e) => String(e.data))
      .join("");

    expect(events.some((e) => e.type === "thought" && String(e.data).includes("planejando com vertex"))).toBe(true);
    expect(fullResponse.includes("resposta final vertex")).toBe(true);
    expect(events.some((e) => e.type === "step")).toBe(false);
    expect(streamMock.mock.calls[0]?.[1]?.streamMode).toEqual(["messages", "updates"]);
  });

  it("emits thought from updates fallback without showing node steps in normal mode", async () => {
    streamMock.mockResolvedValue(
      makeStream([
        [
          "messages",
          [
            {
              id: "ai-fallback-route-1",
              type: "ai",
              content: "resposta principal",
            },
            { langgraph_node: "agent", run_id: "run-fallback-route-1" },
          ],
        ],
        [
          "updates",
          {
            agent: {
              messages: [
                {
                  id: "ai-fallback-route-1",
                  type: "ai",
                  content: [{ type: "reasoning", reasoning: "pensamento vindo de updates" }],
                },
              ],
            },
          },
        ],
      ])
    );

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "teste fallback",
        provider: "vertexai",
        model: "gemini-2.5-pro",
      }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);
    const fullResponse = events
      .filter((e) => e.type === "response")
      .map((e) => String(e.data))
      .join("");

    expect(fullResponse.includes("resposta principal")).toBe(true);
    expect(events.some((e) => e.type === "thought" && String(e.data).includes("pensamento vindo de updates"))).toBe(
      true
    );
    expect(events.some((e) => e.type === "step")).toBe(false);
  });
});
