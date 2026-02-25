"use client";

import { Eye, Shield, AlertTriangle, AlertOctagon, type LucideProps } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useSwarmStore } from "@/stores/swarm-store";
import type { AnalystAlertLevel } from "@/types/swarm";

type LucideIcon = React.FC<LucideProps>;

const alertConfig: Record<
  AnalystAlertLevel,
  { label: string; color: string; bgColor: string; icon: LucideIcon }
> = {
  IDLE: { label: "Idle", color: "text-muted-foreground", bgColor: "bg-muted", icon: Eye },
  MONITORING: { label: "Monitoring", color: "text-green-500", bgColor: "bg-green-500/10", icon: Shield },
  ALERT_LEVE: { label: "Low Alert", color: "text-green-400", bgColor: "bg-green-400/10", icon: Shield },
  ALERT_MODERADO: {
    label: "Moderate",
    color: "text-yellow-500",
    bgColor: "bg-yellow-500/10",
    icon: AlertTriangle,
  },
  ALERT_CRITICO: {
    label: "Critical",
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    icon: AlertOctagon,
  },
};

function QualityBar({ label, value }: { label: string; value: number }) {
  const filled = Math.round((value / 10) * 10);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 text-muted-foreground">{label}</span>
      <div className="flex-1 flex gap-0.5">
        {Array.from({ length: 10 }, (_, i) => (
          <div
            key={i}
            className={`h-2 flex-1 rounded-sm ${
              i < filled ? "bg-primary" : "bg-muted"
            }`}
          />
        ))}
      </div>
      <span className="w-6 text-right text-muted-foreground">{value}</span>
    </div>
  );
}

export function AnalystPanel() {
  const analystState = useSwarmStore((s) => s.analystState);
  const analystReport = useSwarmStore((s) => s.analystReport);
  const taskStatus = useSwarmStore((s) => s.taskStatus);

  const config = alertConfig[analystState];
  const Icon = config.icon;

  const isActive =
    taskStatus === "coding" ||
    taskStatus === "planning" ||
    taskStatus === "reviewing";

  // Parse quality scores from analyst report if available
  const scores = parseQualityScores(analystReport);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Eye className="h-4 w-4 text-purple-500" />
            <CardTitle className="text-sm">Live Analyst</CardTitle>
          </div>
          <Badge
            variant="outline"
            className={`text-xs ${config.color} border-current`}
          >
            <Icon className="h-3 w-3 mr-1" />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0">
        <ScrollArea className="h-full">
          <div className="px-4 pb-4 space-y-3">
            {scores && (
              <div className="space-y-1.5 rounded-md border p-3">
                <p className="text-xs font-medium mb-2">Quality Scores</p>
                <QualityBar label="Code Quality" value={scores.codeQuality} />
                <QualityBar label="Security" value={scores.security} />
                <QualityBar label="Performance" value={scores.performance} />
                <QualityBar label="Maintainability" value={scores.maintainability} />
                <QualityBar label="Test Coverage" value={scores.testCoverage} />
              </div>
            )}
            {analystReport ? (
              <pre className="text-xs whitespace-pre-wrap break-words font-mono leading-relaxed">
                {analystReport}
              </pre>
            ) : isActive ? (
              <p className="text-muted-foreground text-sm py-2">
                Stealth monitoring in progress...
              </p>
            ) : (
              <p className="text-muted-foreground text-sm py-2">
                Waiting for coder activity...
              </p>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function parseQualityScores(report: string) {
  if (!report) return null;

  const extract = (label: string): number => {
    const regex = new RegExp(`${label}:\\s*\\[?(\\d+)`, "i");
    const match = report.match(regex);
    return match ? Math.min(10, Math.max(0, parseInt(match[1], 10))) : 0;
  };

  const codeQuality = extract("Code Quality");
  const security = extract("Security");
  const performance = extract("Performance");
  const maintainability = extract("Maintainability");
  const testCoverage = extract("Test Coverage");

  if (
    codeQuality === 0 &&
    security === 0 &&
    performance === 0 &&
    maintainability === 0 &&
    testCoverage === 0
  ) {
    return null;
  }

  return { codeQuality, security, performance, maintainability, testCoverage };
}
