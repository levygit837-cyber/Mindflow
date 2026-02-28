from __future__ import annotations

from collections.abc import Iterable, Iterator


def _normalize_line(raw_line: str | bytes) -> str:
    if isinstance(raw_line, bytes):
        return raw_line.decode("utf-8", errors="replace")
    return raw_line


def iter_sse_payloads(lines: Iterable[str | bytes]) -> Iterator[str]:
    """Yield SSE payload blocks by joining `data:` lines until a blank separator."""

    data_lines: list[str] = []

    for raw_line in lines:
        line = _normalize_line(raw_line).rstrip("\r\n")
        if line == "":
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue

        if line.startswith(":"):
            continue

        if not line.startswith("data:"):
            continue

        data_lines.append(line[5:].lstrip())

    if data_lines:
        yield "\n".join(data_lines)
