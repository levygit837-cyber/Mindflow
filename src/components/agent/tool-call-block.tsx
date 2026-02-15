"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getToolConfig,
  SpinnerIcon,
  CheckIcon,
  ErrorIcon,
} from "./tool-icon-map";

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
      return val.length > 60 ? val.slice(0, 57) + "..." : val;
    }
  }
  const keys = Object.keys(args);
  if (keys.length === 0) return "";
  const first = String(args[keys[0]] ?? "");
  return first.length > 60 ? first.slice(0, 57) + "..." : first;
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
    <span className="text-[10px] font-mono text-blue-400/80 tabular-nums">
      {formatDuration(elapsed)}
    </span>
  );
}

function StatusIndicator({ status }: { status: ToolCallBlockProps["status"] }) {
  switch (status) {
    case "pending":
      return <SpinnerIcon className="h-3 w-3 animate-pulse text-muted-foreground" />;
    case "running":
      return <SpinnerIcon className="h-3 w-3 animate-spin text-blue-500" />;
    case "success":
      return <CheckIcon className="h-3 w-3 text-green-500" />;
    case "error":
      return <ErrorIcon className="h-3 w-3 text-red-500" />;
  }
}

function truncateOutput(output: string, limit = 200): string {
  if (output.length <= limit) return output;
  return output.slice(0, limit) + "...";
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
    <div
      className={cn(
        "mb-2 rounded-lg border transition-all duration-200",
        status === "running" && "border-blue-500/30 bg-blue-500/5 shadow-sm shadow-blue-500/5",
        status === "success" && "border-green-500/20 bg-green-500/5",
        status === "error" && "border-red-500/20 bg-red-500/5",
        status === "pending" && "border-muted bg-muted/20"
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors hover:bg-muted/30 rounded-lg"
      >
        <Icon
          className={cn("h-3.5 w-3.5 shrink-0", {
            "text-blue-500 animate-pulse": status === "running",
            "text-green-500": status === "success",
            "text-red-500": status === "error",
            "text-muted-foreground": status === "pending",
          })}
        />

        <span className="font-medium text-foreground/90">{config.label}</span>

        {agentId && (
          <span className="rounded bg-muted px-1 py-0.5 text-[10px] font-medium uppercase opacity-60">
            {agentId}
          </span>
        )}

        {!expanded && summary && (
          <span className="min-w-0 flex-1 truncate text-muted-foreground/60 font-mono text-[11px]">
            {summary}
          </span>
        )}

        {/* Output preview when collapsed and completed */}
        {!expanded && status === "success" && toolOutput && !summary && (
          <span className="min-w-0 flex-1 truncate text-muted-foreground/50 text-[11px]">
            {truncateOutput(toolOutput, 60)}
          </span>
        )}

        <span className="ml-auto flex items-center gap-1.5 shrink-0">
          {status === "running" && <ElapsedTimer startedAt={startedAt} />}
          {completedMs != null && (
            <span className="text-[10px] font-mono text-muted-foreground/60 tabular-nums">
              {formatDuration(completedMs)}
            </span>
          )}
          <StatusIndicator status={status} />
          {expanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          )}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-muted/50 space-y-2 px-3 pb-3 pt-2 text-xs">
          {Object.keys(toolInput).length > 0 && (
            <div>
              <span className="font-medium text-muted-foreground text-[10px] uppercase tracking-wider">Input</span>
              <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-muted/40 p-2 text-[11px] font-mono">
                {JSON.stringify(toolInput, null, 2)}
              </pre>
            </div>
          )}

          {toolOutput != null && (
            <div>
              <span className="font-medium text-muted-foreground text-[10px] uppercase tracking-wider">Output</span>
              <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-muted/40 p-2 text-[11px] font-mono">
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
