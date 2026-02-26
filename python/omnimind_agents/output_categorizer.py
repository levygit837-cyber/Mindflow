from __future__ import annotations

import re

from .types import OutputCategory


def categorize_output(text: str) -> OutputCategory:
    if not text or not text.strip():
        return "response"

    trimmed = text.lstrip()

    if re.search(r"^(I'll|I will|Let me|I'm going to|I am going to|Vou|Deixa eu|Vou usar)\b", trimmed, re.I):
        return "decision"

    if "```" in text:
        return "code_result"

    if re.search(
        r"^(Here's|Here is|Aqui está|Aqui estão|The result|Os resultados|O resultado|Based on)\b",
        trimmed,
        re.I,
    ):
        return "summary"

    if len(text.strip()) >= 80:
        return "explanation"

    return "response"
