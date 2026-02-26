"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { LogEntry } from "@shared/types/log";

export type LogFilter =
  | "all"
  | "thought"
  | "tool_call"
  | "tool_result"
  | "response"
  | "agent_step"
  | "done"
  | "error";

export function useLogStream() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState<LogFilter>("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const seenIds = useRef(new Set<string>());

  useEffect(() => {
    const es = new EventSource("/api/agent/logs/stream");
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (e) => {
      try {
        const entry = JSON.parse(e.data as string) as LogEntry & { type: string };
        if ((entry.type as string) === "connected") return;
        if (!entry.id || seenIds.current.has(entry.id)) return;
        seenIds.current.add(entry.id);

        setEntries((prev) => [...prev, entry as LogEntry]);
        setUnreadCount((n) => n + 1);
      } catch {
        // ignorar eventos malformados
      }
    };

    es.onerror = () => setConnected(false);

    return () => {
      es.close();
      setConnected(false);
    };
  }, []);

  const clearEntries = useCallback(() => {
    setEntries([]);
    seenIds.current.clear();
    setUnreadCount(0);
  }, []);

  const resetUnread = useCallback(() => setUnreadCount(0), []);

  const filteredEntries =
    filter === "all"
      ? entries
      : entries.filter((e) => e.type === filter);

  const exportJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(filteredEntries, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `omnimind-logs-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filteredEntries]);

  return {
    entries: filteredEntries,
    allEntries: entries,
    connected,
    filter,
    setFilter,
    autoScroll,
    setAutoScroll,
    unreadCount,
    resetUnread,
    clearEntries,
    exportJson,
  };
}
