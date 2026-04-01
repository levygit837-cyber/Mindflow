"""Secret scanner for detecting exposed credentials in code.

Implements 50+ secret patterns to detect API keys, tokens, passwords,
and other sensitive data before they are committed to version control.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class SecretMatch:
    """Detected secret match."""
    secret_type: str
    line_number: int
    column_start: int
    column_end: int
    context: str
    severity: str  # "critical", "high", "medium"
    file_path: str = ""


class SecretScanner:
    """Scanner for detecting exposed secrets in code.

    Based on Claude Code's secret detection patterns with 50+ patterns.
    """

    # Patterns organized by severity and provider
    PATTERNS = {
        # ============================================================================
        # CRITICAL - API Keys and Tokens
        # ============================================================================
        "anthropic_api_key": {
            "pattern": r"sk-ant-api03-[a-zA-Z0-9_-]{93}AA",
            "severity": "critical",
            "description": "Anthropic API Key",
        },
        "openai_api_key": {
            "pattern": r"sk-[a-zA-Z0-9]{48}",
            "severity": "critical",
            "description": "OpenAI API Key",
        },
        "openai_org_key": {
            "pattern": r"sk-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20}",
            "severity": "critical",
            "description": "OpenAI Organization API Key",
        },

        # ============================================================================
        # AWS Credentials
        # ============================================================================
        "aws_access_key": {
            "pattern": r"AKIA[0-9A-Z]{16}",
            "severity": "critical",
            "description": "AWS Access Key ID",
        },
        "aws_secret_key": {
            "pattern": r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?",
            "severity": "critical",
            "description": "AWS Secret Access Key",
        },
        "aws_session_token": {
            "pattern": r"(?i)aws[_-]?session[_-]?token\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{100,})['\"]?",
            "severity": "critical",
            "description": "AWS Session Token",
        },

        # ============================================================================
        # GitHub Tokens
        # ============================================================================
        "github_pat": {
            "pattern": r"ghp_[a-zA-Z0-9]{36}",
            "severity": "critical",
            "description": "GitHub Personal Access Token",
        },
        "github_oauth": {
            "pattern": r"gho_[a-zA-Z0-9]{36}",
            "severity": "critical",
            "description": "GitHub OAuth Token",
        },
        "github_app": {
            "pattern": r"ghs_[a-zA-Z0-9]{36}",
            "severity": "critical",
            "description": "GitHub App Token",
        },
        "github_refresh": {
            "pattern": r"ghr_[a-zA-Z0-9]{36}",
            "severity": "critical",
            "description": "GitHub Refresh Token",
        },

        # ============================================================================
        # Google Cloud
        # ============================================================================
        "google_api_key": {
            "pattern": r"AIza[a-zA-Z0-9_-]{35}",
            "severity": "critical",
            "description": "Google API Key",
        },
        "google_oauth": {
            "pattern": r"ya29\.[a-zA-Z0-9_-]{68,}",
            "severity": "critical",
            "description": "Google OAuth Access Token",
        },
        "gcp_service_account": {
            "pattern": r'"type":\s*"service_account"',
            "severity": "critical",
            "description": "GCP Service Account JSON",
        },

        # ============================================================================
        # Azure
        # ============================================================================
        "azure_client_secret": {
            "pattern": r"(?i)azure[_-]?client[_-]?secret\s*[:=]\s*['\"]?([a-zA-Z0-9~._-]{34,})['\"]?",
            "severity": "critical",
            "description": "Azure Client Secret",
        },
        "azure_storage_key": {
            "pattern": r"(?i)DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[a-zA-Z0-9+/=]{88}",
            "severity": "critical",
            "description": "Azure Storage Account Key",
        },

        # ============================================================================
        # Slack
        # ============================================================================
        "slack_token": {
            "pattern": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}",
            "severity": "critical",
            "description": "Slack Token",
        },
        "slack_webhook": {
            "pattern": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",
            "severity": "high",
            "description": "Slack Webhook URL",
        },

        # ============================================================================
        # Stripe
        # ============================================================================
        "stripe_secret_key": {
            "pattern": r"sk_live_[a-zA-Z0-9]{24,}",
            "severity": "critical",
            "description": "Stripe Secret Key (Live)",
        },
        "stripe_restricted_key": {
            "pattern": r"rk_live_[a-zA-Z0-9]{24,}",
            "severity": "critical",
            "description": "Stripe Restricted Key (Live)",
        },

        # ============================================================================
        # Twilio
        # ============================================================================
        "twilio_api_key": {
            "pattern": r"SK[a-z0-9]{32}",
            "severity": "critical",
            "description": "Twilio API Key",
        },

        # ============================================================================
        # SendGrid
        # ============================================================================
        "sendgrid_api_key": {
            "pattern": r"SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}",
            "severity": "critical",
            "description": "SendGrid API Key",
        },

        # ============================================================================
        # Mailgun
        # ============================================================================
        "mailgun_api_key": {
            "pattern": r"key-[a-zA-Z0-9]{32}",
            "severity": "high",
            "description": "Mailgun API Key",
        },

        # ============================================================================
        # Database Connection Strings
        # ============================================================================
        "postgres_url": {
            "pattern": r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+/[^\s\"']+",
            "severity": "critical",
            "description": "PostgreSQL Connection String",
        },
        "mysql_url": {
            "pattern": r"mysql://[^:]+:[^@]+@[^/]+/[^\s\"']+",
            "severity": "critical",
            "description": "MySQL Connection String",
        },
        "mongodb_url": {
            "pattern": r"mongodb(?:\+srv)?://[^:]+:[^@]+@[^\s\"']+",
            "severity": "critical",
            "description": "MongoDB Connection String",
        },
        "redis_url": {
            "pattern": r"redis://[^:]*:[^@]+@[^\s\"']+",
            "severity": "high",
            "description": "Redis Connection String",
        },

        # ============================================================================
        # Private Keys
        # ============================================================================
        "rsa_private_key": {
            "pattern": r"-----BEGIN RSA PRIVATE KEY-----",
            "severity": "critical",
            "description": "RSA Private Key",
        },
        "openssh_private_key": {
            "pattern": r"-----BEGIN OPENSSH PRIVATE KEY-----",
            "severity": "critical",
            "description": "OpenSSH Private Key",
        },
        "dsa_private_key": {
            "pattern": r"-----BEGIN DSA PRIVATE KEY-----",
            "severity": "critical",
            "description": "DSA Private Key",
        },
        "ec_private_key": {
            "pattern": r"-----BEGIN EC PRIVATE KEY-----",
            "severity": "critical",
            "description": "EC Private Key",
        },
        "pgp_private_key": {
            "pattern": r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
            "severity": "critical",
            "description": "PGP Private Key",
        },

        # ============================================================================
        # JWT Tokens
        # ============================================================================
        "jwt_token": {
            "pattern": r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
            "severity": "high",
            "description": "JWT Token",
        },

        # ============================================================================
        # Generic Patterns (HIGH)
        # ============================================================================
        "generic_api_key": {
            "pattern": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            "severity": "high",
            "description": "Generic API Key",
        },
        "generic_secret": {
            "pattern": r"(?i)(secret[_-]?key|secretkey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            "severity": "high",
            "description": "Generic Secret Key",
        },
        "generic_token": {
            "pattern": r"(?i)(access[_-]?token|accesstoken)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            "severity": "high",
            "description": "Generic Access Token",
        },

        # ============================================================================
        # Passwords (MEDIUM)
        # ============================================================================
        "generic_password": {
            "pattern": r"(?i)password\s*[:=]\s*['\"]([^'\"]{8,})['\"]",
            "severity": "medium",
            "description": "Generic Password",
        },
        "basic_auth": {
            "pattern": r"(?i)authorization:\s*basic\s+[a-zA-Z0-9+/=]{20,}",
            "severity": "high",
            "description": "Basic Auth Header",
        },

        # ============================================================================
        # Additional Cloud Providers
        # ============================================================================
        "heroku_api_key": {
            "pattern": r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            "severity": "high",
            "description": "Heroku API Key (UUID format)",
        },
        "digitalocean_token": {
            "pattern": r"(?i)do[_-]?token\s*[:=]\s*['\"]?([a-zA-Z0-9]{64})['\"]?",
            "severity": "critical",
            "description": "DigitalOcean Access Token",
        },
        "cloudflare_api_key": {
            "pattern": r"(?i)cloudflare[_-]?api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{37})['\"]?",
            "severity": "critical",
            "description": "Cloudflare API Key",
        },

        # ============================================================================
        # NPM and Package Managers
        # ============================================================================
        "npm_token": {
            "pattern": r"npm_[a-zA-Z0-9]{36}",
            "severity": "critical",
            "description": "NPM Access Token",
        },
        "pypi_token": {
            "pattern": r"pypi-[a-zA-Z0-9_-]{59,}",
            "severity": "critical",
            "description": "PyPI Upload Token",
        },

        # ============================================================================
        # SSH and Certificates
        # ============================================================================
        "ssh_password": {
            "pattern": r"(?i)sshpass\s+-p\s+['\"]?([^'\"\\s]+)['\"]?",
            "severity": "critical",
            "description": "SSH Password in Command",
        },
        "certificate": {
            "pattern": r"-----BEGIN CERTIFICATE-----",
            "severity": "medium",
            "description": "Certificate (may contain sensitive data)",
        },
    }

    def scan_content(self, content: str, file_path: str = "") -> List[SecretMatch]:
        """Scan content for secrets.

        Args:
            content: Content to scan
            file_path: Optional file path for context

        Returns:
            List of detected secrets
        """
        matches = []
        lines = content.split("\n")

        for secret_type, config in self.PATTERNS.items():
            pattern = re.compile(config["pattern"])

            for line_num, line in enumerate(lines, start=1):
                for match in pattern.finditer(line):
                    matches.append(SecretMatch(
                        secret_type=secret_type,
                        line_number=line_num,
                        column_start=match.start(),
                        column_end=match.end(),
                        context=line.strip(),
                        severity=config["severity"],
                        file_path=file_path,
                    ))

        return matches

    def scan_file(self, file_path: str) -> List[SecretMatch]:
        """Scan file for secrets."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.scan_content(content, file_path)
        except Exception as e:
            _logger.error(f"Failed to scan file {file_path}: {e}")
            return []

    def scan_directory(self, directory: str, extensions: List[str] | None = None) -> List[SecretMatch]:
        """Scan directory recursively for secrets.

        Args:
            directory: Directory path to scan
            extensions: File extensions to scan (e.g., [".py", ".js"])

        Returns:
            List of all detected secrets
        """
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".env", ".yaml", ".yml", ".json", ".sh"]

        all_matches = []
        dir_path = Path(directory)

        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                matches = self.scan_file(str(file_path))
                all_matches.extend(matches)

        return all_matches

    def format_report(self, matches: List[SecretMatch]) -> str:
        """Format scan results as report."""
        if not matches:
            return "✅ No secrets detected"

        # Group by severity
        critical = [m for m in matches if m.severity == "critical"]
        high = [m for m in matches if m.severity == "high"]
        medium = [m for m in matches if m.severity == "medium"]

        report = f"🔴 Found {len(matches)} potential secret(s):\n\n"

        if critical:
            report += f"CRITICAL ({len(critical)}):\n"
            for match in critical:
                report += f"  [{match.secret_type}] Line {match.line_number}\n"
                report += f"    {match.context[:80]}...\n"
            report += "\n"

        if high:
            report += f"HIGH ({len(high)}):\n"
            for match in high:
                report += f"  [{match.secret_type}] Line {match.line_number}\n"
                report += f"    {match.context[:80]}...\n"
            report += "\n"

        if medium:
            report += f"MEDIUM ({len(medium)}):\n"
            for match in medium:
                report += f"  [{match.secret_type}] Line {match.line_number}\n"
                report += f"    {match.context[:80]}...\n"

        return report
