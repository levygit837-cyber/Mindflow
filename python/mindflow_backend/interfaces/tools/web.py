"""Web tool interfaces for MindFlow backend.

Provides contracts for web-related operations including HTTP requests,
API interactions, browser automation, and web scraping with proper
security and rate limiting controls.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, List, Optional


@runtime_checkable
class WebToolInterface(Protocol):
    """Interface for web-related operations."""
    
    async def fetch_url(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
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
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        follow_redirects: bool = True
    ) -> Dict[str, Any]:
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
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
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
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
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
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
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
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
        """Load OpenAPI specification.
        
        Args:
            spec_url: URL or path to OpenAPI spec
            
        Returns:
            Dictionary with parsed specification
        """
        ...
    
    async def validate_api_response(
        self,
        response: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
        selector: Optional[str] = None,
        wait_for: Optional[str] = None,
        screenshot: bool = False
    ) -> Dict[str, Any]:
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
        form_data: Dict[str, str],
        submit: bool = True
    ) -> Dict[str, Any]:
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
        events: List[str],
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
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
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
        """Scan for web vulnerabilities.
        
        Args:
            url: Target URL
            scan_type: Type of scan to perform
            
        Returns:
            Dictionary with scan results
        """
        ...
