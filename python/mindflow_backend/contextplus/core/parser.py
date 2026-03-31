# Multi-language symbol extraction with regex-based AST parsing
# FEATURE: Core parsing layer for structural code analysis

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SymbolKind(str, Enum):
    """Kind of code symbol."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ENUM = "enum"
    INTERFACE = "interface"
    STRUCT = "struct"
    TYPE = "type"
    TRAIT = "trait"
    CONST = "const"
    VARIABLE = "variable"
    EXPORT = "export"


@dataclass
class CodeSymbol:
    """A single code symbol extracted from source."""

    name: str
    kind: SymbolKind
    line: int
    end_line: int
    signature: str
    children: list[CodeSymbol] = field(default_factory=list)


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""

    path: str
    header: str
    symbols: list[CodeSymbol]
    line_count: int


LANG_MAP: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".cs": "csharp",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".lua": "lua",
    ".zig": "zig",
}

TS_PATTERNS: list[tuple[re.Pattern[str], SymbolKind]] = [
    (re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(?:<[^>]*>)?\s*\([^)]*\)(?:\s*:\s*[^\n{]+)?"), SymbolKind.FUNCTION),
    (re.compile(r"^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)"), SymbolKind.CLASS),
    (re.compile(r"^(?:export\s+)?(?:const\s+)?enum\s+(\w+)"), SymbolKind.ENUM),
    (re.compile(r"^(?:export\s+)?interface\s+(\w+)"), SymbolKind.INTERFACE),
    (re.compile(r"^(?:export\s+)?type\s+(\w+)\s*(?:<[^>]*>)?\s*="), SymbolKind.TYPE),
    (re.compile(r"^(?:export\s+)?const\s+(\w+)\s*(?::\s*[^=]+)?\s*="), SymbolKind.CONST),
]

PY_PATTERNS: list[tuple[re.Pattern[str], SymbolKind]] = [
    (re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\([^)]*\)(?:\s*->\s*\S+)?"), SymbolKind.FUNCTION),
    (re.compile(r"^class\s+(\w+)(?:\([^)]*\))?"), SymbolKind.CLASS),
]

RS_PATTERNS: list[tuple[re.Pattern[str], SymbolKind]] = [
    (re.compile(r"^(?:pub(?:\(crate\))?\s+)?(?:async\s+)?fn\s+(\w+)"), SymbolKind.FUNCTION),
    (re.compile(r"^(?:pub(?:\(crate\))?\s+)?struct\s+(\w+)"), SymbolKind.STRUCT),
    (re.compile(r"^(?:pub(?:\(crate\))?\s+)?enum\s+(\w+)"), SymbolKind.ENUM),
    (re.compile(r"^(?:pub(?:\(crate\))?\s+)?trait\s+(\w+)"), SymbolKind.TRAIT),
    (re.compile(r"^impl(?:<[^>]*>)?\s+(\w+)"), SymbolKind.CLASS),
]

GO_PATTERNS: list[tuple[re.Pattern[str], SymbolKind]] = [
    (re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\("), SymbolKind.FUNCTION),
    (re.compile(r"^type\s+(\w+)\s+struct"), SymbolKind.STRUCT),
    (re.compile(r"^type\s+(\w+)\s+interface"), SymbolKind.INTERFACE),
]

JAVA_PATTERNS: list[tuple[re.Pattern[str], SymbolKind]] = [
    (re.compile(r"^(?:public|private|protected)?\s*(?:static\s+)?(?:abstract\s+)?(?:final\s+)?\w+(?:<[^>]*>)?\s+(\w+)\s*\("), SymbolKind.METHOD),
    (re.compile(r"^(?:public|private|protected)?\s*(?:abstract\s+)?(?:final\s+)?class\s+(\w+)"), SymbolKind.CLASS),
    (re.compile(r"^(?:public|private|protected)?\s*(?:abstract\s+)?interface\s+(\w+)"), SymbolKind.INTERFACE),
    (re.compile(r"^(?:public|private|protected)?\s*enum\s+(\w+)"), SymbolKind.ENUM),
]

LANGUAGE_PATTERNS: dict[str, list[tuple[re.Pattern[str], SymbolKind]]] = {
    "typescript": TS_PATTERNS,
    "javascript": TS_PATTERNS,
    "python": PY_PATTERNS,
    "rust": RS_PATTERNS,
    "go": GO_PATTERNS,
    "java": JAVA_PATTERNS,
}

SUPPORTED_EXTENSIONS = frozenset(LANG_MAP.keys())


def detect_language(file_path: str) -> str | None:
    """Detect language from file extension."""
    return LANG_MAP.get(Path(file_path).suffix.lower())


def is_supported_file(file_path: str) -> bool:
    """Check if file is a supported source file."""
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


def extract_header(lines: list[str]) -> str:
    """Extract 2-line header from file content."""
    header_lines: list[str] = []
    for line in lines[:10]:
        stripped = re.sub(r"^//\s?|^#\s?|^--\s?|^\*\s?|^/\*\*?\s?|\*/$", "", line).strip()
        if stripped and not stripped.startswith("!") and not stripped.startswith("use ") and not stripped.startswith("import "):
            header_lines.append(stripped)
            if len(header_lines) >= 2:
                break
    return " | ".join(header_lines)


def _match_patterns(line: str, patterns: list[tuple[re.Pattern[str], SymbolKind]]) -> CodeSymbol | None:
    """Try to match a line against language-specific patterns."""
    for pattern, kind in patterns:
        match = pattern.search(line)
        if match and match.group(1):
            return CodeSymbol(
                name=match.group(1),
                kind=kind,
                line=0,
                end_line=0,
                signature=line.strip().rstrip("{").strip(),
                children=[],
            )
    return None


def _find_block_end(lines: list[str], start_index: int) -> int:
    """Find the end of a code block using brace counting."""
    depth = 0
    seen_opening = False

    for i in range(start_index, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                seen_opening = True
            elif ch == "}" and seen_opening:
                depth -= 1
                if depth <= 0:
                    return i + 1
    return len(lines)


async def analyze_file(file_path: str) -> FileAnalysis:
    """Analyze a source file and extract symbols.

    Args:
        file_path: Absolute path to the file

    Returns:
        FileAnalysis with header, symbols, and line count
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return FileAnalysis(path=file_path, header="", symbols=[], line_count=0)

    lines = content.splitlines()
    language = detect_language(file_path)
    header = extract_header(lines)

    symbols: list[CodeSymbol] = []

    if language and language in LANGUAGE_PATTERNS:
        patterns = LANGUAGE_PATTERNS[language]
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            symbol = _match_patterns(stripped, patterns)
            if symbol:
                symbol.line = i + 1
                if "{" in stripped or (language in ("typescript", "javascript", "rust", "go")):
                    end = _find_block_end(lines, i)
                    symbol.end_line = end
                else:
                    symbol.end_line = i + 1
                symbols.append(symbol)

    return FileAnalysis(
        path=file_path,
        header=header,
        symbols=symbols,
        line_count=len(lines),
    )


def format_symbol(symbol: CodeSymbol, indent: int = 0) -> str:
    """Format a symbol for display in context tree."""
    pad = "  " * indent
    line_range = f"L{symbol.line}-L{symbol.end_line}" if symbol.end_line > symbol.line else f"L{symbol.line}"
    return f"{pad}[{symbol.kind.value}] {line_range} {symbol.name}"


def flatten_symbols(symbols: list[CodeSymbol]) -> list[CodeSymbol]:
    """Flatten nested symbols into a flat list."""
    result: list[CodeSymbol] = []
    for sym in symbols:
        result.append(sym)
        result.extend(flatten_symbols(sym.children))
    return result