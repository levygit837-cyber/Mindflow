"""Web tool interfaces for MindFlow backend.

Provides contracts for web-related operations including HTTP requests,
API interactions, browser automation, and web scraping with proper
security and rate limiting controls.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WebToolInterface(Protocol):
    """Interface for web-related operations."""
    
    async def fetch_url(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int = 30
    ) -> dict[str, Any]:
        """Fetch URL with HTTP request.
        
        Args:
            url: URL to fetch
            method: HTTP method
            headers: Request headers
            data: Request data
            timeout: Request timeout
            
        Returns:
            Dictionary with response data
        """
        ...


@runtime_checkable
class HttpClientTool(Protocol):
    """Interface for HTTP client operations."""
    
    async def get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        follow_redirects: bool = True
    ) -> dict[str, Any]:
        """Perform HTTP GET request.
        
        Args:
            url: Target URL
            params: Query parameters
            headers: Request headers
            timeout: Request timeout
            follow_redirects: Follow HTTP redirects
            
        Returns:
            Dictionary with response data
        """
        ...
    
    async def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 30
    ) -> dict[str, Any]:
        """Perform HTTP POST request.
        
        Args:
            url: Target URL
            data: Form data
            json: JSON data
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Dictionary with response data
        """
        ...
    
    async def put(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 30
    ) -> dict[str, Any]:
        """Perform HTTP PUT request.
        
        Args:
            url: Target URL
            data: Form data
            json: JSON data
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Dictionary with response data
        """
        ...
    
    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 30
    ) -> dict[str, Any]:
        """Perform HTTP DELETE request.
        
        Args:
            url: Target URL
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Dictionary with response data
        """
        ...


@runtime_checkable
class ApiClientTool(Protocol):
    """Interface for API client operations."""
    
    async def call_api(
        self,
        api_base_url: str,
        endpoint: str,
        method: str = "GET",
        params: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Call REST API endpoint.
        
        Args:
            api_base_url: Base URL of API
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request data
            headers: Request headers
            auth: Authentication credentials
            
        Returns:
            Dictionary with API response
        """
        ...
    
    async def load_openapi_spec(
        self,
        spec_url: str
    ) -> dict[str, Any]:
        """Load OpenAPI specification.
        
        Args:
            spec_url: URL or path to OpenAPI spec
            
        Returns:
            Dictionary with parsed specification
        """
        ...
    
    async def validate_api_response(
        self,
        response: dict[str, Any],
        schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate API response against schema.
        
        Args:
            response: API response
            schema: Response schema
            
        Returns:
            Dictionary with validation result
        """
        ...


@runtime_checkable
class BrowserSearchTool(Protocol):
    """Interface for browser-based search operations."""
    
    async def search_web(
        self,
        query: str,
        search_engine: str = "google",
        num_results: int = 10,
        language: str = "en"
    ) -> dict[str, Any]:
        """Search the web using browser automation.
        
        Args:
            query: Search query
            search_engine: Search engine to use
            num_results: Number of results to return
            language: Search language
            
        Returns:
            Dictionary with search results
        """
        ...
    
    async def scrape_page(
        self,
        url: str,
        selector: str | None = None,
        wait_for: str | None = None,
        screenshot: bool = False
    ) -> dict[str, Any]:
        """Scrape web page content.
        
        Args:
            url: Page URL
            selector: CSS selector for specific content
            wait_for: Element to wait for
            screenshot: Take screenshot
            
        Returns:
            Dictionary with scraped content
        """
        ...
    
    async def fill_form(
        self,
        url: str,
        form_data: dict[str, str],
        submit: bool = True
    ) -> dict[str, Any]:
        """Fill and submit web form.
        
        Args:
            url: Page URL
            form_data: Form field data
            submit: Submit form automatically
            
        Returns:
            Dictionary with form submission result
        """
        ...


@runtime_checkable
class WebhookTool(Protocol):
    """Interface for webhook operations."""
    
    async def create_webhook(
        self,
        url: str,
        events: list[str],
        secret: str | None = None
    ) -> dict[str, Any]:
        """Create webhook subscription.
        
        Args:
            url: Webhook URL
            events: Events to subscribe to
            secret: Webhook secret
            
        Returns:
            Dictionary with webhook information
        """
        ...
    
    async def trigger_webhook(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        signature: str | None = None
    ) -> dict[str, Any]:
        """Trigger webhook with payload.
        
        Args:
            webhook_url: Webhook URL
            payload: Payload data
            signature: HMAC signature
            
        Returns:
            Dictionary with trigger result
        """
        ...
    
    async def verify_webhook(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> dict[str, Any]:
        """Verify webhook signature.
        
        Args:
            payload: Raw payload
            signature: Received signature
            secret: Webhook secret
            
        Returns:
            Dictionary with verification result
        """
        ...


@runtime_checkable
class RssFeedTool(Protocol):
    """Interface for RSS feed operations."""
    
    async def parse_feed(
        self,
        feed_url: str,
        limit: int = 20
    ) -> dict[str, Any]:
        """Parse RSS feed.
        
        Args:
            feed_url: RSS feed URL
            limit: Maximum items to parse
            
        Returns:
            Dictionary with parsed feed
        """
        ...
    
    async def search_feeds(
        self,
        query: str,
        limit: int = 10
    ) -> dict[str, Any]:
        """Search for RSS feeds.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            Dictionary with feed search results
        """
        ...


@runtime_checkable
class WebSecurityTool(Protocol):
    """Interface for web security operations."""
    
    async def check_url_safety(
        self,
        url: str
    ) -> dict[str, Any]:
        """Check if URL is safe.
        
        Args:
            url: URL to check
            
        Returns:
            Dictionary with safety assessment
        """
        ...
    
    async def validate_ssl_certificate(
        self,
        domain: str
    ) -> dict[str, Any]:
        """Validate SSL certificate.
        
        Args:
            domain: Domain to check
            
        Returns:
            Dictionary with certificate info
        """
        ...
    
    async def scan_for_vulnerabilities(
        self,
        url: str,
        scan_type: str = "basic"
    ) -> dict[str, Any]:
        """Scan for web vulnerabilities.
        
        Args:
            url: Target URL
            scan_type: Type of scan to perform
            
        Returns:
            Dictionary with scan results
        """
        ...
