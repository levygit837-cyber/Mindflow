/**
 * System prompt module — Web search tool.
 * Incluído quando o agente usa: search_web
 */
export const WEB_SEARCH_PROMPT = `## Web Search Tool

### search_web (Web Search)
- Search the web for up-to-date information, documentation, APIs, error solutions.
- Returns top 10 results with title, URL, and snippet.
- Use specific, targeted queries: search_web(query="Next.js 16 app router streaming SSE") not just "nextjs".
- Use when you need: current documentation, error messages you don't recognize, package APIs, best practices.
- This is your ONLY source of external information — use it when your knowledge is uncertain or outdated.`;
