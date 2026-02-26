"use client";

import { useEffect, useRef } from "react";
import { useSwarmStore } from "@client/stores/swarm.store";
import type { NotificationEvent } from "@shared/types/swarm";

/**
 * Hook that connects to the swarm SSE stream for a given task and routes
 * incoming NotificationEvents into the Zustand store.
 *
 * Automatically connects when `taskId` is non-null and disconnects on
 * unmount or when `taskId` changes. Uses the native `EventSource` API
 * which handles automatic reconnect with `Last-Event-ID`.
 */
export function useSwarmStream(taskId: string | null) {
  const updateFromEvent = useSwarmStore((s) => s.updateFromEvent);
  const setConnected = useSwarmStore((s) => s.setConnected);
  const disconnect = useSwarmStore((s) => s.disconnect);

  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!taskId) {
      // No task — make sure we're cleaned up
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      disconnect();
      return;
    }

    const url = `/api/swarm/${taskId}/stream`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
    };

    es.onmessage = (msg) => {
      try {
        const event: NotificationEvent = JSON.parse(msg.data);
        updateFromEvent(event);
      } catch {
        // Ignore malformed events
      }
    };

    es.onerror = () => {
      // EventSource auto-reconnects on transient errors.
      // If it transitions to CLOSED we mark as disconnected.
      if (es.readyState === EventSource.CLOSED) {
        setConnected(false);
      }
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      disconnect();
    };
  }, [taskId, updateFromEvent, setConnected, disconnect]);
}
