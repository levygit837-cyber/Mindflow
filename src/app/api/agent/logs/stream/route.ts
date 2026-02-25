import { logBus } from "@backend/agent/log-bus";
import type { LogEntry } from "@backend/agent/log-bus";

export const dynamic = "force-dynamic";

export async function GET() {
  const encoder = new TextEncoder();
  let unsubscribe: (() => void) | null = null;

  const stream = new ReadableStream({
    start(controller) {
      // Enviar histórico imediatamente ao conectar
      const history = logBus.getHistory();
      for (const entry of history) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(entry)}\n\n`)
        );
      }

      // Enviar evento de conexão
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ type: "connected" })}\n\n`)
      );

      // Assinar novos eventos
      unsubscribe = logBus.subscribe((entry: LogEntry) => {
        try {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(entry)}\n\n`)
          );
        } catch {
          // Stream fechado pelo cliente — limpar subscriber
          if (unsubscribe) {
            unsubscribe();
            unsubscribe = null;
          }
        }
      });
    },
    cancel() {
      // Cliente desconectou — remover subscriber do LogBus
      if (unsubscribe) {
        unsubscribe();
        unsubscribe = null;
      }
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
