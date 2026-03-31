"""Network utilities for MindFlow backend.

HTTP clients, URL manipulation, and network-related helpers.
"""

from .http_utils import (
    HTTPClient,
    build_query_string,
    create_user_agent,
    download_file_async,
    extract_domain,
    extract_path,
    get_status_category,
    is_client_error,
    is_server_error,
    is_success_status,
    parse_response_headers,
    validate_url,
)
from .port_utils import (
    PortManager,
    find_free_port,
    get_port_manager,
    is_port_open,
    wait_for_port_close,
    wait_for_port_open,
)
from .retry_utils import (
    RetryState,
    exponential_backoff_retry,
    retry_async_with_state,
    retry_on_error,
    retry_with_jitter,
)
from .url_utils import (
    add_query_params,
    build_api_url,
    build_url,
    decode_url_component,
    encode_url_component,
    extract_emails,
    extract_urls,
    get_canonical_url,
    get_domain,
    get_path_segments,
    get_query_param,
    get_relative_url,
    get_social_media_domain,
    get_subdomain,
    get_url_extension,
    is_internal_url,
    is_same_domain,
    is_secure_url,
    is_valid_url,
    join_paths,
    normalize_url,
    parse_url,
    remove_query_params,
    resolve_url,
    sanitize_url,
)

__all__ = [
    # Retry utilities
    "retry_on_error",
    "retry_with_jitter",
    "exponential_backoff_retry",
    "RetryState",
    "retry_async_with_state",
    
    # HTTP utilities
    "HTTPClient",
    "parse_response_headers",
    "is_success_status",
    "is_client_error",
    "is_server_error",
    "get_status_category",
    "validate_url",
    "extract_domain",
    "extract_path",
    "build_query_string",
    "download_file_async",
    "create_user_agent",
    
    # Port utilities
    "PortManager",
    "get_port_manager",
    "find_free_port",
    "is_port_open",
    "wait_for_port_open",
    "wait_for_port_close",
    
    # URL utilities
    "parse_url",
    "build_url",
    "normalize_url",
    "add_query_params",
    "remove_query_params",
    "get_query_param",
    "get_domain",
    "get_subdomain",
    "is_valid_url",
    "is_secure_url",
    "get_url_extension",
    "is_same_domain",
    "get_relative_url",
    "sanitize_url",
    "extract_urls",
    "extract_emails",
    "encode_url_component",
    "decode_url_component",
    "build_api_url",
    "get_path_segments",
    "join_paths",
    "resolve_url",
    "get_canonical_url",
    "is_internal_url",
    "get_social_media_domain",
]
