"""Network access control policy for MindFlow.

Controls network access by domain/IP allowlist and blocklist.
Based on Claude Code's network restrictions.
"""

import ipaddress
import re
from urllib.parse import urlparse
from typing import Tuple
from enum import Enum

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class NetworkAction(Enum):
    """Network policy action."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class NetworkPolicy:
    """Network access control policy.

    Features:
    - Domain allowlist (code-related, safe domains)
    - IP blocklist (private networks, loopback)
    - URL validation
    - Command validation (curl, wget, etc.)
    """

    # Allowed domains (code-related, safe)
    ALLOWED_DOMAINS = {
        # Package registries
        "pypi.org",
        "files.pythonhosted.org",
        "npmjs.com",
        "registry.npmjs.org",
        "rubygems.org",
        "crates.io",
        "static.crates.io",
        "maven.apache.org",
        "repo.maven.apache.org",

        # Code hosting
        "github.com",
        "raw.githubusercontent.com",
        "api.github.com",
        "gitlab.com",
        "bitbucket.org",

        # Documentation
        "docs.python.org",
        "developer.mozilla.org",
        "stackoverflow.com",
        "readthedocs.org",
        "readthedocs.io",

        # APIs
        "api.anthropic.com",
        "api.openai.com",
        "generativelanguage.googleapis.com",

        # CDNs
        "cdn.jsdelivr.net",
        "unpkg.com",
        "cdnjs.cloudflare.com",

        # Cloud providers (API endpoints)
        "amazonaws.com",
        "s3.amazonaws.com",
        "storage.googleapis.com",
        "blob.core.windows.net",
    }

    # Blocked IP ranges (private networks)
    BLOCKED_IP_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
        ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
        ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback
        ipaddress.ip_network("169.254.0.0/16"),   # Link-local
        ipaddress.ip_network("::1/128"),          # IPv6 loopback
        ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
        ipaddress.ip_network("fc00::/7"),         # IPv6 unique local
    ]

    def validate_url(self, url: str) -> Tuple[NetworkAction, str]:
        """Validate URL against network policy.

        Args:
            url: URL to validate

        Returns:
            Tuple of (action, reason)
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                return NetworkAction.DENY, "Invalid URL: no hostname"

            # Check domain allowlist
            if hostname in self.ALLOWED_DOMAINS:
                return NetworkAction.ALLOW, "Domain in allowlist"

            # Check if subdomain of allowed domain
            for allowed_domain in self.ALLOWED_DOMAINS:
                if hostname.endswith(f".{allowed_domain}"):
                    return NetworkAction.ALLOW, f"Subdomain of {allowed_domain}"

            # Check IP address
            try:
                ip = ipaddress.ip_address(hostname)

                # Check blocked ranges
                for blocked_range in self.BLOCKED_IP_RANGES:
                    if ip in blocked_range:
                        return NetworkAction.DENY, f"IP in blocked range: {blocked_range}"

                # Public IP - ask user
                return NetworkAction.ASK, f"Public IP address: {ip}"

            except ValueError:
                # Not an IP, it's a hostname
                pass

            # Unknown domain - ask user
            return NetworkAction.ASK, f"Unknown domain: {hostname}"

        except Exception as e:
            _logger.error(f"URL validation error: {e}")
            return NetworkAction.DENY, f"Validation error: {str(e)}"

    def validate_command(self, command: str) -> Tuple[NetworkAction, str]:
        """Validate command for network access.

        Detects network commands like curl, wget, nc, etc.

        Args:
            command: Shell command to validate

        Returns:
            Tuple of (action, reason)
        """
        # Detect network commands
        network_commands = ["curl", "wget", "nc", "netcat", "telnet", "ssh", "scp", "ftp", "sftp"]

        tokens = command.split()
        if not tokens:
            return NetworkAction.ALLOW, "Empty command"

        base_command = tokens[0]

        if base_command not in network_commands:
            return NetworkAction.ALLOW, "Not a network command"

        # Extract URL from command
        url_pattern = r"https?://[^\s\"']+"
        urls = re.findall(url_pattern, command)

        if not urls:
            # Network command without URL - might be dangerous
            return NetworkAction.ASK, f"Network command without URL: {base_command}"

        # Validate each URL
        for url in urls:
            action, reason = self.validate_url(url)
            if action != NetworkAction.ALLOW:
                return action, reason

        return NetworkAction.ALLOW, "All URLs allowed"

    def is_domain_allowed(self, domain: str) -> bool:
        """Check if domain is in allowlist.

        Args:
            domain: Domain name to check

        Returns:
            True if allowed, False otherwise
        """
        if domain in self.ALLOWED_DOMAINS:
            return True

        # Check subdomains
        for allowed_domain in self.ALLOWED_DOMAINS:
            if domain.endswith(f".{allowed_domain}"):
                return True

        return False

    def is_ip_blocked(self, ip_str: str) -> bool:
        """Check if IP is in blocklist.

        Args:
            ip_str: IP address string

        Returns:
            True if blocked, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_str)

            for blocked_range in self.BLOCKED_IP_RANGES:
                if ip in blocked_range:
                    return True

            return False

        except ValueError:
            # Invalid IP
            return True
