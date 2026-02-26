import { beforeEach, describe, expect, it, vi } from "vitest";
import { EventEmitter } from "node:events";

const { spawnMock } = vi.hoisted(() => ({
  spawnMock: vi.fn(),
}));

vi.mock("node:child_process", () => ({
  spawn: spawnMock,
  default: {
    spawn: spawnMock,
  },
}));

import { POST } from "@/app/api/agent/chat/route";

function makeChildProcessMock() {
  const child = new EventEmitter() as EventEmitter & {
    stdout: EventEmitter;
    stderr: EventEmitter;
    stdin: { write: ReturnType<typeof vi.fn>; end: ReturnType<typeof vi.fn> };
  };

  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.stdin = {
    write: vi.fn(),
    end: vi.fn(),
  };

  return child;
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
    spawnMock.mockReset();
  });

  it("streams events produced by python runtime", async () => {
    const child = makeChildProcessMock();
    spawnMock.mockReturnValue(child);

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "oi", provider: "anthropic", model: "claude-sonnet-4-20250514" }),
    });

    const response = await POST(request as never);

    child.stdout.emit(
      "data",
      Buffer.from(
        [
          JSON.stringify({ type: "thought", data: "analisando", mode: "messages" }),
          JSON.stringify({ type: "response", data: "resposta", mode: "messages" }),
          JSON.stringify({ type: "done", data: "", mode: "messages" }),
        ].join("\n") + "\n"
      )
    );
    child.emit("close", 0);

    const events = await readSSEEvents(response);
    const types = events.map((e) => e.type);

    expect(types).toContain("thought");
    expect(types).toContain("response");
    expect(types).toContain("done");
    expect(spawnMock).toHaveBeenCalledWith(
      expect.any(String),
      ["-m", "omnimind_agents.runtime.chat_runner"],
      expect.objectContaining({
        cwd: expect.any(String),
      })
    );
    expect(child.stdin.write).toHaveBeenCalled();
    expect(child.stdin.end).toHaveBeenCalled();
  });

  it("emits error event when python runtime exits with non-zero code", async () => {
    const child = makeChildProcessMock();
    spawnMock.mockReturnValue(child);

    const request = new Request("http://localhost/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "oi" }),
    });

    const response = await POST(request as never);

    child.stderr.emit("data", Buffer.from("python error"));
    child.emit("close", 1);

    const events = await readSSEEvents(response);
    expect(events.some((e) => e.type === "error" && String(e.data).includes("python error"))).toBe(true);
  });
});
