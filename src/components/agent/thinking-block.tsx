"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronRight } from "lucide-react";
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

function parseReasoningContent(text: string): React.ReactNode[] {
  if (!text) return [];
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-zinc-300">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

function ThinkingBlockInner({
  content,
  isStreaming,
  agentId,
}: ThinkingBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isStreaming && expanded && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [content, isStreaming, expanded]);

  if (!content && !isStreaming) return null;

  const tokenCount = estimateTokenCount(content);

  // Streaming state: compact inline indicator
  if (isStreaming && !expanded) {
    return (
      <div className="flex items-center gap-2 py-1.5 animate-fade-in-up">
        <button
          onClick={() => setExpanded(true)}
          className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-zinc-500/40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-zinc-500" />
          </span>
          <span className="font-medium">
            {agentId ? `${agentId} thinking` : "Thinking"}
          </span>
          <span className="text-zinc-600 font-mono text-[10px]">
            ~{formatTokenCount(tokenCount)}t
          </span>
          <ChevronRight className="h-3 w-3 text-zinc-600" />
        </button>
      </div>
    );
  }

  // Completed or expanded state: compact expandable
  return (
    <div className="py-1 animate-fade-in-up">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 text-zinc-600 transition-transform duration-200",
            expanded && "rotate-90"
          )}
        />
        <span className="font-medium">
          {agentId ? `${agentId} thought` : "Thought"}
        </span>
        <span className="text-zinc-600 font-mono text-[10px]">
          {formatTokenCount(tokenCount)} tokens
        </span>
      </button>

      {expanded && (
        <div className="mt-1.5 ml-4 pl-3 border-l border-zinc-800">
          <div
            ref={scrollRef}
            className="max-h-72 overflow-y-auto whitespace-pre-wrap text-xs text-zinc-500 leading-relaxed font-mono scrollbar-thin"
          >
            {parseReasoningContent(content)}
            {isStreaming && (
              <span className="ml-0.5 inline-block w-1 h-3 bg-zinc-500 animate-typewriter-blink rounded-sm" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export const ThinkingBlock = React.memo(ThinkingBlockInner);
