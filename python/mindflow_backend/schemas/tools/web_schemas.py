"""Web tool schemas for MindFlow agents.

Provides standardized schemas for web-related tools including
HTTP clients, API interactions, web scraping, and browser automation.
"""

from __future__ import annotations

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema

# API Client Tool Schema
API_CLIENT_SCHEMA = ToolSchema(
    name="api_client",
    description="REST API client with authentication and retry logic",
    category="web",
    parameters=[
        ToolParameter(
            name="api_url",
            type="string",
            description="Base API URL",
            required=True
        ),
        ToolParameter(
            name="endpoint",
            type="string",
            description="API endpoint",
            required=True
        ),
        ToolParameter(
            name="method",
            type="string",
            description="HTTP method",
            required=False,
            default="GET"
        ),
        ToolParameter(
            name="headers",
            type="object",
            description="API headers",
            required=False,
            default={}
        ),
        ToolParameter(
            name="auth_type",
            type="string",
            description="Authentication type (bearer, basic, api_key)",
            required=False
        ),
        ToolParameter(
            name="auth_token",
            type="string",
            description="Authentication token",
            required=False
        ),
        ToolParameter(
            name="username",
            type="string",
            description="Username for basic auth",
            required=False
        ),
        ToolParameter(
            name="password",
            type="string",
            description="Password for basic auth",
            required=False
        ),
        ToolParameter(
            name="api_key_header",
            type="string",
            description="API key header name",
            required=False,
            default="X-API-Key"
        ),
        ToolParameter(
            name="data",
            type="object",
            description="Request data",
            required=False
        ),
        ToolParameter(
            name="params",
            type="object",
            description="Query parameters",
            required=False,
            default={}
        )
    ],
    returns={
        "type": "object",
        "description": "API response",
        "properties": {
            "status_code": {"type": "integer", "description": "HTTP status code"},
            "data": {"type": "object", "description": "Response data"},
            "headers": {"type": "object", "description": "Response headers"},
            "success": {"type": "boolean", "description": "Request success"}
        }
    }
)


# HTTP Client Tool Schema
HTTP_CLIENT_SCHEMA = ToolSchema(
    name="http_client",
    description="HTTP client for web requests",
    category="web",
    parameters=[
        ToolParameter(
            name="method",
            type="string",
            description="HTTP method (GET, POST, PUT, DELETE, PATCH)",
            required=True
        ),
        ToolParameter(
            name="url",
            type="string",
            description="Target URL",
            required=True
        ),
        ToolParameter(
            name="headers",
            type="object",
            description="HTTP headers",
            required=False,
            default={}
        ),
        ToolParameter(
            name="params",
            type="object",
            description="Query parameters",
            required=False,
            default={}
        ),
        ToolParameter(
            name="data",
            type="object",
            description="Request body data (JSON)",
            required=False
        ),
        ToolParameter(
            name="form_data",
            type="object",
            description="Form data",
            required=False
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Request timeout in seconds",
            required=False,
            default=30
        ),
        ToolParameter(
            name="verify_ssl",
            type="boolean",
            description="Verify SSL certificates",
            required=False,
            default=True
        ),
        ToolParameter(
            name="follow_redirects",
            type="boolean",
            description="Follow HTTP redirects",
            required=False,
            default=True
        ),
        ToolParameter(
            name="max_redirects",
            type="integer",
            description="Maximum redirects to follow",
            required=False,
            default=5
        )
    ],
    returns={
        "type": "object",
        "description": "HTTP response data",
        "properties": {
            "status_code": {"type": "integer", "description": "HTTP status code"},
            "headers": {"type": "object", "description": "Response headers"},
            "body": {"type": "string", "description": "Response body"},
            "url": {"type": "string", "description": "Final URL after redirects"},
            "elapsed": {"type": "float", "description": "Request time in seconds"},
            "content_type": {"type": "string", "description": "Response content type"},
            "content_length": {"type": "integer", "description": "Response content length"}
        }
    }
)


# Web Scraper Tool Schema
WEB_SCRAPER_SCHEMA = ToolSchema(
    name="web_scraper",
    description="Web scraping with CSS selectors and extraction",
    category="web",
    parameters=[
        ToolParameter(
            name="url",
            type="string",
            description="URL to scrape",
            required=True
        ),
        ToolParameter(
            name="selectors",
            type="array",
            description="CSS selectors to extract",
            required=False,
            default=[]
        ),
        ToolParameter(
            name="headers",
            type="object",
            description="HTTP headers",
            required=False,
            default={}
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Request timeout in seconds",
            required=False,
            default=30
        ),
        ToolParameter(
            name="wait_for_selector",
            type="string",
            description="CSS selector to wait for (JavaScript sites)",
            required=False
        ),
        ToolParameter(
            name="extract_links",
            type="boolean",
            description="Extract all links from page",
            required=False,
            default=False
        ),
        ToolParameter(
            name="extract_images",
            type="boolean",
            description="Extract all images from page",
            required=False,
            default=False
        ),
        ToolParameter(
            name="extract_text",
            type="boolean",
            description="Extract clean text content",
            required=False,
            default=True
        )
    ],
    returns={
        "type": "object",
        "description": "Scraped content",
        "properties": {
            "title": {"type": "string", "description": "Page title"},
            "content": {"type": "string", "description": "Clean text content"},
            "extracted_data": {"type": "object", "description": "Extracted data by selectors"},
            "links": {"type": "array", "description": "Extracted links"},
            "images": {"type": "array", "description": "Extracted images"},
            "metadata": {"type": "object", "description": "Page metadata"}
        }
    }
)


# Browser Search Tool Schema
BROWSER_SEARCH_SCHEMA = ToolSchema(
    name="browser_search",
    description="Browser-based web research tool",
    category="web",
    parameters=[
        ToolParameter(
            name="query_plan",
            type="object",
            description="Research query plan with multiple queries and browser configuration",
            required=True
        ),
        ToolParameter(
            name="max_concurrent_browsers",
            type="integer",
            description="Maximum number of concurrent browser instances",
            required=False,
            default=5
        ),
        ToolParameter(
            name="session_id",
            type="string",
            description="Research session identifier",
            required=False
        ),
        ToolParameter(
            name="agent_id",
            type="string",
            description="Agent performing the search",
            required=False
        )
    ],
    returns={
        "type": "object",
        "description": "Browser research results",
        "properties": {
            "session_id": {"type": "string", "description": "Research session ID"},
            "agent_id": {"type": "string", "description": "Agent ID"},
            "original_query": {"type": "string", "description": "Original search query"},
            "findings": {"type": "array", "description": "Research findings with source classification"},
            "synthesis": {"type": "string", "description": "Synthesized summary of findings"},
            "browsers_used": {"type": "integer", "description": "Number of browsers used"},
            "successful_searches": {"type": "integer", "description": "Number of successful searches"},
            "total_time": {"type": "float", "description": "Total research time"},
            "completed_at": {"type": "string", "description": "Research completion timestamp"}
        }
    }
)


# Dictionary of all web tool schemas
WEB_SCHEMAS = {
    "api_client": API_CLIENT_SCHEMA,
    "http_client": HTTP_CLIENT_SCHEMA,
    "web_scraper": WEB_SCRAPER_SCHEMA,
    "browser_search": BROWSER_SEARCH_SCHEMA
}


# Export schemas for easy import
__all__ = [
    "API_CLIENT_SCHEMA",
    "HTTP_CLIENT_SCHEMA", 
    "WEB_SCRAPER_SCHEMA",
    "BROWSER_SEARCH_SCHEMA",
    "WEB_SCHEMAS"
]
