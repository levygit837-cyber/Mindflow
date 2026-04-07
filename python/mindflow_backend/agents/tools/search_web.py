"""Web search functionality for agents.

This module provides search capabilities that can be used by agents
to research and gather information from the web.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Perform web search for the given query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing search results with metadata
    """
    try:
        _logger.info("web_search_initiated", query=query, max_results=max_results)
        
        # Try to use LightPanda browser search tool if available
        try:
            from mindflow_backend.agents.tools.web.lightpanda_browser_search import (
                get_lightpanda_browser_search_tool,
            )
            
            tool = get_lightpanda_browser_search_tool()
            
            # Perform web search using LightPanda
            search_results = await tool.search_web(
                query=query,
                max_results=max_results,
            )
            
            _logger.info(
                "web_search_completed_with_lightpanda",
                query=query,
                results_count=len(search_results.get("results", [])),
            )
            
            return search_results
            
        except ImportError:
            _logger.debug("lightpanda_browser_search_not_available")
        except Exception as exc:
            _logger.warning("lightpanda_search_failed", error=str(exc))
        
        # Fallback to simulated search
        await asyncio.sleep(0.1)
        
        result = {
            "query": query,
            "status": "completed",
            "results": [
                {
                    "title": f"Search result for: {query}",
                    "url": "https://example.com",
                    "snippet": f"This is a search result for the query: {query}. For real web search, ensure LightPanda browser is configured.",
                    "relevance_score": 0.8
                }
            ],
            "total_results": 1,
            "search_time": 0.1,
            "note": "Using fallback search. For real results, configure LightPanda browser.",
        }
        
        _logger.info("web_search_completed_fallback", query=query)
        return result
        
    except Exception as e:
        _logger.error("web_search_failed", query=query, error=str(e))
        return {
            "query": query,
            "status": "error",
            "error": str(e),
            "results": [],
            "total_results": 0
        }
