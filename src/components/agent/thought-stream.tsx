"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThoughtStreamProps {
  thoughts: string;
  isStreaming: boolean;
}

export function ThoughtStream({ thoughts, isStreaming }: ThoughtStreamProps) {
  const [expanded, setExpanded] = useState(false);

  if (!thoughts) return null;

  return (
    <div className="mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Brain className="h-3 w-3" />
        {isStreaming ? "Thinking..." : "Thoughts"}
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
      </button>
      {expanded && (
        <div className="mt-1 text-xs text-muted-foreground bg-muted/50 rounded p-2 whitespace-pre-wrap max-h-48 overflow-auto">
          {thoughts}
          {isStreaming && <span className="animate-pulse">|</span>}
        </div>
      )}
    </div>
  );
}
