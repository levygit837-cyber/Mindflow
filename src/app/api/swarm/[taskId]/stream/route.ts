/**
 * GET /api/swarm/[taskId]/stream — SSE stream for swarm task events.
 *
 * Subscribes to the task's NotifierService and pushes each
 * NotificationEvent as an SSE `data:` line. Supports reconnect via the
 * `Last-Event-ID` header — missed events are replayed from the circular
 * buffer before switching to live streaming.
 */

import { NextRequest } from "next/server";
import { getSession } from "@server/swarm/registry";
import type { NotificationEvent } from "@shared/types/swarm";
import { createLogger } from "@server/utils/logger";

const logger = createLogger("api:swarm:stream");

function encodeSSEEvent(event: NotificationEvent): string {
  return `id: ${event.metadata.sequence_number}\ndata: ${JSON.stringify(event)}\n\n`;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;
  const session = getSession(taskId);

  if (!session) {
    return new Response(JSON.stringify({ error: "Task not found", task_id: taskId }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { notifier } = session;
  const encoder = new TextEncoder();

  // Check for Last-Event-ID for reconnect replay
  const lastEventIdHeader = request.headers.get("Last-Event-ID");
  const lastSeenSequence = lastEventIdHeader !== null ? parseInt(lastEventIdHeader, 10) : -1;

  const stream = new ReadableStream({
    start(controller) {
      // Replay buffered events the client missed.
      // On initial connection (lastSeenSequence === -1): replay ALL buffered events
      // so events emitted between POST response and SSE connect are not lost.
      // On reconnect (lastSeenSequence >= 0): replay only events after the last seen.
      const missed = lastSeenSequence >= 0
        ? notifier.getBufferAfter(lastSeenSequence)
        : notifier.getBuffer();

      let alreadyTerminal = false;
      if (missed.length > 0) {
        logger.info("SSE stream — replaying buffered events", {
          taskId,
          lastSeenSequence,
          replayCount: missed.length,
        });
        for (const event of missed) {
          controller.enqueue(encoder.encode(encodeSSEEvent(event)));
          if (
            event.event_type === "AGENT_STATE_CHANGE" &&
            event.payload.terminal === true
          ) {
            alreadyTerminal = true;
          }
        }
      }

      // If the task already reached a terminal state during replay, close immediately
      if (alreadyTerminal) {
        logger.info("SSE stream closing — terminal event found in replay", { taskId });
        controller.close();
        return;
      }

      // Subscribe to live events
      const unsubscribe = notifier.subscribe((event: NotificationEvent) => {
        try {
          controller.enqueue(encoder.encode(encodeSSEEvent(event)));

          // Close the stream on terminal state events
          if (
            event.event_type === "AGENT_STATE_CHANGE" &&
            event.payload.terminal === true
          ) {
            logger.info("SSE stream closing — terminal event received", { taskId });
            unsubscribe();
            controller.close();
          }
        } catch {
          // Controller may already be closed (client disconnect)
          unsubscribe();
        }
      });

      // Handle client disconnect via abort signal
      request.signal.addEventListener("abort", () => {
        logger.info("SSE stream aborted by client", { taskId });
        unsubscribe();
        try {
          controller.close();
        } catch {
          // Already closed — safe to ignore
        }
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
