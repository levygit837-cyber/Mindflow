import httpx

from omnimind_backend.infra.config import get_settings


async def search_web(query: str) -> str:
    settings = get_settings()
    url = f"{settings.searxng_url}/search"
    params = {"q": query, "format": "json"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - network execution path
        return f"Web search unavailable: {exc}"

    results = payload.get("results", [])
    if not results:
        suggestions = payload.get("suggestions", [])
        if suggestions:
            return "No results found. Suggestions: " + ", ".join(suggestions)
        return "No results found."

    top = results[:10]
    formatted: list[str] = []
    for idx, item in enumerate(top, start=1):
        title = item.get("title") or "Untitled"
        source_url = item.get("url") or ""
        snippet = item.get("content") or ""
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."
        formatted.append(f"{idx}. **{title}**\\n   URL: {source_url}\\n   {snippet}")
    return "\\n\\n".join(formatted)
