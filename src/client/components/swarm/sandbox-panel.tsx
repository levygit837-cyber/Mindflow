"use client";

import { Monitor } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@client/components/ui/card";
import { ScrollArea } from "@client/components/ui/scroll-area";
import { Badge } from "@client/components/ui/badge";
import { useSwarmStore } from "@client/stores/swarm.store";

export function SandboxPanel() {
  const sandboxDisplay = useSwarmStore((s) => s.sandboxDisplay);
  const taskStatus = useSwarmStore((s) => s.taskStatus);

  const isActive =
    taskStatus === "coding" ||
    taskStatus === "planning" ||
    taskStatus === "reviewing";

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Monitor className="h-4 w-4 text-cyan-500" />
            <CardTitle className="text-sm">Sandbox Preview</CardTitle>
          </div>
          {sandboxDisplay && (
            <Badge variant="outline" className="text-xs text-cyan-500 border-cyan-500/30">
              Live
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0">
        <ScrollArea className="h-full">
          <div className="px-4 pb-4">
            {sandboxDisplay ? (
              <pre className="text-xs whitespace-pre font-mono leading-relaxed bg-black/30 rounded-md p-3 overflow-x-auto">
                {sandboxDisplay}
              </pre>
            ) : isActive ? (
              <p className="text-muted-foreground text-sm py-2">
                Generating preview...
              </p>
            ) : (
              <p className="text-muted-foreground text-sm py-2">
                Preview appears when the coder modifies files
              </p>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
