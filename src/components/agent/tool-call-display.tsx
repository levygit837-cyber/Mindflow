"use client";

import { Wrench, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ToolCallInfo } from "@/types/agent";

interface ToolCallDisplayProps {
  toolCalls: ToolCallInfo[];
}

const toolLabels: Record<string, string> = {
  read_note: "Reading note",
  search_notes: "Searching notes",
  get_notes_context: "Loading notes context",
  list_notes: "Listing notes",
  link_notes: "Linking notes",
  read_file: "Reading file",
  write_file: "Writing file",
  glob: "Searching files",
  grep: "Searching content",
  ls: "Listing directory",
};

export function ToolCallDisplay({ toolCalls }: ToolCallDisplayProps) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      {toolCalls.map((tc, i) => (
        <Badge key={i} variant="outline" className="text-[10px] gap-1">
          {tc.result ? <Check className="h-3 w-3 text-green-500" /> : <Wrench className="h-3 w-3 animate-spin" />}
          {toolLabels[tc.name] || tc.name}
          {tc.args && typeof tc.args === "object" && "noteId" in tc.args && (
            <span className="text-muted-foreground">: {String(tc.args.noteId).slice(0, 8)}...</span>
          )}
          {tc.args && typeof tc.args === "object" && "query" in tc.args && (
            <span className="text-muted-foreground">: &ldquo;{String(tc.args.query)}&rdquo;</span>
          )}
        </Badge>
      ))}
    </div>
  );
}
