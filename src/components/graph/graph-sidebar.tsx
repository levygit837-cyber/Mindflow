"use client";

import { useRouter } from "next/navigation";
import { X, Bot, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import type { GraphNode } from "@/types/graph";

interface GraphSidebarProps {
  selectedNodes: GraphNode[];
  onClear: () => void;
}

export function GraphSidebar({ selectedNodes, onClear }: GraphSidebarProps) {
  const router = useRouter();

  if (selectedNodes.length === 0) {
    return (
      <div className="w-72 border-l p-4 flex flex-col items-center justify-center text-center text-muted-foreground">
        <Globe className="h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm">Click nodes to select them</p>
        <p className="text-xs mt-1">Selected notes will appear here</p>
      </div>
    );
  }

  const handleAskAI = () => {
    const noteIds = selectedNodes.map((n) => n.id).join(",");
    router.push(`/agent?notes=${noteIds}`);
  };

  return (
    <div className="w-72 border-l flex flex-col">
      <div className="p-3 border-b flex items-center justify-between">
        <h3 className="font-semibold text-sm">
          Selected ({selectedNodes.length})
        </h3>
        <Button variant="ghost" size="sm" onClick={onClear}>
          Clear
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-2">
          {selectedNodes.map((node) => (
            <div
              key={node.id}
              className="flex items-start gap-2 p-2 rounded-md bg-accent/50"
            >
              <span>{node.emoji}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{node.title}</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {node.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-[10px] px-1 py-0">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      <div className="p-3 border-t space-y-2">
        <Button className="w-full" onClick={handleAskAI}>
          <Bot className="h-4 w-4 mr-2" />
          Ask AI about these notes
        </Button>
      </div>
    </div>
  );
}

function Globe(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
      <path d="M2 12h20" />
    </svg>
  );
}
