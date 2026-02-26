import { beforeEach, describe, expect, it, vi } from "vitest";

const { streamMock, createOmniMindAgentMock } = vi.hoisted(() => ({
  streamMock: vi.fn(),
  createOmniMindAgentMock: vi.fn(),
}));

vi.mock("@server/agent", () => ({
  createOmniMindAgent: createOmniMindAgentMock,
}));

import { POST } from "@/app/api/agent/chat/route";

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
    streamMock.mockReset();
    createOmniMindAgentMock.mockReset();
    createOmniMindAgentMock.mockReturnValue({
      stream: streamMock
    });
  });

  it("streams events produced by the TS deepagents runtime", async () => {
    async function* mockStreamGenerator() {
      yield ["messages", ["analisando", { langgraph_node: "agent" }]];
      yield ["messages", ["resposta", { langgraph_node: "agent" }]];
    }
    streamMock.mockReturnValue(mockStreamGenerator());

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "oi", provider: "anthropic", model: "claude-sonnet-4-20250514" }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);
    const types = events.map((e) => e.type);

    expect(types).toContain("response");
    expect(types).toContain("done");
    expect(createOmniMindAgentMock).toHaveBeenCalled();
    expect(streamMock).toHaveBeenCalled();
  });

  it("emits error event when the TS runtime throws an error", async () => {
    streamMock.mockImplementation(() => {
      throw new Error("ts error");
    });

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "oi" }),
    });

    const response = await POST(request as never);
    const events = await readSSEEvents(response);

    expect(events.some((e) => e.type === "error" && String(e.data).includes("ts error"))).toBe(true);
  });
});
