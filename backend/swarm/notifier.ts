/**
 * NotifierService — central event broadcasting service for the swarm.
 *
 * Manages a circular buffer of NotificationEvents and broadcasts them
 * to all subscribers in real-time. Each event gets a UUID v4, ISO timestamp,
 * and monotonically increasing sequence number.
 */

import { v4 as uuidv4 } from "uuid";
import { createLogger } from "@/utils/logger";
import type {
  SwarmEventType,
  SwarmAgentId,
  NotificationEvent,
} from "@/types/swarm";

const logger = createLogger("swarm:notifier");

const DEFAULT_BUFFER_CAP = 500;

export type NotifierSubscriber = (event: NotificationEvent) => void;

export class NotifierService {
  private readonly taskId: string;
  private readonly bufferCap: number;
  private buffer: NotificationEvent[];
  private subscribers: Set<NotifierSubscriber>;
  private sequence: number;

  constructor(taskId: string, bufferCap: number = DEFAULT_BUFFER_CAP) {
    this.taskId = taskId;
    this.bufferCap = bufferCap;
    this.buffer = [];
    this.subscribers = new Set();
    this.sequence = 0;
  }

  /**
   * Emit a new notification event.
   *
   * Creates a fully-formed NotificationEvent with UUID, timestamp, and
   * monotonic sequence number. Stores it in the circular buffer and
   * broadcasts to all active subscribers.
   */
  emit(
    type: SwarmEventType,
    agentId: SwarmAgentId,
    payload: Record<string, unknown>
  ): NotificationEvent {
    const event: NotificationEvent = {
      event_id: uuidv4(),
      event_type: type,
      agent_id: agentId,
      timestamp: new Date().toISOString(),
      payload,
      metadata: {
        task_id: this.taskId,
        sequence_number: this.sequence++,
      },
    };

    // Circular buffer: drop oldest when at capacity
    if (this.buffer.length >= this.bufferCap) {
      this.buffer.shift();
    }
    this.buffer.push(event);

    // Broadcast to all subscribers
    for (const callback of this.subscribers) {
      try {
        callback(event);
      } catch (err) {
        logger.error("Subscriber callback error", { error: err });
      }
    }

    logger.debug("Event emitted", {
      event_type: type,
      agent_id: agentId,
      sequence: event.metadata.sequence_number,
    });

    return event;
  }

  /**
   * Subscribe to receive events as they are emitted.
   * Returns an unsubscribe function.
   */
  subscribe(callback: NotifierSubscriber): () => void {
    this.subscribers.add(callback);
    logger.debug("Subscriber added", { total: this.subscribers.size });

    return () => {
      this.subscribers.delete(callback);
      logger.debug("Subscriber removed", { total: this.subscribers.size });
    };
  }

  /**
   * Returns all currently buffered events (up to bufferCap).
   */
  getBuffer(): NotificationEvent[] {
    return [...this.buffer];
  }

  /**
   * Returns events from the buffer with a sequence number greater than
   * the given value. Useful for SSE reconnect / replay.
   */
  getBufferAfter(afterSequence: number): NotificationEvent[] {
    return this.buffer.filter(
      (e) => e.metadata.sequence_number > afterSequence
    );
  }

  /**
   * Returns the current sequence counter (the next sequence number to be assigned).
   */
  getSequence(): number {
    return this.sequence;
  }

  /**
   * Returns the task ID this notifier is bound to.
   */
  getTaskId(): string {
    return this.taskId;
  }
}
