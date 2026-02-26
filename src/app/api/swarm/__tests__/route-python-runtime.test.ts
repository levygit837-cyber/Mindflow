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

import { POST } from "@/app/api/swarm/route";
import { getSession } from "@server/swarm/registry";

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

describe("POST /api/swarm", () => {
  beforeEach(() => {
    spawnMock.mockReset();
  });

  it("creates session and starts python swarm runtime", async () => {
    const child = makeChildProcessMock();
    spawnMock.mockReturnValue(child);

    const request = new Request("http://localhost/api/swarm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description: "Build a CLI" }),
    });

    const response = await POST(request as never);
    const payload = (await response.json()) as { task_id: string; stream_url: string; status: string };

    expect(response.status).toBe(201);
    expect(payload.task_id).toBeTruthy();
    expect(payload.stream_url).toBe(`/api/swarm/${payload.task_id}/stream`);
    expect(payload.status).toBe("pending");

    const session = getSession(payload.task_id);
    expect(session).toBeDefined();
    expect(spawnMock).toHaveBeenCalledWith(
      expect.any(String),
      ["-m", "omnimind_agents.runtime.swarm_runner"],
      expect.objectContaining({
        cwd: expect.any(String),
      })
    );
    expect(child.stdin.write).toHaveBeenCalled();
    expect(child.stdin.end).toHaveBeenCalled();

    // Graceful close of background runtime
    child.emit("close", 0);
  });
});
