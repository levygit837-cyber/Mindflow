"""Local HTTP server for OAuth2 callback handling.

Creates a temporary localhost HTTP server to receive OAuth2
authorization code callbacks.
"""

from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Callable
from urllib.parse import parse_qs, urlparse

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth2 callback."""

    def __init__(
        self,
        *args: Any,
        callback: Callable[[str, dict[str, str]], None],
        expected_state: str,
        **kwargs: Any,
    ):
        """Initialize callback handler.

        Args:
            callback: Callback function to handle authorization code
            expected_state: Expected state parameter for CSRF protection
        """
        self.callback = callback
        self.expected_state = expected_state
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Override to prevent default logging."""
        _logger.debug("oauth_callback_log", message=format % args)

    def do_GET(self) -> None:
        """Handle GET request (OAuth2 callback)."""
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            # Extract parameters
            code = query_params.get("code", [None])[0]
            state = query_params.get("state", [None])[0]
            error = query_params.get("error", [None])[0]

            # Validate state for CSRF protection
            if state != self.expected_state:
                self.send_error_response(400, "Invalid state - possible CSRF attack")
                _logger.warning(
                    "oauth_state_mismatch",
                    expected=self.expected_state,
                    received=state,
                )
                return

            # Handle error response
            if error:
                error_description = query_params.get("error_description", ["Unknown error"])[0]
                self.send_error_response(400, f"OAuth error: {error_description}")
                _logger.error("oauth_error", error=error, description=error_description)
                return

            # Handle successful authorization
            if code:
                # Call callback with authorization code
                self.callback(code, query_params)

                # Send success response
                self.send_success_response()
                _logger.info("oauth_callback_success")
            else:
                self.send_error_response(400, "Missing authorization code")
                _logger.error("oauth_missing_code")

        except Exception as e:
            self.send_error_response(500, f"Internal server error: {str(e)}")
            _logger.error("oauth_callback_exception", error=str(e))

    def send_success_response(self) -> None:
        """Send success HTML response."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    margin-bottom: 10px;
                }
                p {
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authentication Successful</h1>
                <p>You can close this window and return to the application.</p>
            </div>
        </body>
        </html>
        """

        self.wfile.write(html.encode())

    def send_error_response(self, code: int, message: str) -> None:
        """Send error HTML response.

        Args:
            code: HTTP status code
            message: Error message
        """
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        # Sanitize error message to prevent XSS
        sanitized_message = message.replace("<", "&lt;").replace(">", "&gt;")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #e74c3c;
                    margin-bottom: 10px;
                }}
                p {{
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authentication Error</h1>
                <p>{sanitized_message}</p>
            </div>
        </body>
        </html>
        """

        self.wfile.write(html.encode())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling multiple connections."""

    daemon_threads = True


class OAuthCallbackServer:
    """OAuth2 callback HTTP server.

    Features:
    - Temporary localhost server
    - Dynamic port assignment
    - CSRF state validation
    - Automatic shutdown
    """

    def __init__(self, expected_state: str, timeout: int = 300):
        """Initialize callback server.

        Args:
            expected_state: Expected state parameter for CSRF protection
            timeout: Server timeout in seconds (default: 5 minutes)
        """
        self.expected_state = expected_state
        self.timeout = timeout
        self.server: ThreadedHTTPServer | None = None
        self.port: int = 0
        self.authorization_code: str | None = None
        self.callback_params: dict[str, str] = {}
        self._callback_received = asyncio.Event()

    def _handle_callback(self, code: str, params: dict[str, str]) -> None:
        """Handle OAuth2 callback.

        Args:
            code: Authorization code
            params: Query parameters
        """
        self.authorization_code = code
        self.callback_params = params
        self._callback_received.set()

    async def start(self) -> int:
        """Start the callback server.

        Returns:
            Port number the server is listening on
        """
        # Create handler with callback
        def handler_factory(*args: Any, **kwargs: Any) -> OAuthCallbackHandler:
            return OAuthCallbackHandler(
                *args,
                callback=self._handle_callback,
                expected_state=self.expected_state,
                **kwargs,
            )

        # Create server with dynamic port (port=0)
        self.server = ThreadedHTTPServer(("127.0.0.1", 0), handler_factory)
        self.port = self.server.server_address[1]

        # Start server in background thread
        import threading

        server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        server_thread.start()

        _logger.info("oauth_callback_server_started", port=self.port)

        return self.port

    async def wait_for_callback(self) -> tuple[str | None, dict[str, str]]:
        """Wait for OAuth2 callback.

        Returns:
            Tuple of (authorization_code, callback_params)
        """
        try:
            # Wait for callback with timeout
            await asyncio.wait_for(self._callback_received.wait(), timeout=self.timeout)
            return self.authorization_code, self.callback_params
        except asyncio.TimeoutError:
            _logger.error("oauth_callback_timeout")
            return None, {}

    async def stop(self) -> None:
        """Stop the callback server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            _logger.info("oauth_callback_server_stopped", port=self.port)
