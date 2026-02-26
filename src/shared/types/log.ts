import type { StreamEvent } from "./agent";

export interface LogEntry extends StreamEvent {
  sessionId: string;
  wallTime: string;
}
