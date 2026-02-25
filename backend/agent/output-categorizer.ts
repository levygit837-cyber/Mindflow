import type { OutputCategory } from "@/types/agent";

/**
 * Heuristically categorizes a text response from the LLM.
 * Used to populate meta.category on "response" SSE events.
 *
 * Categories (in priority order):
 *  - "decision"    — agent announces what it is about to do
 *  - "code_result" — response contains a fenced code block
 *  - "summary"     — agent presents a result or summary
 *  - "explanation" — long informative passage without action phrases
 *  - "response"    — generic fallback
 */
export function categorizeOutput(text: string): OutputCategory {
  if (!text || text.trim().length === 0) return "response";

  const trimmed = text.trimStart();

  // Decision: agent announces intent (English & Portuguese)
  if (
    /^(I'll|I will|Let me|I'm going to|I am going to|Vou|Deixa eu|Vou usar)\b/i.test(trimmed)
  ) {
    return "decision";
  }

  // Code result: contains a fenced code block
  if (/```/.test(text)) {
    return "code_result";
  }

  // Summary: agent presents results
  if (
    /^(Here's|Here is|Aqui está|Aqui estão|The result|Os resultados|O resultado|Based on)\b/i.test(
      trimmed
    )
  ) {
    return "summary";
  }

  // Explanation: longer informative text (≥ 80 chars) without action opener
  if (text.trim().length >= 80) {
    return "explanation";
  }

  return "response";
}
