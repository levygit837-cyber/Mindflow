"use client";

import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { Button } from "@client/components/ui/button";
import { Textarea } from "@client/components/ui/textarea";
import { cn } from "@client/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  return (
    <div className="p-4 border-t border-white/[0.06]">
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl p-2",
          "backdrop-blur-md bg-white/[0.03] border border-white/[0.08]",
          "transition-all duration-200",
          "focus-within:border-cyan-500/30 focus-within:shadow-[0_0_12px_rgba(6,182,212,0.08)]"
        )}
      >
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask OmniMind anything..."
          className={cn(
            "min-h-10 max-h-52 resize-none border-0 bg-transparent",
            "focus-visible:ring-0 focus-visible:ring-offset-0",
            "placeholder:text-muted-foreground/30",
            "text-foreground/90"
          )}
          rows={1}
          disabled={disabled}
        />
        <Button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          size="icon"
          className={cn(
            "shrink-0 rounded-xl h-9 w-9",
            "bg-cyan-500/20 border border-cyan-500/30 text-cyan-400",
            "hover:bg-cyan-500/30 hover:border-cyan-500/40 hover:shadow-[0_0_12px_rgba(6,182,212,0.15)]",
            "disabled:opacity-30 disabled:hover:bg-cyan-500/20",
            "transition-all duration-200"
          )}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
