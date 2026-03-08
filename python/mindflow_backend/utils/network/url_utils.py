"""URL manipulation utilities for MindFlow backend.

Functions for working with URLs and URIs.
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import (
    parse_qs,
    urlparse,
    urljoin,
    urlunparse,
    urlencode,
    quote,
    unquote,
)


def parse_url(url: str) -> Dict[str, str]:
    """Parse URL into components."""
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "netloc": parsed.netloc,
        "path": parsed.path,
        "params": parsed.params,
        "query": parsed.query,
        "fragment": parsed.fragment,
        "username": parsed.username or "",
        "password": parsed.password or "",
        "hostname": parsed.hostname or "",
        "port": parsed.port or 0,
    }


def build_url(
    scheme: str,
    netloc: str,
    path: str = "",
    params: str = "",
    query: str = "",
    fragment: str = "",
) -> str:
    """Build URL from components."""
    return urlunparse((scheme, netloc, path, params, query, fragment))


def normalize_url(url: str) -> str:
    """Normalize URL by removing redundant parts."""
    parsed = urlparse(url)
    
    # Remove default ports
    if (parsed.scheme == "http" and parsed.port == 80) or \
       (parsed.scheme == "https" and parsed.port == 443):
        netloc = parsed.hostname
        if parsed.port and parsed.port not in [80, 443]:
            netloc = f"{parsed.hostname}:{parsed.port}"
        else:
            netloc = parsed.hostname
    else:
        netloc = parsed.netloc
    
    # Remove trailing slash from path (except root)
    path = parsed.path.rstrip("/") if parsed.path != "/" else parsed.path
    
    # Remove fragment if not needed
    fragment = parsed.fragment
    
    return urlunparse((
        parsed.scheme,
        netloc,
        path,
        parsed.params,
        parsed.query,
        fragment,
    ))


def add_query_params(url: str, params: Dict[str, str]) -> str:
    """Add query parameters to URL."""
    parsed = urlparse(url)
    
    # Parse existing query parameters
    existing_params = parse_qs(parsed.query)
    
    # Add new parameters
    for key, value in params.items():
        existing_params[key] = [value]
    
    # Build new query string
    new_query = urlencode(existing_params, doseq=True)
    
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


def remove_query_params(url: str, param_names: List[str]) -> str:
    """Remove specific query parameters from URL."""
    parsed = urlparse(url)
    
    # Parse existing query parameters
    existing_params = parse_qs(parsed.query)
    
    # Remove specified parameters
    for param_name in param_names:
        existing_params.pop(param_name, None)
    
    # Build new query string
    new_query = urlencode(existing_params, doseq=True)
    
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


def get_query_param(url: str, param_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get specific query parameter from URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    values = params.get(param_name)
    return values[0] if values else default


def get_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.hostname


def get_subdomain(url: str) -> Optional[str]:
    """Extract subdomain from URL."""
    domain = get_domain(url)
    if not domain:
        return None
    
    parts = domain.split('.')
    if len(parts) > 2:
        return '.'.join(parts[:-2])
    return None


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def is_secure_url(url: str) -> bool:
    """Check if URL uses HTTPS."""
    return urlparse(url).scheme == "https"


def get_url_extension(url: str) -> Optional[str]:
    """Get file extension from URL."""
    path = urlparse(url).path
    if '.' in path:
        return path.split('.')[-1].lower()
    return None


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs have the same domain."""
    domain1 = get_domain(url1)
    domain2 = get_domain(url2)
    return domain1 and domain2 and domain1.lower() == domain2.lower()


def get_relative_url(base_url: str, target_url: str) -> Optional[str]:
    """Get relative URL from base to target."""
    try:
        from urllib.parse import urljoin
        return urljoin(base_url, target_url)
    except Exception:
        return None


def sanitize_url(url: str) -> str:
    """Sanitize URL by removing dangerous parts."""
    # Remove javascript: and data: URLs
    if url.lower().startswith(('javascript:', 'data:', 'vbscript:')):
        return ''
    
    # Ensure URL has scheme
    if not urlparse(url).scheme:
        url = 'https://' + url
    
    return url


def extract_urls(text: str) -> List[str]:
    """Extract all URLs from text."""
    # URL regex pattern
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
    
    return re.findall(url_pattern, text)


def extract_emails(text: str) -> List[str]:
    """Extract all email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def encode_url_component(component: str) -> str:
    """Encode URL component."""
    return quote(component, safe='')


def decode_url_component(component: str) -> str:
    """Decode URL component."""
    return unquote(component)


def build_api_url(base_url: str, endpoint: str, params: Optional[Dict[str, str]] = None) -> str:
    """Build API URL with endpoint and parameters."""
    url = urljoin(base_url.rstrip('/') + '/', endpoint.lstrip('/'))
    
    if params:
        url = add_query_params(url, params)
    
    return url


def get_path_segments(url: str) -> List[str]:
    """Get path segments from URL."""
    path = urlparse(url).path
    segments = [segment for segment in path.split('/') if segment]
    return segments


def join_paths(*paths: str) -> str:
    """Join URL path segments."""
    segments = []
    for path in paths:
        segments.extend([segment for segment in path.split('/') if segment])
    return '/' + '/'.join(segments)


def resolve_url(base_url: str, relative_url: str) -> str:
    """Resolve relative URL against base URL."""
    return urljoin(base_url, relative_url)


def get_canonical_url(url: str) -> str:
    """Get canonical form of URL."""
    # Parse and normalize
    parsed = urlparse(url.lower())
    
    # Ensure scheme
    if not parsed.scheme:
        parsed = urlparse('https://' + url)
    
    # Remove www prefix
    hostname = parsed.hostname
    if hostname and hostname.startswith('www.'):
        hostname = hostname[4:]
    
    # Remove trailing slash from path
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    
    # Sort query parameters
    if parsed.query:
        query_params = parse_qs(parsed.query)
        sorted_params = sorted(query_params.items())
        query = urlencode(sorted_params, doseq=True)
    else:
        query = ''
    
    return urlunparse((
        parsed.scheme,
        hostname + (f':{parsed.port}' if parsed.port else ''),
        path,
        parsed.params,
        query,
        '',  # Remove fragment
    ))


def is_internal_url(url: str, base_domain: str) -> bool:
    """Check if URL is internal to the base domain."""
    url_domain = get_domain(url)
    if not url_domain:
        return False
    
    return url_domain == base_domain or url_domain.endswith('.' + base_domain)


def get_social_media_domain(url: str) -> Optional[str]:
    """Get social media platform from URL."""
    domain = get_domain(url)
    if not domain:
        return None
    
    social_domains = {
        'twitter.com': 'twitter',
        'x.com': 'twitter',
        'facebook.com': 'facebook',
        'instagram.com': 'instagram',
        'linkedin.com': 'linkedin',
        'youtube.com': 'youtube',
        'tiktok.com': 'tiktok',
        'reddit.com': 'reddit',
        'github.com': 'github',
    }
    
    return social_domains.get(domain.lower())
