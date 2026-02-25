"use client";

import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  if (role !== "user") return null;

  return (
    <div className="flex justify-end py-2 animate-fade-in-up">
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm",
          "bg-zinc-800 border border-zinc-700/50",
          "text-zinc-200"
        )}
      >
        <div className="whitespace-pre-wrap break-words">{content}</div>
      </div>
    </div>
  );
}
