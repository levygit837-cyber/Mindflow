"""Trusted client IP extraction helpers."""

from __future__ import annotations

from ipaddress import ip_address, ip_network

from starlette.requests import Request

from mindflow_backend.infra.config import Settings, get_settings


def _is_valid_ip(value: str) -> bool:
    try:
        ip_address(value)
    except ValueError:
        return False
    return True


def _is_trusted_proxy(client_host: str, settings: Settings) -> bool:
    if not settings.security_trust_proxy_headers:
        return False

    for candidate in settings.get_trusted_proxy_ips_list():
        try:
            if "/" in candidate:
                if ip_address(client_host) in ip_network(candidate, strict=False):
                    return True
            elif ip_address(client_host) == ip_address(candidate):
                return True
        except ValueError:
            continue

    return False


def get_client_ip(request: Request, *, settings: Settings | None = None) -> str:
    """Extract the client IP, trusting proxy headers only from known proxies."""
    active_settings = settings or get_settings()
    client_host = request.client.host if request.client else "unknown"

    if not _is_trusted_proxy(client_host, active_settings):
        return client_host

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        if _is_valid_ip(first_hop):
            return first_hop

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        candidate = real_ip.strip()
        if _is_valid_ip(candidate):
            return candidate

    return client_host
