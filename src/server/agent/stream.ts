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
        controller.enqueue(encoder.encode(encodeSSE(event)));
      }
    },
    close() {
      if (controller) {
        controller.close();
      }
    },
  };
}
