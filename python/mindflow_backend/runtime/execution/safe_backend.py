import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ExecuteResult:
    stdout: str
    stderr: str
    exitCode: int


class BackendProtocol(Protocol):
    async def execute(self, command: str) -> ExecuteResult:  # pragma: no cover - protocol
        ...


BLOCKED_PATTERNS = [
    re.compile(r"\brm\s", re.IGNORECASE),
    re.compile(r"\brmdir\s", re.IGNORECASE),
    re.compile(r"\bdel\s", re.IGNORECASE),
    re.compile(r"\bfind\b.*-delete", re.IGNORECASE),
    re.compile(r"\bxargs\b.*\brm\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bfdisk\b", re.IGNORECASE),
    re.compile(r"\bdd\s", re.IGNORECASE),
    re.compile(r"\bchmod\s", re.IGNORECASE),
    re.compile(r"\bchown\s", re.IGNORECASE),
    re.compile(r"\bkill\b", re.IGNORECASE),
    re.compile(r"\bkillall\b", re.IGNORECASE),
    re.compile(r"\bpkill\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breboot\b", re.IGNORECASE),
    re.compile(r"\bhalt\b", re.IGNORECASE),
    re.compile(r"\bpoweroff\b", re.IGNORECASE),
    re.compile(r"\biptables\b", re.IGNORECASE),
    re.compile(r"\bufw\b", re.IGNORECASE),
    re.compile(r"\bfirewall-cmd\b", re.IGNORECASE),
    re.compile(r"\buseradd\b", re.IGNORECASE),
    re.compile(r"\buserdel\b", re.IGNORECASE),
    re.compile(r"\bpasswd\b", re.IGNORECASE),
    re.compile(r"\busermod\b", re.IGNORECASE),
    re.compile(r"\bmount\b", re.IGNORECASE),
    re.compile(r"\bumount\b", re.IGNORECASE),
    re.compile(r"\bsystemctl\b", re.IGNORECASE),
    re.compile(r"\bservice\s", re.IGNORECASE),
    re.compile(r"\bcrontab\s+-[re]", re.IGNORECASE),
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bsu\s", re.IGNORECASE),
    re.compile(r"\bdoas\b", re.IGNORECASE),
    re.compile(r"\bssh\b", re.IGNORECASE),
    re.compile(r"\bscp\b", re.IGNORECASE),
    re.compile(r"\brsync\b.*@", re.IGNORECASE),
    re.compile(r"\bcurl\b.*-X\s*(POST|PUT|DELETE|PATCH)", re.IGNORECASE),
    re.compile(r"\bwget\b.*--post", re.IGNORECASE),
    re.compile(r"\|\s*(bash|sh|zsh|fish)\b", re.IGNORECASE),
    re.compile(r"\beval\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+--force\b", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-f", re.IGNORECASE),
    re.compile(r"\bdocker\s+(rm|rmi)\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
    re.compile(r"\bnohup\b", re.IGNORECASE),
    re.compile(r"\bdisown\b", re.IGNORECASE),
    re.compile(r":\(\)\s*\{", re.IGNORECASE),
]


class SafeBackend:
    def __init__(self, inner: BackendProtocol):
        self.inner = inner

    async def execute(self, command: str) -> ExecuteResult:
        normalized = command.strip()
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(normalized):
                return ExecuteResult(
                    stdout="",
                    stderr=(
                        "BLOCKED: This command matches a security rule and cannot be executed. "
                        f"Matched pattern: {pattern.pattern}"
                    ),
                    exitCode=1,
                )
        return await self.inner.execute(command)
