from typing import Literal

OutputCategory = Literal["explanation", "decision", "code_result", "summary", "response"]


def categorize_output(text: str) -> OutputCategory:
    if not text or not text.strip():
        return "response"

    trimmed = text.lstrip()

    decision_prefixes = (
        "i'll",
        "i will",
        "let me",
        "i'm going to",
        "i am going to",
        "vou",
        "deixa eu",
        "vou usar",
    )
    if trimmed.lower().startswith(decision_prefixes):
        return "decision"

    if "```" in text:
        return "code_result"

    summary_prefixes = (
        "here's",
        "here is",
        "aqui está",
        "aqui estão",
        "the result",
        "os resultados",
        "o resultado",
        "based on",
    )
    if trimmed.lower().startswith(summary_prefixes):
        return "summary"

    if len(text.strip()) >= 80:
        return "explanation"

    return "response"
