"use client";

import { useRef, useEffect } from "react";
import { Code2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@client/components/ui/card";
import { ScrollArea } from "@client/components/ui/scroll-area";
import { Badge } from "@client/components/ui/badge";
import { useSwarmStore } from "@client/stores/swarm.store";

export function TokenStreamPanel() {
  const coderTokens = useSwarmStore((s) => s.coderTokens);
  const coderPlan = useSwarmStore((s) => s.coderPlan);
  const taskStatus = useSwarmStore((s) => s.taskStatus);
  const bottomRef = useRef<HTMLDivElement>(null);

  const isCoding = taskStatus === "coding" || taskStatus === "planning";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [coderTokens]);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="h-4 w-4 text-blue-500" />
            <CardTitle className="text-sm">Coder Agent</CardTitle>
          </div>
          {isCoding && (
            <Badge variant="secondary" className="text-xs">
              <span className="mr-1 h-2 w-2 rounded-full bg-blue-500 animate-pulse inline-block" />
              {taskStatus === "planning" ? "Planning" : "Coding"}
            </Badge>
          )}
          {taskStatus === "reviewing" && (
            <Badge variant="outline" className="text-xs">Done</Badge>
          )}
          {taskStatus === "complete" && (
            <Badge className="text-xs bg-green-600">Complete</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0">
        <ScrollArea className="h-full">
          <div className="px-4 pb-4">
            {coderPlan && (
              <div className="mb-3 rounded-md border border-blue-500/20 bg-blue-500/5 p-3">
                <p className="text-xs font-medium text-blue-400 mb-1">Plan</p>
                <pre className="text-xs text-muted-foreground whitespace-pre-wrap break-words font-mono">
                  {coderPlan}
                </pre>
              </div>
            )}
            {coderTokens ? (
              <pre className="text-sm whitespace-pre-wrap break-words font-mono leading-relaxed">
                {coderTokens}
                {isCoding && <span className="animate-pulse text-blue-500">|</span>}
              </pre>
            ) : isCoding ? (
              <div className="flex items-center gap-2 text-muted-foreground text-sm py-4">
                <span className="animate-pulse">Thinking...</span>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm py-4">
                Waiting for task submission...
              </p>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
