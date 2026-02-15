"use client";

import { useRef, useEffect } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { ThinkingBlock } from "./thinking-block";
import { ToolCallBlock } from "./tool-call-block";
import { ChatInput } from "./chat-input";
import { ProviderSelector } from "./provider-selector";
import { useAgentChat } from "@/hooks/use-agent-chat";
import type { ContentPart } from "@/types/agent";

interface ContentPartRendererProps {
  part: ContentPart;
  isLastTextPart: boolean;
  messageIsStreaming: boolean;
}

function ContentPartRenderer({ part, isLastTextPart, messageIsStreaming }: ContentPartRendererProps) {
  switch (part.type) {
    case "thinking":
      return (
        <ThinkingBlock
          id={part.id}
          content={part.content}
          isStreaming={part.isStreaming}
        />
      );
    case "tool_call":
      return (
        <ToolCallBlock
          id={part.id}
          toolName={part.name}
          toolInput={part.args}
          toolOutput={part.result ?? null}
          status={part.status}
          startedAt={part.startedAt}
          completedAt={part.completedAt}
        />
      );
    case "text":
      if (!part.content) return null;
      return (
        <MessageBubble
          role="assistant"
          content={part.content}
          isStreaming={isLastTextPart && messageIsStreaming}
        />
      );
    case "notifier":
      // Minimal inline notifier — will be replaced by a dedicated component in a later step
      return (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground py-0.5 px-2">
          <span className="text-[10px] opacity-60">{part.label}</span>
        </div>
      );
    default:
      return null;
  }
}

export function ChatInterface() {
  const {
    messages,
    isLoading,
    provider,
    model,
    sendMessage,
    setProvider,
    setModel,
    clearMessages,
  } = useAgentChat();

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <ProviderSelector
          provider={provider}
          model={model}
          onProviderChange={setProvider}
          onModelChange={setModel}
        />
        <Button variant="ghost" size="sm" onClick={clearMessages} className="text-muted-foreground">
          <Trash2 className="h-4 w-4 mr-1" />
          Clear
        </Button>
      </div>

      <ScrollArea className="flex-1 px-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-center py-20">
            <div>
              <p className="text-lg font-medium">OmniMind Agent</p>
              <p className="text-sm mt-1">Ask me anything about your notes</p>
            </div>
          </div>
        ) : (
          <div className="py-4">
            {messages.map((msg) => (
              <div key={msg.id}>
                {msg.role === "user" ? (
                  <MessageBubble
                    role="user"
                    content={msg.content}
                    isStreaming={false}
                  />
                ) : msg.contentParts.length > 0 ? (
                  // Render ordered content parts chronologically
                  <>
                    {msg.contentParts.map((part, idx) => {
                      // Determine if this is the last text part in the array
                      const isLastTextPart =
                        part.type === "text" &&
                        msg.contentParts.findLastIndex((p) => p.type === "text") === idx;
                      return (
                        <ContentPartRenderer
                          key={part.id}
                          part={part}
                          isLastTextPart={isLastTextPart}
                          messageIsStreaming={msg.isStreaming}
                        />
                      );
                    })}
                    {/* Show streaming cursor when assistant is streaming but has no text part yet */}
                    {msg.isStreaming && !msg.contentParts.some((p) => p.type === "text") && (
                      <MessageBubble
                        role="assistant"
                        content=""
                        isStreaming={true}
                      />
                    )}
                  </>
                ) : (
                  // Fallback: legacy render for messages without contentParts
                  <>
                    {msg.thoughts && (
                      <ThinkingBlock
                        id={`${msg.id}-thoughts`}
                        content={msg.thoughts}
                        isStreaming={msg.isStreaming}
                      />
                    )}
                    {msg.toolCalls.map((tc, i) => (
                      <ToolCallBlock
                        key={`${msg.id}-tool-${i}`}
                        id={`${msg.id}-tool-${i}`}
                        toolName={tc.name}
                        toolInput={tc.args}
                        toolOutput={tc.result ?? null}
                        status={tc.result ? "success" : "running"}
                        startedAt={new Date().toISOString()}
                      />
                    ))}
                    <MessageBubble
                      role="assistant"
                      content={msg.content}
                      isStreaming={msg.isStreaming}
                    />
                  </>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
