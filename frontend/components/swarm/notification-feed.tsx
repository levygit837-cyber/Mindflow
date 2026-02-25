"use client";

import { useMemo } from "react";
import { Bell } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@frontend/components/ui/card";
import { ScrollArea } from "@frontend/components/ui/scroll-area";
import { Badge } from "@frontend/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@frontend/components/ui/select";
import { useSwarmStore } from "@frontend/stores/swarm.store";
import type { SwarmAgentId, SwarmEventType, NotificationEvent } from "@shared/types/swarm";

const AGENT_IDS: SwarmAgentId[] = [
  "orchestrator",
  "coder",
  "live_analyst",
  "reviewer",
  "sandbox_renderer",
];

const EVENT_TYPES: SwarmEventType[] = [
  "AGENT_STATE_CHANGE",
  "TOKEN_STREAM",
  "TOOL_CALL",
  "TOOL_RESULT",
  "FILE_CHANGE",
  "PLAN_UPDATE",
  "ANALYST_FINDING",
  "ANALYST_STATE_CHANGE",
  "REVIEW_FINDING",
  "SANDBOX_UPDATE",
  "ERROR",
];

const agentColors: Record<SwarmAgentId, string> = {
  orchestrator: "bg-slate-500",
  coder: "bg-blue-500",
  live_analyst: "bg-purple-500",
  reviewer: "bg-amber-500",
  sandbox_renderer: "bg-cyan-500",
};

const eventColors: Record<SwarmEventType, string> = {
  AGENT_STATE_CHANGE: "text-slate-400",
  TOKEN_STREAM: "text-blue-400",
  TOOL_CALL: "text-green-400",
  TOOL_RESULT: "text-green-300",
  FILE_CHANGE: "text-yellow-400",
  PLAN_UPDATE: "text-indigo-400",
  ANALYST_FINDING: "text-purple-400",
  ANALYST_STATE_CHANGE: "text-purple-300",
  REVIEW_FINDING: "text-amber-400",
  SANDBOX_UPDATE: "text-cyan-400",
  ERROR: "text-red-400",
};

function formatTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function summarizePayload(event: NotificationEvent): string {
  const p = event.payload;
  switch (event.event_type) {
    case "TOKEN_STREAM":
      return `"${String(p.token ?? "").slice(0, 40)}..."`;
    case "AGENT_STATE_CHANGE":
      return `${String(p.old_state ?? "?")} → ${String(p.new_state ?? "?")}`;
    case "TOOL_CALL":
      return String(p.tool_name ?? "unknown tool");
    case "TOOL_RESULT":
      return `${String(p.tool_name ?? "tool")} → ${p.success ? "ok" : "fail"}`;
    case "FILE_CHANGE":
      return `${String(p.action ?? "?")} ${String(p.filepath ?? "")}`;
    case "PLAN_UPDATE":
      return `${String(p.plan_step ?? "")} [${String(p.status ?? "")}]`;
    case "ANALYST_FINDING":
      return `[${String(p.severity ?? "?")}] ${String(p.description ?? "").slice(0, 60)}`;
    case "ANALYST_STATE_CHANGE":
      return `${String(p.old_state ?? "?")} → ${String(p.new_state ?? "?")}`;
    case "REVIEW_FINDING":
      return `[${String(p.category ?? "?")}] ${String(p.description ?? "").slice(0, 60)}`;
    case "SANDBOX_UPDATE":
      return String(p.display_type ?? "update");
    case "ERROR":
      return String(p.message ?? "Unknown error").slice(0, 80);
    default:
      return JSON.stringify(p).slice(0, 60);
  }
}

export function NotificationFeed() {
  const notifications = useSwarmStore((s) => s.notifications);
  const agentFilter = useSwarmStore((s) => s.agentFilter);
  const eventTypeFilter = useSwarmStore((s) => s.eventTypeFilter);
  const setAgentFilter = useSwarmStore((s) => s.setAgentFilter);
  const setEventTypeFilter = useSwarmStore((s) => s.setEventTypeFilter);
  const filteredNotifications = useSwarmStore((s) => s.filteredNotifications);

  const filtered = useMemo(() => {
    const items = filteredNotifications();
    // Reverse chronological, skip TOKEN_STREAM by default to avoid noise
    return items
      .filter((e) => eventTypeFilter !== null || e.event_type !== "TOKEN_STREAM")
      .slice(-100)
      .reverse();
  }, [filteredNotifications, eventTypeFilter]);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-orange-500" />
            <CardTitle className="text-sm">
              Events{" "}
              <span className="text-muted-foreground font-normal">
                ({notifications.length})
              </span>
            </CardTitle>
          </div>
          <div className="flex gap-2">
            <Select
              value={agentFilter ?? "all"}
              onValueChange={(v) =>
                setAgentFilter(v === "all" ? null : (v as SwarmAgentId))
              }
            >
              <SelectTrigger className="h-7 w-[140px] text-xs">
                <SelectValue placeholder="All agents" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All agents</SelectItem>
                {AGENT_IDS.map((id) => (
                  <SelectItem key={id} value={id}>
                    {id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={eventTypeFilter ?? "all"}
              onValueChange={(v) =>
                setEventTypeFilter(v === "all" ? null : (v as SwarmEventType))
              }
            >
              <SelectTrigger className="h-7 w-[180px] text-xs">
                <SelectValue placeholder="All events" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All events</SelectItem>
                {EVENT_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0">
        <ScrollArea className="h-full">
          <div className="px-4 pb-4 space-y-1">
            {filtered.length === 0 ? (
              <p className="text-muted-foreground text-sm py-2">
                No events yet
              </p>
            ) : (
              filtered.map((event) => (
                <div
                  key={event.event_id}
                  className="flex items-start gap-2 text-xs py-1 border-b border-border/50 last:border-0"
                >
                  <span className="text-muted-foreground shrink-0 w-16 pt-0.5">
                    {formatTime(event.timestamp)}
                  </span>
                  <span
                    className={`shrink-0 inline-flex h-4 items-center rounded px-1.5 text-[10px] text-white ${
                      agentColors[event.agent_id]
                    }`}
                  >
                    {event.agent_id.replace("_", " ")}
                  </span>
                  <span
                    className={`shrink-0 font-medium ${eventColors[event.event_type]}`}
                  >
                    {event.event_type}
                  </span>
                  <span className="text-muted-foreground truncate">
                    {summarizePayload(event)}
                  </span>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
