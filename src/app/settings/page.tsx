"use client";

import { useState, useEffect } from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AppSettings } from "@/types/settings";
import { DEFAULT_SETTINGS, PROVIDER_MODELS } from "@/types/settings";
import type { LLMProvider } from "@/types/agent";

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then(setSettings)
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const update = (key: keyof AppSettings, value: string) => {
    setSettings((s) => ({ ...s, [key]: value }));
  };

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Default LLM Provider</CardTitle>
          <CardDescription>Choose your default AI model provider</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={settings.defaultProvider}
              onValueChange={(v) => {
                update("defaultProvider", v);
                update("defaultModel", PROVIDER_MODELS[v as LLMProvider][0]);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
                <SelectItem value="openai">OpenAI (GPT)</SelectItem>
                <SelectItem value="google">Google (Gemini)</SelectItem>
                <SelectItem value="ollama">Ollama (Local)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Model</Label>
            <Select
              value={settings.defaultModel}
              onValueChange={(v) => update("defaultModel", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDER_MODELS[settings.defaultProvider as LLMProvider]?.map((m) => (
                  <SelectItem key={m} value={m}>{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>
            Enter API keys for each provider. Keys are stored locally.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Anthropic API Key</Label>
            <Input
              type="password"
              value={settings.anthropicApiKey}
              onChange={(e) => update("anthropicApiKey", e.target.value)}
              placeholder="sk-ant-..."
            />
          </div>

          <div className="space-y-2">
            <Label>OpenAI API Key</Label>
            <Input
              type="password"
              value={settings.openaiApiKey}
              onChange={(e) => update("openaiApiKey", e.target.value)}
              placeholder="sk-..."
            />
          </div>

          <div className="space-y-2">
            <Label>Google API Key</Label>
            <Input
              type="password"
              value={settings.googleApiKey}
              onChange={(e) => update("googleApiKey", e.target.value)}
              placeholder="AI..."
            />
          </div>

          <div className="space-y-2">
            <Label>Ollama Base URL</Label>
            <Input
              value={settings.ollamaBaseUrl}
              onChange={(e) => update("ollamaBaseUrl", e.target.value)}
              placeholder="http://localhost:11434"
            />
          </div>
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving}>
        <Save className="h-4 w-4 mr-2" />
        {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
      </Button>
    </div>
  );
}
