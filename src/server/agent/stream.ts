import type { StreamEvent } from "@shared/types/agent";

export function encodeSSE(event: StreamEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

export function createSSEStream() {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController | null = null;

  const stream = new ReadableStream({
    start(c) {
      controller = c;
    },
  });

  return {
    stream,
    send(event: StreamEvent) {
      if (controller) {
        try {
          controller.enqueue(encoder.encode(encodeSSE(event)));
        } catch (e) {
          // Ignore if stream is already closed
        }
      }
    },
    close() {
      if (controller) {
        try {
          controller.close();
        } catch (e) {
          // Ignore if stream is already closed
        }
      }
    },
  };
}
