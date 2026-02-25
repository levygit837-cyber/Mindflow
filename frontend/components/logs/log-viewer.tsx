"use client";

import React, { useEffect, useRef, useState } from "react";
import { Download, Trash2, ChevronDown, ChevronUp, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useLogStream, type LogFilter } from "@/hooks/use-log-stream";
import type { LogEntry } from "@/lib/agent/log-bus";

const FILTER_OPTIONS: { value: LogFilter; label: string }[] = [
  { value: "all", label: "ALL" },
  { value: "thought", label: "THOUGHT" },
  { value: "tool_call", label: "TOOL" },
  { value: "tool_result", label: "RESULT" },
  { value: "response", label: "RESP" },
  { value: "agent_step", label: "STEP" },
  { value: "error", label: "ERROR" },
];

const TYPE_COLORS: Record<string, string> = {
  thought: "text-violet-400",
  tool_call: "text-yellow-400",
  tool_result: "text-green-400",
  response: "text-zinc-300",
  agent_step: "text-blue-400",
  done: "text-emerald-400",
  error: "text-red-400",
  step: "text-zinc-500",
  notifier: "text-zinc-500",
};

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toTimeString().slice(0, 8) + "." + String(d.getMilliseconds()).padStart(3, "0");
  } catch {
    return iso.slice(11, 23);
  }
}

function summarizeData(type: string, data: string): string {
  if (!data) return "";
  if (type === "tool_call" || type === "tool_result") {
    try {
      const parsed = JSON.parse(data) as { name?: string; result?: string; args?: unknown };
      if (parsed.name) {
        const extra = typeof parsed.result === "string" && parsed.result
          ? ` → ${parsed.result.slice(0, 60)}`
          : parsed.args
          ? `(${JSON.stringify(parsed.args).slice(0, 60)})`
          : "";
        return `${parsed.name}${extra}`;
      }
    } catch {
      // fall through
    }
  }
  return data.length > 120 ? data.slice(0, 120) + "…" : data;
}

function LogRow({ entry }: { entry: LogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const color = TYPE_COLORS[entry.type] ?? "text-zinc-400";

  return (
    <div className="border-b border-zinc-800/50 hover:bg-white/[0.02] transition-colors">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-2 px-3 py-1.5 text-left"
      >
        <span className="text-zinc-600 font-mono text-[10px] shrink-0 pt-0.5 tabular-nums">
          {formatTime(entry.wallTime)}
        </span>
        <span className={cn("font-mono text-[10px] font-bold shrink-0 pt-0.5 w-16", color)}>
          [{entry.type.toUpperCase().slice(0, 8)}]
        </span>
        <span className="text-zinc-400 text-[11px] font-mono truncate flex-1 min-w-0">
          {summarizeData(entry.type, entry.data)}
        </span>
        {expanded ? (
          <ChevronUp className="h-3 w-3 text-zinc-600 shrink-0 mt-0.5" />
        ) : (
          <ChevronDown className="h-3 w-3 text-zinc-600 shrink-0 mt-0.5" />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-2">
          <pre className="text-[10px] font-mono text-zinc-500 bg-zinc-900/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all border border-zinc-800">
            {JSON.stringify(entry, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export function LogViewer() {
  const {
    entries,
    connected,
    filter,
    setFilter,
    autoScroll,
    setAutoScroll,
    clearEntries,
    exportJson,
    resetUnread,
  } = useLogStream();

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    resetUnread();
  }, [resetUnread]);

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [entries, autoScroll]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] backdrop-blur-sm bg-white/[0.02]">
        <div className="flex items-center gap-2">
          {connected ? (
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-red-400" />
          )}
          <span className="text-xs text-zinc-400 font-medium">
            Agent Logs
          </span>
          <span className="text-xs text-zinc-600 font-mono">
            ({entries.length})
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setAutoScroll((v) => !v)}
            className={cn(
              "text-xs h-7 px-2",
              autoScroll
                ? "text-zinc-300"
                : "text-zinc-600"
            )}
          >
            Auto-scroll
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={exportJson}
            className="text-muted-foreground/60 hover:text-foreground/80 hover:bg-white/[0.05] h-7 px-2"
          >
            <Download className="h-3.5 w-3.5 mr-1" />
            Export
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearEntries}
            className="text-muted-foreground/60 hover:text-foreground/80 hover:bg-white/[0.05] h-7 px-2"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            Clear
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-1 px-3 py-1.5 border-b border-white/[0.04] overflow-x-auto">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFilter(opt.value)}
            className={cn(
              "text-[10px] font-mono font-bold px-2 py-0.5 rounded shrink-0 transition-colors",
              filter === opt.value
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-600 hover:text-zinc-400"
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Log entries */}
      <ScrollArea className="flex-1">
        {entries.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-zinc-600 text-xs font-mono">
            {connected ? "Aguardando eventos do agente..." : "Desconectado"}
          </div>
        ) : (
          <div>
            {entries.map((entry) => (
              <LogRow key={entry.id} entry={entry} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
