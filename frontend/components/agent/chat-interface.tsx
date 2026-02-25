"use client";

import { useRef, useEffect } from "react";
import { Trash2, Bot } from "lucide-react";
import { Button } from "@frontend/components/ui/button";
import { ScrollArea } from "@frontend/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { ThinkingBlock } from "./thinking-block";
import { ToolCallBlock } from "./tool-call-block";
import { ResponseBlock } from "./response-block";
import { AgentStepsBlock } from "./agent-steps-block";
import { ChatInput } from "./chat-input";
import { ProviderSelector } from "./provider-selector";
import { useAgentChat } from "@frontend/hooks/use-agent-chat";
import type { ContentPart } from "@shared/types/agent";

/* ------------------------------------------------------------------ */
/*  Content Part Renderer                                              */
/* ------------------------------------------------------------------ */
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
        <ResponseBlock
          content={part.content}
          isStreaming={isLastTextPart && messageIsStreaming}
        />
      );
    case "notifier":
      return (
        <div className="py-0.5">
          <span className="text-[10px] text-zinc-700 font-mono">
            {part.label}
          </span>
        </div>
      );
    case "agent_step":
      return (
        <AgentStepsBlock
          id={part.id}
          stepName={part.stepName}
          detail={part.detail}
          status={part.status}
          subSteps={part.subSteps}
          startedAt={part.startedAt}
          completedAt={part.completedAt}
        />
      );
    default:
      return null;
  }
}

/* ------------------------------------------------------------------ */
/*  Chat Interface                                                     */
/* ------------------------------------------------------------------ */
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
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] backdrop-blur-sm bg-white/[0.02]">
        <ProviderSelector
          provider={provider}
          model={model}
          onProviderChange={setProvider}
          onModelChange={setModel}
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={clearMessages}
          className="text-muted-foreground/60 hover:text-foreground/80 hover:bg-white/[0.05]"
        >
          <Trash2 className="h-4 w-4 mr-1" />
          Clear
        </Button>
      </div>

      {/* Messages area */}
      <ScrollArea className="flex-1 px-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-center py-20">
            <div className="space-y-2">
              <div className="flex items-center justify-center">
                <div className="h-10 w-10 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                  <Bot className="h-5 w-5 text-zinc-500" />
                </div>
              </div>
              <p className="text-sm font-medium text-zinc-400">OmniMind Agent</p>
              <p className="text-xs text-zinc-600">Ask me anything</p>
            </div>
          </div>
        ) : (
          <div className="py-2 space-y-0">
            {messages.map((msg) => (
              <div key={msg.id}>
                {msg.role === "user" ? (
                  <MessageBubble
                    role="user"
                    content={msg.content}
                    isStreaming={false}
                  />
                ) : msg.contentParts.length > 0 ? (
                  <div data-testid="assistant-message" className="max-w-3xl">
                    {msg.contentParts.map((part, idx) => {
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
                  </div>
                ) : (
                  // Legacy fallback for messages without contentParts
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
                    {msg.content && (
                      <ResponseBlock
                        content={msg.content}
                        isStreaming={msg.isStreaming}
                      />
                    )}
                  </>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
