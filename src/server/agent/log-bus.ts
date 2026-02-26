import type { StreamEvent } from "@shared/types/agent";
import type { LogEntry } from "@shared/types/log";

type LogSubscriber = (entry: LogEntry) => void;

class LogBus {
  private subscribers = new Set<LogSubscriber>();
  // Mantém os últimos 500 entries para novos conectados
  private history: LogEntry[] = [];
  private readonly MAX_HISTORY = 500;

  publish(event: StreamEvent, sessionId: string): void {
    const entry: LogEntry = {
      ...event,
      sessionId,
      wallTime: new Date().toISOString(),
    };
    this.history.push(entry);
    if (this.history.length > this.MAX_HISTORY) {
      this.history.shift();
    }
    for (const sub of this.subscribers) {
      sub(entry);
    }
  }

  subscribe(callback: LogSubscriber): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  getHistory(): LogEntry[] {
    return [...this.history];
  }

  clear(): void {
    this.history = [];
  }
}

// Singleton: garantido pelo module cache do Node.js
export const logBus = new LogBus();
