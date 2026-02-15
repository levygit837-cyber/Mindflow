"use client";

import React, { useState, useMemo } from "react";
import { Brain, ChevronDown, ChevronRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThinkingBlockProps {
  id: string;
  content: string;
  isStreaming: boolean;
  agentId?: string;
  agentColor?: string;
}

function estimateTokenCount(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

function formatTokenCount(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return String(count);
}

function ThinkingBlockInner({
  content,
  isStreaming,
  agentId,
}: ThinkingBlockProps) {
  // Auto-collapsed by default - user can expand to see reasoning
  const [expanded, setExpanded] = useState(false);

  if (!content && !isStreaming) return null;

  const tokenCount = useMemo(() => estimateTokenCount(content), [content]);
  const preview = useMemo(() => {
    if (!content) return "";
    const firstLine = content.split("\n")[0] || "";
    return firstLine.length > 80 ? firstLine.slice(0, 77).trimEnd() + "..." : firstLine;
  }, [content]);

  return (
    <div
      className={cn(
        "mb-2 rounded-lg border border-purple-500/20 bg-purple-500/5 dark:bg-purple-400/5 transition-all duration-200",
        isStreaming && "border-purple-500/40 shadow-sm shadow-purple-500/10"
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors hover:bg-purple-500/10 rounded-lg"
      >
        {isStreaming ? (
          <Sparkles className="h-3.5 w-3.5 shrink-0 text-purple-400 animate-pulse" />
        ) : (
          <Brain className="h-3.5 w-3.5 shrink-0 text-purple-500/70" />
        )}

        <span className="font-medium text-purple-600 dark:text-purple-400">
          {agentId ? `${agentId} - ` : ""}
          {isStreaming ? "Reasoning..." : "Reasoning"}
        </span>

        {!expanded && preview && (
          <span className="min-w-0 flex-1 truncate text-muted-foreground/60 italic">
            {preview}
          </span>
        )}

        <span className="ml-auto flex items-center gap-2 shrink-0">
          <span className="rounded-full bg-purple-500/10 px-2 py-0.5 text-[10px] font-mono text-purple-500/80">
            {isStreaming ? `~${formatTokenCount(tokenCount)} tokens` : `${formatTokenCount(tokenCount)} tokens`}
          </span>
          {expanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          )}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-purple-500/10 px-3 pb-3 pt-2">
          <div className="max-h-96 overflow-y-auto whitespace-pre-wrap text-xs text-muted-foreground leading-relaxed font-mono">
            {content}
            {isStreaming && (
              <span className="ml-0.5 inline-block w-1.5 h-3.5 bg-purple-400 animate-blink rounded-sm" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export const ThinkingBlock = React.memo(ThinkingBlockInner);
