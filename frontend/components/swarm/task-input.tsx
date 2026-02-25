"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@frontend/components/ui/button";
import { Textarea } from "@frontend/components/ui/textarea";
import { Input } from "@frontend/components/ui/input";
import { useSwarmStore } from "@frontend/stores/swarm.store";
import { ProviderSelector } from "@frontend/components/agent/provider-selector";

export function TaskInput() {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const taskStatus = useSwarmStore((s) => s.taskStatus);
  const taskId = useSwarmStore((s) => s.taskId);
  const submitTask = useSwarmStore((s) => s.submitTask);
  const setTaskId = useSwarmStore((s) => s.setTaskId);
  const clearState = useSwarmStore((s) => s.clearState);
  const provider = useSwarmStore((s) => s.provider);
  const model = useSwarmStore((s) => s.model);
  const setProvider = useSwarmStore((s) => s.setProvider);
  const setModel = useSwarmStore((s) => s.setModel);
  const workingPath = useSwarmStore((s) => s.workingPath);
  const setWorkingPath = useSwarmStore((s) => s.setWorkingPath);

  const isRunning =
    taskId !== null &&
    taskStatus !== "complete" &&
    taskStatus !== "error";

  const handleSubmit = async () => {
    const trimmed = value.trim();
    if (!trimmed || isRunning) return;

    clearState();
    const newTaskId = await submitTask(trimmed, provider, model, workingPath.trim() || undefined);
    if (newTaskId) {
      setTaskId(newTaskId);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <ProviderSelector
          provider={provider}
          model={model}
          onProviderChange={setProvider}
          onModelChange={setModel}
        />
        <Input
          value={workingPath}
          onChange={(e) => setWorkingPath(e.target.value)}
          placeholder="Path de trabalho (ex: docs/ ou src/)"
          className="h-8 text-xs sm:max-w-[280px]"
          disabled={isRunning}
        />
      </div>
      <div className="flex items-end gap-2">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe the task for the swarm agents..."
          className="min-h-10 max-h-52 resize-none"
          rows={1}
          disabled={isRunning}
        />
        <Button
          onClick={handleSubmit}
          disabled={isRunning || !value.trim()}
          size="icon"
        >
          {isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
