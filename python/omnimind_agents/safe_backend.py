from __future__ import annotations

import re
from typing import Any, Dict

BLOCKED_PATTERNS = [
    re.compile(r"\brm\s", re.I),
    re.compile(r"\brmdir\s", re.I),
    re.compile(r"\bdel\s", re.I),
    re.compile(r"\bfind\b.*-delete", re.I),
    re.compile(r"\bxargs\b.*\brm\b", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bfdisk\b", re.I),
    re.compile(r"\bdd\s", re.I),
    re.compile(r"\bchmod\s", re.I),
    re.compile(r"\bchown\s", re.I),
    re.compile(r"\bkill\b", re.I),
    re.compile(r"\bkillall\b", re.I),
    re.compile(r"\bpkill\b", re.I),
    re.compile(r"\bshutdown\b", re.I),
    re.compile(r"\breboot\b", re.I),
    re.compile(r"\bhalt\b", re.I),
    re.compile(r"\bpoweroff\b", re.I),
    re.compile(r"\biptables\b", re.I),
    re.compile(r"\bufw\b", re.I),
    re.compile(r"\bfirewall-cmd\b", re.I),
    re.compile(r"\buseradd\b", re.I),
    re.compile(r"\buserdel\b", re.I),
    re.compile(r"\bpasswd\b", re.I),
    re.compile(r"\busermod\b", re.I),
    re.compile(r"\bmount\b", re.I),
    re.compile(r"\bumount\b", re.I),
    re.compile(r"\bsystemctl\b", re.I),
    re.compile(r"\bservice\s", re.I),
    re.compile(r"\bcrontab\s+-[re]", re.I),
    re.compile(r"\bsudo\b", re.I),
    re.compile(r"\bsu\s", re.I),
    re.compile(r"\bdoas\b", re.I),
    re.compile(r"\bssh\b", re.I),
    re.compile(r"\bscp\b", re.I),
    re.compile(r"\brsync\b.*@", re.I),
    re.compile(r"\bcurl\b.*-X\s*(POST|PUT|DELETE|PATCH)", re.I),
    re.compile(r"\bwget\b.*--post", re.I),
    re.compile(r"\|\s*(bash|sh|zsh|fish)\b", re.I),
    re.compile(r"\beval\b", re.I),
    re.compile(r"\bgit\s+push\s+--force\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-f", re.I),
    re.compile(r"\bdocker\s+(rm|rmi)\b", re.I),
    re.compile(r"\bDROP\s+TABLE\b", re.I),
    re.compile(r"\bDELETE\s+FROM\b", re.I),
    re.compile(r"\bTRUNCATE\b", re.I),
    re.compile(r"\bnohup\b", re.I),
    re.compile(r"\bdisown\b", re.I),
    re.compile(r":\(\)\s*\{", re.I),
]


class SafeBackend:
    def __init__(self, inner_backend: Any) -> None:
        self.inner = inner_backend

    def __getattr__(self, item: str) -> Any:
        if item == "execute":
            return self.execute
        return getattr(self.inner, item)

    async def execute(self, command: str) -> Dict[str, Any]:
        normalized = command.strip()
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(normalized):
                matched = pattern.pattern
                return {
                    "stdout": "",
                    "stderr": (
                        "BLOCKED: This command matches a security rule and cannot be executed. "
                        f"Matched pattern: {matched}. If you need to perform this operation, "
                        "ask the user to do it manually."
                    ),
                    "exitCode": 1,
                }

        return await self.inner.execute(command)
