"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@client/components/ui/select";
import type { LLMProvider } from "@shared/types/agent";
import { PROVIDER_MODELS } from "@shared/types/settings";

interface ProviderSelectorProps {
  provider: LLMProvider;
  model: string;
  onProviderChange: (provider: LLMProvider) => void;
  onModelChange: (model: string) => void;
}

export function ProviderSelector({
  provider,
  model,
  onProviderChange,
  onModelChange,
}: ProviderSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <Select value={provider} onValueChange={(v) => {
        const p = v as LLMProvider;
        onProviderChange(p);
        onModelChange(PROVIDER_MODELS[p][0]);
      }}>
        <SelectTrigger className="w-[130px] h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="vertexai">Vertex AI</SelectItem>
          <SelectItem value="google">Google (Gemini API)</SelectItem>
          <SelectItem value="anthropic">Anthropic</SelectItem>
          <SelectItem value="openai">OpenAI</SelectItem>
          <SelectItem value="ollama">Ollama</SelectItem>
        </SelectContent>
      </Select>

      <Select value={model} onValueChange={onModelChange}>
        <SelectTrigger className="w-[200px] h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {PROVIDER_MODELS[provider].map((m) => (
            <SelectItem key={m} value={m}>
              {m}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
