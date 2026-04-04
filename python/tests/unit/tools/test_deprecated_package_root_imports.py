from __future__ import annotations

import re
from pathlib import Path

DEPRECATED_PACKAGE_ROOT_PATTERN = re.compile(
    r"from mindflow_backend\.agents\.tools\.(filesystem|system|web|planning) "
    r"import [^\n]*V(?:2|3)\b"
)

ALLOWED_COMPAT_TESTS = {
    Path("tests/unit/tools/test_package_compat_exports.py"),
}


def test_only_compatibility_tests_use_deprecated_package_root_imports() -> None:
    tests_root = Path(__file__).resolve().parents[2]
    matches: list[str] = []

    for file_path in tests_root.rglob("*.py"):
        relative_path = file_path.relative_to(tests_root.parent)
        if relative_path in ALLOWED_COMPAT_TESTS:
            continue

        content = file_path.read_text(encoding="utf-8")
        if DEPRECATED_PACKAGE_ROOT_PATTERN.search(content):
            matches.append(str(relative_path))

    assert matches == []
