"""
Web tools for MindFlow backend.
"""

from __future__ import annotations

import re
import urllib.parse
from html.parser import HTMLParser
from typing import Any

from mindflow_backend.schemas.tools.web_schemas import WEB_SCRAPER_SCHEMA

from ..base.tool_interface import AsyncToolInterface
from .api_client import ApiClientTool
from .http_client import HttpClientTool


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_simple_selector(selector: str) -> tuple[str, str | None]:
    if "." in selector:
        tag, class_name = selector.split(".", 1)
        return tag, class_name
    return selector, None


class _FallbackWebParser(HTMLParser):
    def __init__(self, selectors: list[str]):
        super().__init__()
        self._selector_specs = {
            selector: _parse_simple_selector(selector) for selector in selectors
        }
        self._stack: list[dict[str, Any]] = []
        self._ignored_depth = 0
        self.title = ""
        self.content_parts: list[str] = []
        self.extracted_data: dict[str, list[dict[str, Any]]] = {
            selector: [] for selector in selectors
        }
        self.links: list[dict[str, Any]] = []
        self.images: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        node = {
            "tag": tag,
            "attrs": attr_map,
            "text_parts": [],
            "start_tag": self.get_starttag_text() or f"<{tag}>",
        }
        self._stack.append(node)

        if tag in {"script", "style"}:
            self._ignored_depth += 1

        if tag == "img":
            self.images.append(
                {
                    "url": attr_map.get("src", ""),
                    "alt": attr_map.get("alt", ""),
                    "title": attr_map.get("title", ""),
                    "width": attr_map.get("width"),
                    "height": attr_map.get("height"),
                }
            )

    def handle_data(self, data: str) -> None:
        if not data:
            return

        for node in self._stack:
            node["text_parts"].append(data)

        if self._ignored_depth == 0:
            normalized = _collapse_whitespace(data)
            if normalized:
                self.content_parts.append(normalized)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth > 0:
            self._ignored_depth -= 1

        while self._stack:
            node = self._stack.pop()
            self._finalize_node(node)
            if node["tag"] == tag:
                break

    def _finalize_node(self, node: dict[str, Any]) -> None:
        text = _collapse_whitespace(" ".join(node["text_parts"]))
        tag = node["tag"]
        attrs = node["attrs"]

        if tag == "title" and text and not self.title:
            self.title = text

        if tag == "a" and attrs.get("href"):
            self.links.append(
                {
                    "url": attrs["href"],
                    "text": text,
                    "title": attrs.get("title", ""),
                    "target": attrs.get("target", ""),
                }
            )

        class_names = set(attrs.get("class", "").split())
        for selector, (selector_tag, selector_class) in self._selector_specs.items():
            if selector_tag != tag:
                continue
            if selector_class and selector_class not in class_names:
                continue
            self.extracted_data[selector].append(
                {
                    "text": text,
                    "html": f"{node['start_tag']}{text}</{tag}>",
                    "attributes": attrs,
                }
            )


class WebScraperTool(AsyncToolInterface):
    """
    Web scraping tool.
    """

    def __init__(self, backend: Any | None = None):
        super().__init__()
        self.backend = backend
        self.name = "web_scraper"
        self.description = "Web scraping with CSS selectors and extraction"

        try:
            from bs4 import BeautifulSoup

            self.BEAUTIFULSOUP_AVAILABLE = True
            self.BeautifulSoup = BeautifulSoup
        except ImportError:
            self.BEAUTIFULSOUP_AVAILABLE = False
            self.BeautifulSoup = None

        self._schema = WEB_SCRAPER_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Scrape web page content.
        """
        try:
            url = kwargs["url"]
            selectors = kwargs.get("selectors", [])
            headers = kwargs.get("headers", {})
            timeout = kwargs.get("timeout", 30)
            extract_links = kwargs.get("extract_links", False)
            extract_images = kwargs.get("extract_images", False)
            extract_text = kwargs.get("extract_text", True)

            response = await HttpClientTool(backend=self.backend).execute(
                method="GET",
                url=url,
                headers=headers,
                timeout=timeout,
            )
            if not response["success"]:
                return response

            html = response["result"]["body"]
            result = {
                "url": url,
                "title": "",
                "extracted_data": {},
                "links": [],
                "images": [],
                "metadata": {
                    "content_type": response["result"]["content_type"],
                    "content_length": response["result"]["content_length"],
                    "status_code": response["result"]["status_code"],
                },
            }

            if self.BEAUTIFULSOUP_AVAILABLE:
                soup = self.BeautifulSoup(html, "html.parser")
                result["title"] = soup.title.string if soup.title else ""

                if extract_text:
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text = soup.get_text(separator=" ", strip=True)
                    if len(text) > 50000:
                        text = text[:50000] + "\n... Text truncated due to size limit."
                    result["content"] = text

                for selector in selectors:
                    elements = soup.select(selector)
                    extracted = []
                    for element in elements:
                        extracted.append(
                            {
                                "text": element.get_text(strip=True),
                                "html": str(element),
                                "attributes": dict(element.attrs),
                            }
                        )
                    result["extracted_data"][selector] = extracted

                if extract_links:
                    links = []
                    for link in soup.find_all("a", href=True):
                        href = urllib.parse.urljoin(url, link["href"])
                        links.append(
                            {
                                "url": href,
                                "text": link.get_text(strip=True),
                                "title": link.get("title", ""),
                                "target": link.get("target", ""),
                            }
                        )
                    result["links"] = links
                    result["links_count"] = len(links)

                if extract_images:
                    images = []
                    for img in soup.find_all("img", src=True):
                        src = urllib.parse.urljoin(url, img["src"])
                        images.append(
                            {
                                "url": src,
                                "alt": img.get("alt", ""),
                                "title": img.get("title", ""),
                                "width": img.get("width"),
                                "height": img.get("height"),
                            }
                        )
                    result["images"] = images
                    result["images_count"] = len(images)
            else:
                fallback = _FallbackWebParser(selectors)
                fallback.feed(html)
                result["title"] = fallback.title
                result["extracted_data"] = fallback.extracted_data

                if extract_text:
                    text = _collapse_whitespace(" ".join(fallback.content_parts))
                    if len(text) > 50000:
                        text = text[:50000] + "\n... Text truncated due to size limit."
                    result["content"] = text

                if extract_links:
                    links = []
                    for link in fallback.links:
                        links.append(
                            {
                                **link,
                                "url": urllib.parse.urljoin(url, link["url"]),
                            }
                        )
                    result["links"] = links
                    result["links_count"] = len(links)

                if extract_images:
                    images = []
                    for image in fallback.images:
                        images.append(
                            {
                                **image,
                                "url": urllib.parse.urljoin(url, image["url"]),
                            }
                        )
                    result["images"] = images
                    result["images_count"] = len(images)

            return self._format_result(success=True, result=result)
        except Exception as exc:
            return self._format_result(
                success=False,
                error=f"Web scraping failed: {str(exc)}",
            )

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()


__all__ = ["HttpClientTool", "WebScraperTool", "ApiClientTool"]
