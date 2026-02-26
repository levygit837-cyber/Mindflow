import { describe, it, expect, vi } from "vitest";
import { NotifierService } from "../notifier";

describe("NotifierService", () => {
  it("emits an event with correct structure", () => {
    const notifier = new NotifierService("task-1");
    const event = notifier.emit("AGENT_STATE_CHANGE", "coder", {
      old_state: "pending",
      new_state: "planning",
    });

    expect(event.event_id).toBeDefined();
    expect(event.event_type).toBe("AGENT_STATE_CHANGE");
    expect(event.agent_id).toBe("coder");
    expect(event.timestamp).toBeDefined();
    expect(event.payload).toEqual({
      old_state: "pending",
      new_state: "planning",
    });
    expect(event.metadata.task_id).toBe("task-1");
    expect(event.metadata.sequence_number).toBe(0);
  });

  it("assigns monotonically increasing sequence numbers", () => {
    const notifier = new NotifierService("task-2");

    const e1 = notifier.emit("TOKEN_STREAM", "coder", { token: "a" });
    const e2 = notifier.emit("TOKEN_STREAM", "coder", { token: "b" });
    const e3 = notifier.emit("TOKEN_STREAM", "coder", { token: "c" });

    expect(e1.metadata.sequence_number).toBe(0);
    expect(e2.metadata.sequence_number).toBe(1);
    expect(e3.metadata.sequence_number).toBe(2);
    expect(notifier.getSequence()).toBe(3);
  });

  it("stores events in buffer", () => {
    const notifier = new NotifierService("task-3");

    notifier.emit("TOOL_CALL", "coder", { tool_name: "read_file" });
    notifier.emit("TOOL_RESULT", "coder", { tool_name: "read_file", success: true });

    const buffer = notifier.getBuffer();
    expect(buffer).toHaveLength(2);
    expect(buffer[0].event_type).toBe("TOOL_CALL");
    expect(buffer[1].event_type).toBe("TOOL_RESULT");
  });

  it("returns a copy of the buffer (not a reference)", () => {
    const notifier = new NotifierService("task-4");
    notifier.emit("ERROR", "orchestrator", { message: "fail" });

    const buf1 = notifier.getBuffer();
    const buf2 = notifier.getBuffer();
    expect(buf1).not.toBe(buf2);
    expect(buf1).toEqual(buf2);
  });

  it("enforces circular buffer cap", () => {
    const cap = 5;
    const notifier = new NotifierService("task-5", cap);

    for (let i = 0; i < 8; i++) {
      notifier.emit("TOKEN_STREAM", "coder", { token: String(i) });
    }

    const buffer = notifier.getBuffer();
    expect(buffer).toHaveLength(cap);
    // Oldest events (0, 1, 2) should be gone; buffer should have 3..7
    expect(buffer[0].metadata.sequence_number).toBe(3);
    expect(buffer[4].metadata.sequence_number).toBe(7);
  });

  it("broadcasts events to subscribers", () => {
    const notifier = new NotifierService("task-6");
    const received: string[] = [];

    notifier.subscribe((event) => {
      received.push(event.event_type);
    });

    notifier.emit("PLAN_UPDATE", "coder", { step: 1 });
    notifier.emit("FILE_CHANGE", "coder", { filepath: "a.ts" });

    expect(received).toEqual(["PLAN_UPDATE", "FILE_CHANGE"]);
  });

  it("supports multiple subscribers", () => {
    const notifier = new NotifierService("task-7");
    const received1: number[] = [];
    const received2: number[] = [];

    notifier.subscribe((e) => received1.push(e.metadata.sequence_number));
    notifier.subscribe((e) => received2.push(e.metadata.sequence_number));

    notifier.emit("SANDBOX_UPDATE", "sandbox_renderer", { content: "..." });

    expect(received1).toEqual([0]);
    expect(received2).toEqual([0]);
  });

  it("unsubscribe removes the callback", () => {
    const notifier = new NotifierService("task-8");
    const received: number[] = [];

    const unsub = notifier.subscribe((e) =>
      received.push(e.metadata.sequence_number)
    );

    notifier.emit("TOKEN_STREAM", "coder", { token: "a" });
    unsub();
    notifier.emit("TOKEN_STREAM", "coder", { token: "b" });

    expect(received).toEqual([0]);
  });

  it("handles subscriber errors gracefully", () => {
    const notifier = new NotifierService("task-9");
    const received: string[] = [];

    notifier.subscribe(() => {
      throw new Error("boom");
    });
    notifier.subscribe((e) => {
      received.push(e.event_type);
    });

    // Should not throw even though first subscriber throws
    expect(() => {
      notifier.emit("ERROR", "orchestrator", { message: "test" });
    }).not.toThrow();

    // Second subscriber should still receive the event
    expect(received).toEqual(["ERROR"]);
  });

  it("getBufferAfter returns events after a given sequence", () => {
    const notifier = new NotifierService("task-10");

    notifier.emit("TOKEN_STREAM", "coder", { token: "a" }); // seq 0
    notifier.emit("TOKEN_STREAM", "coder", { token: "b" }); // seq 1
    notifier.emit("TOKEN_STREAM", "coder", { token: "c" }); // seq 2
    notifier.emit("TOKEN_STREAM", "coder", { token: "d" }); // seq 3

    const afterOne = notifier.getBufferAfter(1);
    expect(afterOne).toHaveLength(2);
    expect(afterOne[0].metadata.sequence_number).toBe(2);
    expect(afterOne[1].metadata.sequence_number).toBe(3);

    const afterAll = notifier.getBufferAfter(3);
    expect(afterAll).toHaveLength(0);

    const afterNone = notifier.getBufferAfter(-1);
    expect(afterNone).toHaveLength(4);
  });

  it("getTaskId returns the bound task ID", () => {
    const notifier = new NotifierService("my-task-id");
    expect(notifier.getTaskId()).toBe("my-task-id");
  });

  it("generates unique event IDs (UUID v4 format)", () => {
    const notifier = new NotifierService("task-uuid");
    const e1 = notifier.emit("TOKEN_STREAM", "coder", { token: "x" });
    const e2 = notifier.emit("TOKEN_STREAM", "coder", { token: "y" });

    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    expect(e1.event_id).toMatch(uuidRegex);
    expect(e2.event_id).toMatch(uuidRegex);
    expect(e1.event_id).not.toBe(e2.event_id);
  });

  it("generates ISO 8601 timestamps", () => {
    const notifier = new NotifierService("task-ts");
    const event = notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {});

    // Should parse as valid date
    const parsed = new Date(event.timestamp);
    expect(parsed.getTime()).not.toBeNaN();
    // Should contain T separator and end with Z or offset
    expect(event.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });
});
