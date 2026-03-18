import type { LlmProvider } from '../types';

export const DEFAULT_PROVIDER: LlmProvider = 'ollama';

export const PROVIDER_MODELS: Record<LlmProvider, string[]> = {
  google: [
    'gemini-3.1-flash-lite-preview',
    'gemini-3.1-pro-preview',
    'gemini-3.1-pro-preview-customtools',
  ],
  openai: ['gpt-4o'],
  anthropic: ['claude-sonnet-4-6', 'claude-opus-4-6'],
  ollama: ['qwen3.5-0.8b', 'llama3.2'],
};

export function isLlmProvider(value: string | null | undefined): value is LlmProvider {
  return typeof value === 'string' && value in PROVIDER_MODELS;
}

export function normalizeProvider(value: string | null | undefined): LlmProvider {
  return isLlmProvider(value) ? value : DEFAULT_PROVIDER;
}

export function getModelsForProvider(provider: LlmProvider): string[] {
  return PROVIDER_MODELS[provider];
}

export function getDefaultModelForProvider(provider: LlmProvider): string {
  return PROVIDER_MODELS[provider][0];
}

export function resolveModelForProvider(
  provider: LlmProvider,
  model: string | null | undefined,
): string {
  const normalizedModel = model?.trim();
  if (normalizedModel && PROVIDER_MODELS[provider].includes(normalizedModel)) {
    return normalizedModel;
  }

  return getDefaultModelForProvider(provider);
}
