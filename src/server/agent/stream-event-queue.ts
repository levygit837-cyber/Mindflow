import type { StreamEventType, StreamModeName, StreamEvent } from "@shared/types/agent";

type EmitFn = (
  type: StreamEventType,
  data: string,
  mode: StreamModeName,
  meta?: StreamEvent["meta"]
) => void;

interface QueuedEvent {
  type: StreamEventType;
  data: string;
  mode: StreamModeName;
  meta: StreamEvent["meta"];
  /** If true, inject insertBefore pointing to the first response part marker */
  wantsInsertBefore: boolean;
}

/**
 * Deferred event queue for the chat stream normalizer.
 *
 * Problem: LangGraph emits tool_call / tool_result from the `updates` channel
 * *after* the response tokens have already streamed via the `messages` channel.
 * This causes tool blocks to appear below the response text in the UI.
 *
 * Solution: defer tool_call / tool_result events from `updates`, then drain
 * them at flush() time with `meta.insertBefore` set to the stable marker ID
 * of the first response part emitted this turn. The frontend uses this to
 * reorder the parts correctly.
 *
 * Marker convention:
 *   The first "response" SSE event of each turn carries
 *   `meta.turnRunId` which is also used as the insertBefore anchor.
 *   Specifically: `insertBefore = "first-response-{turnRunId}"`
 *   and the first response event carries `meta.firstResponseMarker = same value`.
 *   The hook in use-agent-chat.ts maps that marker → the created TextPart id.
 */
export class StreamEventQueue {
  private queue: QueuedEvent[] = [];
  /** Marker string used as insertBefore anchor for this turn */
  private firstResponseMarker: string | null = null;

  /**
   * Called by the normalizer when the first "response" text is about to be emitted.
   * Returns a stable marker string that should be placed in meta.firstResponseMarker.
   */
  setFirstResponseMarker(turnRunId: string): string {
    if (!this.firstResponseMarker) {
      this.firstResponseMarker = `first-response-${turnRunId}`;
    }
    return this.firstResponseMarker;
  }

  /** Whether a first-response marker has been established this turn. */
  hasFirstResponseMarker(): boolean {
    return this.firstResponseMarker !== null;
  }

  /**
   * Enqueue a deferred event. If wantsInsertBefore is true, the event will
   * receive `meta.insertBefore` pointing to the first response marker at drain time.
   */
  enqueue(
    type: StreamEventType,
    data: string,
    mode: StreamModeName,
    meta: StreamEvent["meta"],
    wantsInsertBefore: boolean
  ): void {
    this.queue.push({ type, data, mode, meta, wantsInsertBefore });
  }

  /**
   * Emit all queued events, injecting insertBefore where requested.
   */
  drain(emit: EmitFn): void {
    for (const item of this.queue) {
      const finalMeta: StreamEvent["meta"] =
        item.wantsInsertBefore && this.firstResponseMarker
          ? { ...item.meta, insertBefore: this.firstResponseMarker }
          : item.meta;
      emit(item.type, item.data, item.mode, finalMeta);
    }
    this.queue = [];
  }

  /** Reset for a new turn. */
  reset(): void {
    this.queue = [];
    this.firstResponseMarker = null;
  }
}
