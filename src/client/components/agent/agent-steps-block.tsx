"use client";

import React, { useState } from "react";
import { ChevronRight, GitBranch, Loader2 } from "lucide-react";
import { cn } from "@client/lib/utils";

interface AgentStepsBlockProps {
  id: string;
  stepName: string;
  detail: string;
  status: "running" | "completed";
  subSteps: string[];
  startedAt: string;
  completedAt?: string;
  hidden?: boolean;
}

function AgentStepsBlockInner({
  stepName,
  detail,
  status,
  subSteps,
  startedAt,
  completedAt,
  hidden,
}: AgentStepsBlockProps) {
  const [expanded, setExpanded] = useState(status === "running");

  if (hidden) return null;

  const duration = completedAt
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

        {status === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />
        ) : (
          <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
        )}

        <GitBranch className="h-3 w-3 shrink-0 text-zinc-500" />

        <span className="font-medium text-zinc-400">{stepName}</span>

        {detail && (
          <span className="min-w-0 flex-1 truncate text-zinc-600 text-[11px]">
            {detail}
          </span>
        )}

        {duration != null && (
          <span className="ml-auto text-[10px] font-mono text-zinc-600 tabular-nums">
            {duration < 1000
              ? `${duration}ms`
              : `${(duration / 1000).toFixed(1)}s`}
          </span>
        )}
      </button>

      {expanded && subSteps.length > 0 && (
        <div className="ml-4 mt-1 pl-3 border-l border-zinc-800 space-y-0.5 pb-1">
          {subSteps.map((step, i) => (
            <div
              key={i}
              className="flex items-center gap-1.5 text-[11px] text-zinc-600 font-mono"
            >
              <span className="h-1 w-1 rounded-full bg-zinc-700 shrink-0" />
              {step}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const AgentStepsBlock = React.memo(AgentStepsBlockInner);
