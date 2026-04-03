from mindflow_backend.runtime.output_categorizer import categorize_output
from mindflow_backend.runtime.processing.output_categorizer import categorize_output as processing_categorize_output


def test_decision_prefix() -> None:
    assert categorize_output("Vou usar a ferramenta de busca") == "decision"


def test_code_result_detection() -> None:
    assert categorize_output("```python\\nprint('ok')\\n```") == "code_result"


def test_summary_prefix() -> None:
    assert categorize_output("Aqui está o resultado final") == "summary"


def test_explanation_fallback() -> None:
    text = "x" * 100
    assert categorize_output(text) == "explanation"


def test_processing_module_reexports_canonical_implementation() -> None:
    assert processing_categorize_output is categorize_output
