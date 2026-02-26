"use client";

import Link from "next/link";
import { Bot, Settings } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@client/components/ui/card";

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">OmniMind</h2>
        <p className="text-muted-foreground mt-1">
          Your personal Deep Agent powered by Vertex AI
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link href="/agent">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10 text-green-500">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Deep Agent</CardTitle>
                  <CardDescription>Chat with OmniMind</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/settings">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                  <Settings className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Settings</CardTitle>
                  <CardDescription>Configure provider & model</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}
