"""Network utilities for MindFlow backend.

HTTP clients, URL manipulation, and network-related helpers.
"""

from .retry_utils import (
    retry_on_error,
    retry_with_jitter,
    exponential_backoff_retry,
    RetryState,
    retry_async_with_state,
)

from .http_utils import (
    HTTPClient,
    parse_response_headers,
    is_success_status,
    is_client_error,
    is_server_error,
    get_status_category,
    validate_url,
    extract_domain,
    extract_path,
    build_query_string,
    download_file_async,
    create_user_agent,
)

from .port_utils import (
    PortManager,
    get_port_manager,
    find_free_port,
    is_port_open,
    wait_for_port_open,
    wait_for_port_close,
)

from .url_utils import (
    parse_url,
    build_url,
    normalize_url,
    add_query_params,
    remove_query_params,
    get_query_param,
    get_domain,
    get_subdomain,
    is_valid_url,
    is_secure_url,
    get_url_extension,
    is_same_domain,
    get_relative_url,
    sanitize_url,
    extract_urls,
    extract_emails,
    encode_url_component,
    decode_url_component,
    build_api_url,
    get_path_segments,
    join_paths,
    resolve_url,
    get_canonical_url,
    is_internal_url,
    get_social_media_domain,
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
