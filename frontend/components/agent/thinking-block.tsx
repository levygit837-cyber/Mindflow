"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@frontend/lib/utils";

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

  // Streaming state: indicador compacto com preview dos últimos tokens
  if (isStreaming && !expanded) {
    const previewText = content.length > 0
      ? content.slice(-120).replace(/\n+/g, " ").trim()
      : "";

    return (
      <div className="flex flex-col gap-0.5 py-1">
        <button
          onClick={() => setExpanded(true)}
          className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-pulse" />
          <span className="font-medium">
            {agentId ? `${agentId} thinking` : "Thinking"}
          </span>
          {tokenCount > 0 && (
            <span className="text-zinc-600 font-mono text-[10px]">
              ~{formatTokenCount(tokenCount)}t
            </span>
          )}
          <ChevronRight className="h-3 w-3 text-zinc-600" />
        </button>
        {previewText && (
          <div className="ml-4 pl-3 border-l border-zinc-800">
            <span className="text-[10px] font-mono text-zinc-600 italic line-clamp-2">
              {previewText}
              <span className="ml-0.5 inline-block w-1 h-2.5 bg-zinc-600 animate-typewriter-blink rounded-sm align-middle" />
            </span>
          </div>
        )}
      </div>
    );
  }

  // Completed or expanded state: compact expandable
  return (
    <div className="py-1">
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
