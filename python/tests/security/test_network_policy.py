"""Tests for Network Policy implementation."""

import pytest

from mindflow_backend.security.policies.network_policy import (
    NetworkPolicy,
    NetworkAction,
)


def test_network_policy_allowed_domain():
    """Test allowed domain passes."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("https://github.com/user/repo")

    assert action == NetworkAction.ALLOW
    assert "allowlist" in reason.lower()


def test_network_policy_allowed_subdomain():
    """Test subdomain of allowed domain passes."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("https://api.github.com/repos")

    assert action == NetworkAction.ALLOW


def test_network_policy_pypi_allowed():
    """Test PyPI is allowed."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("https://pypi.org/project/requests/")

    assert action == NetworkAction.ALLOW


def test_network_policy_npmjs_allowed():
    """Test npmjs is allowed."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("https://registry.npmjs.org/express")

    assert action == NetworkAction.ALLOW


def test_network_policy_unknown_domain():
    """Test unknown domain requires approval."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("https://unknown-site.com")

    assert action == NetworkAction.ASK
    assert "unknown domain" in reason.lower()


def test_network_policy_private_ip_blocked():
    """Test private IP is blocked."""
    policy = NetworkPolicy()

    # Test various private IPs
    private_ips = [
        "http://192.168.1.1",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://127.0.0.1",
    ]

    for ip_url in private_ips:
        action, reason = policy.validate_url(ip_url)
        assert action == NetworkAction.DENY
        assert "blocked range" in reason.lower()


def test_network_policy_loopback_blocked():
    """Test loopback is blocked."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("http://127.0.0.1:8000")

    assert action == NetworkAction.DENY


def test_network_policy_link_local_blocked():
    """Test link-local is blocked."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("http://169.254.1.1")

    assert action == NetworkAction.DENY


def test_network_policy_public_ip():
    """Test public IP requires approval."""
    policy = NetworkPolicy()
    action, reason = policy.validate_url("http://8.8.8.8")

    assert action == NetworkAction.ASK
    assert "public ip" in reason.lower()


def test_network_policy_curl_command():
    """Test curl command validation."""
    policy = NetworkPolicy()

    # Safe curl
    action, reason = policy.validate_command("curl https://github.com")
    assert action == NetworkAction.ALLOW

    # Curl to private IP
    action, reason = policy.validate_command("curl http://192.168.1.1")
    assert action == NetworkAction.DENY


def test_network_policy_wget_command():
    """Test wget command validation."""
    policy = NetworkPolicy()

    action, reason = policy.validate_command("wget https://pypi.org/package.tar.gz")
    assert action == NetworkAction.ALLOW


def test_network_policy_non_network_command():
    """Test non-network command passes."""
    policy = NetworkPolicy()

    action, reason = policy.validate_command("ls -la")
    assert action == NetworkAction.ALLOW
    assert "not a network command" in reason.lower()


def test_network_policy_network_command_without_url():
    """Test network command without URL requires approval."""
    policy = NetworkPolicy()

    action, reason = policy.validate_command("nc -l 8080")
    assert action == NetworkAction.ASK


def test_network_policy_is_domain_allowed():
    """Test is_domain_allowed method."""
    policy = NetworkPolicy()

    assert policy.is_domain_allowed("github.com") is True
    assert policy.is_domain_allowed("api.github.com") is True
    assert policy.is_domain_allowed("unknown.com") is False


def test_network_policy_is_ip_blocked():
    """Test is_ip_blocked method."""
    policy = NetworkPolicy()

    assert policy.is_ip_blocked("192.168.1.1") is True
    assert policy.is_ip_blocked("10.0.0.1") is True
    assert policy.is_ip_blocked("127.0.0.1") is True
    assert policy.is_ip_blocked("8.8.8.8") is False


def test_network_policy_invalid_url():
    """Test invalid URL is denied."""
    policy = NetworkPolicy()

    action, reason = policy.validate_url("not-a-url")
    assert action == NetworkAction.DENY


def test_network_policy_multiple_urls_in_command():
    """Test command with multiple URLs."""
    policy = NetworkPolicy()

    # All allowed
    action, reason = policy.validate_command(
        "curl https://github.com && wget https://pypi.org"
    )
    assert action == NetworkAction.ALLOW

    # One blocked
    action, reason = policy.validate_command(
        "curl https://github.com && wget http://192.168.1.1"
    )
    assert action == NetworkAction.DENY
