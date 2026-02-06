"use client";

import { useRef, useEffect } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { ThoughtStream } from "./thought-stream";
import { ToolCallDisplay } from "./tool-call-display";
import { ChatInput } from "./chat-input";
import { ProviderSelector } from "./provider-selector";
import { useAgentChat } from "@/hooks/use-agent-chat";

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
                {msg.role === "assistant" && (
                  <>
                    <ThoughtStream thoughts={msg.thoughts} isStreaming={msg.isStreaming} />
                    <ToolCallDisplay toolCalls={msg.toolCalls} />
                  </>
                )}
                <MessageBubble
                  role={msg.role}
                  content={msg.content}
                  isStreaming={msg.isStreaming}
                />
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
