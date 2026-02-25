"use client";

import { ClipboardCheck, CheckCircle, AlertCircle, XCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@frontend/components/ui/card";
import { ScrollArea } from "@frontend/components/ui/scroll-area";
import { Badge } from "@frontend/components/ui/badge";
import { useSwarmStore } from "@frontend/stores/swarm.store";

export function ReviewerPanel() {
  const reviewerReport = useSwarmStore((s) => s.reviewerReport);
  const taskStatus = useSwarmStore((s) => s.taskStatus);

  const isReviewing = taskStatus === "reviewing";
  const isComplete = taskStatus === "complete";
  const showPanel = isReviewing || isComplete || !!reviewerReport;

  if (!showPanel) {
    return (
      <Card className="flex flex-col h-full">
        <CardHeader className="py-3 px-4">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="h-4 w-4 text-amber-500" />
            <CardTitle className="text-sm">Code Reviewer</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground text-sm">
            Review starts after coding completes
          </p>
        </CardContent>
      </Card>
    );
  }

  const assessment = parseAssessment(reviewerReport);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="h-4 w-4 text-amber-500" />
            <CardTitle className="text-sm">Code Reviewer</CardTitle>
          </div>
          {assessment && <AssessmentBadge assessment={assessment} />}
          {isReviewing && !reviewerReport && (
            <Badge variant="secondary" className="text-xs">
              <span className="mr-1 h-2 w-2 rounded-full bg-amber-500 animate-pulse inline-block" />
              Reviewing
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0">
        <ScrollArea className="h-full">
          <div className="px-4 pb-4">
            {reviewerReport ? (
              <pre className="text-xs whitespace-pre-wrap break-words font-mono leading-relaxed">
                {reviewerReport}
              </pre>
            ) : (
              <div className="flex items-center gap-2 text-muted-foreground text-sm py-4">
                <span className="animate-pulse">Running code review...</span>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function AssessmentBadge({ assessment }: { assessment: string }) {
  if (assessment === "APPROVED") {
    return (
      <Badge className="text-xs bg-green-600">
        <CheckCircle className="h-3 w-3 mr-1" />
        Approved
      </Badge>
    );
  }
  if (assessment === "APPROVED_WITH_SUGGESTIONS") {
    return (
      <Badge variant="secondary" className="text-xs text-yellow-500 border-yellow-500/30">
        <AlertCircle className="h-3 w-3 mr-1" />
        Suggestions
      </Badge>
    );
  }
  if (assessment === "CHANGES_REQUESTED") {
    return (
      <Badge variant="destructive" className="text-xs">
        <XCircle className="h-3 w-3 mr-1" />
        Changes Requested
      </Badge>
    );
  }
  return null;
}

function parseAssessment(report: string): string | null {
  if (!report) return null;
  if (report.includes("CHANGES_REQUESTED")) return "CHANGES_REQUESTED";
  if (report.includes("APPROVED_WITH_SUGGESTIONS")) return "APPROVED_WITH_SUGGESTIONS";
  if (report.includes("APPROVED")) return "APPROVED";
  return null;
}
