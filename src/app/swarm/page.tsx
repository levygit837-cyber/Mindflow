"use client";

import { useSwarmStore } from "@client/stores/swarm.store";
import { useSwarmStream } from "@client/hooks/use-swarm-stream";
import { TaskInput } from "@client/components/swarm/task-input";
import { TokenStreamPanel } from "@client/components/swarm/token-stream-panel";
import { AnalystPanel } from "@client/components/swarm/analyst-panel";
import { ReviewerPanel } from "@client/components/swarm/reviewer-panel";
import { SandboxPanel } from "@client/components/swarm/sandbox-panel";
import { NotificationFeed } from "@client/components/swarm/notification-feed";
import { Badge } from "@client/components/ui/badge";

const statusLabels: Record<string, { label: string; className: string }> = {
  pending: { label: "Pending", className: "bg-muted text-muted-foreground" },
  planning: { label: "Planning", className: "bg-indigo-500/20 text-indigo-400" },
  coding: { label: "Coding", className: "bg-blue-500/20 text-blue-400" },
  reviewing: { label: "Reviewing", className: "bg-amber-500/20 text-amber-400" },
  complete: { label: "Complete", className: "bg-green-500/20 text-green-400" },
  error: { label: "Error", className: "bg-red-500/20 text-red-400" },
};

export default function SwarmPage() {
  const taskId = useSwarmStore((s) => s.taskId);
  const taskStatus = useSwarmStore((s) => s.taskStatus);
  const isConnected = useSwarmStore((s) => s.isConnected);

  useSwarmStream(taskId);

  const status = statusLabels[taskStatus] ?? statusLabels.pending;

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header + Task Input */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Swarm Dashboard</h2>
            <p className="text-sm text-muted-foreground">
              Multi-agent coding session orchestrator
            </p>
          </div>
          <div className="flex items-center gap-2">
            {taskId && (
              <>
                <Badge variant="outline" className={status.className}>
                  {status.label}
                </Badge>
                {isConnected && (
                  <span className="flex items-center gap-1 text-xs text-green-500">
                    <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    Live
                  </span>
                )}
              </>
            )}
          </div>
        </div>
        <TaskInput />
      </div>

      {/* Main grid: left (Coder + Sandbox), right (Analyst + Reviewer) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-0">
        {/* Left column */}
        <div className="flex flex-col gap-4 min-h-0">
          <div className="flex-1 min-h-[200px]">
            <TokenStreamPanel />
          </div>
          <div className="h-[280px] shrink-0">
            <SandboxPanel />
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4 min-h-0">
          <div className="flex-1 min-h-[200px]">
            <AnalystPanel />
          </div>
          <div className="flex-1 min-h-[200px]">
            <ReviewerPanel />
          </div>
        </div>
      </div>

      {/* Notification feed at bottom */}
      <div className="h-[240px] shrink-0">
        <NotificationFeed />
      </div>
    </div>
  );
}
