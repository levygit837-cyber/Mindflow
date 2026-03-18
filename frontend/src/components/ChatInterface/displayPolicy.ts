export interface StreamDisplayOptions {
  showReasoning: boolean;
  enableNotifications: boolean;
}

const HIDDEN_NOTIFIER_PREFIXES = [
  'file_',
  'shell_',
] as const;

const HIDDEN_NOTIFIER_KINDS = new Set([
  'search_done',
  'tool_start',
]);

export function extractNotifierKind(eventData: string): string | null {
  try {
    const payload = JSON.parse(eventData) as {
      kind?: string;
      category?: string;
    } | null;
    const kind = String(payload?.kind ?? payload?.category ?? '').trim().toLowerCase();
    return kind || null;
  } catch {
    return null;
  }
}

export function shouldDisplayNotifierKind(kind: string | null): boolean {
  if (!kind) return false;
  if (HIDDEN_NOTIFIER_KINDS.has(kind)) return false;
  return !HIDDEN_NOTIFIER_PREFIXES.some((prefix) => kind.startsWith(prefix));
}

export function shouldDisplayNotifierEvent(
  eventData: string,
  options: StreamDisplayOptions,
): boolean {
  if (!options.enableNotifications) return false;
  return shouldDisplayNotifierKind(extractNotifierKind(eventData));
}
