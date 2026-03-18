"""Research-domain worker schemas."""

from .browser_tasks import (
    BrowserTaskPayload,
    PageScrapingPayload,
    WebSearchPayload,
    build_page_scraping_envelope,
    build_web_search_envelope,
)
from .content_tasks import (
    ContentSynthesisPayload,
    build_content_synthesis_envelope,
)

__all__ = [
    "BrowserTaskPayload",
    "ContentSynthesisPayload",
    "PageScrapingPayload",
    "WebSearchPayload",
    "build_content_synthesis_envelope",
    "build_page_scraping_envelope",
    "build_web_search_envelope",
]
