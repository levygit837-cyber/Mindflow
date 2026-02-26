"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronRight, Loader2, X } from "lucide-react";
import { cn } from "@client/lib/utils";
import { getToolConfig } from "./tool-icon-map";

interface ToolCallBlockProps {
  id: string;
  toolName: string;
  toolInput: Record<string, unknown>;
  toolOutput: string | null | undefined;
  status: "pending" | "running" | "success" | "error";
  startedAt: string;
  completedAt?: string;
  agentId?: string;
  agentColor?: string;
}

function argsSummary(toolName: string, args: Record<string, unknown>): string {
  for (const key of ["path", "filePath", "file_path", "noteId", "query", "command", "pattern", "url", "glob"]) {
    if (key in args && args[key] != null) {
      const val = String(args[key]);
      return val.length > 50 ? val.slice(0, 47) + "..." : val;
    }
  }
  const keys = Object.keys(args);
  if (keys.length === 0) return "";
  const first = String(args[keys[0]] ?? "");
  return first.length > 50 ? first.slice(0, 47) + "..." : first;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}

function ElapsedTimer({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(new Date(startedAt).getTime());

  useEffect(() => {
    startRef.current = new Date(startedAt).getTime();
    const interval = setInterval(() => {
      setElapsed(Date.now() - startRef.current);
    }, 100);
    return () => clearInterval(interval);
  }, [startedAt]);

  return (
    <span className="text-[10px] font-mono text-zinc-600 tabular-nums">
      {formatDuration(elapsed)}
    </span>
  );
}

function StatusDot({ status }: { status: ToolCallBlockProps["status"] }) {
  switch (status) {
    case "pending":
      return <span className="h-1.5 w-1.5 rounded-full bg-zinc-600" />;
    case "running":
      return <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />;
    case "success":
      return <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />;
    case "error":
      return <X className="h-3 w-3 text-red-400/70" />;
  }
}

function ToolCallBlockInner({
  toolName,
  toolInput,
  toolOutput,
  status,
  startedAt,
  completedAt,
  agentId,
}: ToolCallBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const config = getToolConfig(toolName);
  const Icon = config.icon;
  const summary = argsSummary(toolName, toolInput);

  const completedMs = completedAt
    ? new Date(completedAt).getTime() - new Date(startedAt).getTime()
    : null;

  return (
    <div className="py-0.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors text-left"
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 text-zinc-600 shrink-0 transition-transform duration-200",
            expanded && "rotate-90"
          )}
        />

        <StatusDot status={status} />

        <Icon className="h-3 w-3 shrink-0 text-zinc-500" />

        <span className="font-medium text-zinc-400">{config.label}</span>

        {agentId && (
          <span className="text-[10px] text-zinc-600 font-mono">
            [{agentId}]
          </span>
        )}

        {summary && (
          <span className="min-w-0 flex-1 truncate text-zinc-600 font-mono text-[11px]">
            {summary}
          </span>
        )}

        <span className="ml-auto flex items-center gap-1.5 shrink-0">
          {status === "running" && <ElapsedTimer startedAt={startedAt} />}
          {completedMs != null && (
            <span className="text-[10px] font-mono text-zinc-600 tabular-nums">
              {formatDuration(completedMs)}
            </span>
          )}
        </span>
      </button>

      {expanded && (
        <div className="ml-4 mt-1 pl-3 border-l border-zinc-800 space-y-2 pb-1">
          {Object.keys(toolInput).length > 0 && (
            <div>
              <span className="text-[10px] font-medium text-zinc-600 uppercase tracking-wider">
                Input
              </span>
              <pre className="mt-0.5 max-h-32 overflow-auto whitespace-pre-wrap rounded-lg bg-zinc-900/50 border border-zinc-800 p-2 text-[11px] font-mono text-zinc-500">
                {JSON.stringify(toolInput, null, 2)}
              </pre>
            </div>
          )}

          {toolOutput != null && (
            <div>
              <span className="text-[10px] font-medium text-zinc-600 uppercase tracking-wider">
                Output
              </span>
              <pre className="mt-0.5 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-zinc-900/50 border border-zinc-800 p-2 text-[11px] font-mono text-zinc-500">
                {toolOutput}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export const ToolCallBlock = React.memo(ToolCallBlockInner);
