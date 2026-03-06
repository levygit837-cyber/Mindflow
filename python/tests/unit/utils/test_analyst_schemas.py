"""Tests for Analyst agent mode schemas."""

from mindflow_backend.schemas.analyst import (
    AnalysisMode,
    AnalystOutput,
)


def test_analysis_modes() -> None:
    assert AnalysisMode.FAST == "fast"
    assert AnalysisMode.DEEP == "deep"


def test_analyst_output_fast_mode() -> None:
    output = AnalystOutput(
        summary="Found 3 relevant files",
        context_files_read=["src/main.py", "src/utils.py", "src/config.py"],
        symbol_map={"src/main.py": ["main", "setup"]},
        missing_info=["database schema not found"],
        suggested_model="flash",
        confidence=0.9,
        analysis_mode=AnalysisMode.FAST,
    )
    assert output.confidence >= 0.85  # should deliver directly
    assert output.analysis_mode == AnalysisMode.FAST


def test_analyst_confidence_thresholds() -> None:
    # High confidence: deliver directly
    high = AnalystOutput(summary="clear", confidence=0.9, analysis_mode=AnalysisMode.FAST)
    assert high.should_deliver_directly()

    # Medium confidence: deliver with caveats
    medium = AnalystOutput(summary="partial", confidence=0.7, analysis_mode=AnalysisMode.FAST)
    assert not medium.should_deliver_directly()
    assert medium.should_deliver_with_caveats()

    # Low confidence: escalate
    low = AnalystOutput(summary="unclear", confidence=0.5, analysis_mode=AnalysisMode.FAST)
    assert low.should_escalate()
