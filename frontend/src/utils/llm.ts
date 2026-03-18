import type { LlmProvider } from '../types';

export const DEFAULT_PROVIDER: LlmProvider = 'google';

export const PROVIDER_MODELS: Record<LlmProvider, string[]> = {
  google: [
    'gemini-3.1-flash-preview',
    'gemini-3.1-flash-lite-preview',
    'gemini-3.1-pro-preview',
    'gemini-2.0-flash',
    'gemini-2.0-pro',
  ],
  openai: ['gpt-4o', 'gpt-4o-mini', 'o3-mini'],
  anthropic: ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-haiku-4-5'],
  ollama: ['llama3.2', 'mistral', 'qwen2.5'],
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
