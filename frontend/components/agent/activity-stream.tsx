"use client";

import { useMemo } from "react";
import { Badge } from "@frontend/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@frontend/components/ui/tooltip";
import {
  Wrench,
  Check,
  Loader2,
  FileText,
  Search,
  List,
  Link2,
  FileInput,
  FileOutput,
  Pencil,
  Folder,
} from "lucide-react";
import { ThinkingBlock } from "./thinking-block";
import type { AgentActivity, ToolActivity } from "@shared/types/agent";

interface ActivityStreamProps {
  activities: AgentActivity[];
  isStreaming: boolean;
  activeThinkingId?: string;
}

const toolMeta: Record<string, { label: string; icon: typeof Wrench }> = {
  read_note: { label: "Read Note", icon: FileText },
  search_notes: { label: "Search Notes", icon: Search },
  get_notes_context: { label: "Load Notes Context", icon: FileText },
  list_notes: { label: "List Notes", icon: List },
  link_notes: { label: "Link Notes", icon: Link2 },
  read_file: { label: "Read File", icon: FileInput },
  write_file: { label: "Write File", icon: FileOutput },
  edit_file: { label: "Edit File", icon: Pencil },
  glob: { label: "Find Files", icon: Folder },
  grep: { label: "Search Content", icon: Search },
  ls: { label: "List Directory", icon: List },
};

function ToolCallChip({ tool }: { tool: ToolActivity }) {
  const meta = toolMeta[tool.name];
  const Icon = meta?.icon || Wrench;
  const label = meta?.label || tool.name || "Tool";

  const tooltipContent = useMemo(() => {
    const parts: string[] = [];
    if (tool.args && Object.keys(tool.args).length > 0) {
      parts.push(`args: ${JSON.stringify(tool.args, null, 2)}`);
    }
    if (tool.result) {
      parts.push(`result: ${tool.result}`);
    }
    return parts.join("\n\n");
  }, [tool.args, tool.result]);

  const statusIcon = tool.result ? (
    <Check className="h-3 w-3 text-green-500" />
  ) : (
    <Loader2 className="h-3 w-3 animate-spin" />
  );

  const chip = (
    <Badge variant="outline" className="text-[10px] gap-1.5">
      <Icon className="h-3 w-3" />
      <span>{label}</span>
      {statusIcon}
    </Badge>
  );

  if (!tooltipContent) return chip;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{chip}</TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs whitespace-pre-wrap text-xs">
        {tooltipContent}
      </TooltipContent>
    </Tooltip>
  );
}

export function ActivityStream({ activities, isStreaming, activeThinkingId }: ActivityStreamProps) {
  if (!activities || activities.length === 0) return null;

  return (
    <TooltipProvider delayDuration={150}>
      <div className="mb-2 flex flex-col gap-2">
        {activities.map((activity) => {
          if (activity.type === "thinking") {
            return (
              <ThinkingBlock
                key={activity.id}
                id={activity.id}
                content={activity.text}
                isStreaming={isStreaming && activity.id === activeThinkingId}
              />
            );
          }

          return <ToolCallChip key={activity.id} tool={activity} />;
        })}
      </div>
    </TooltipProvider>
  );
}
