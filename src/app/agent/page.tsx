"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { ChatInterface } from "@frontend/components/agent/chat-interface";
import { useAgentStore } from "@frontend/stores/agent.store";

function AgentPageInner() {
  const searchParams = useSearchParams();
  const setNoteContext = useAgentStore((s) => s.setNoteContext);

  useEffect(() => {
    const notes = searchParams.get("notes");
    if (notes) {
      setNoteContext(notes.split(",").filter(Boolean));
    }
  }, [searchParams, setNoteContext]);

  return <ChatInterface />;
}

export default function AgentPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground">Loading...</div>}>
      <AgentPageInner />
    </Suspense>
  );
}
