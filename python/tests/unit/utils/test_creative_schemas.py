"""Tests for Creative agent output schemas."""

from mindflow_backend.schemas.creative import (
    CreativeOutput,
    CreativeWorkType,
    DiscardedPath,
    ExploredPath,
    PathEvaluation,
    ShortlistedPath,
)


def test_creative_work_types() -> None:
    assert CreativeWorkType.NEW_FEATURE == "new_feature"
    assert CreativeWorkType.FRAMEWORK_CHANGE == "framework_change"
    assert CreativeWorkType.REFACTORING == "refactoring"
    assert CreativeWorkType.EXPLORATORY == "exploratory"


def test_path_evaluation_bounds() -> None:
    ev = PathEvaluation(
        impact=0.8,
        risk=0.3,
        effort=0.5,
        time_estimate="2 days",
        reversibility=0.9,
        learning_potential=0.6,
    )
    assert 0 <= ev.impact <= 1
    assert 0 <= ev.risk <= 1


def test_creative_output_round_trip() -> None:
    output = CreativeOutput(
        creative_work_type=CreativeWorkType.NEW_FEATURE,
        explored_paths=[
            ExploredPath(
                title="Path A",
                description="Approach A",
                evaluations=PathEvaluation(
                    impact=0.9,
                    risk=0.2,
                    effort=0.4,
                    time_estimate="1 day",
                    reversibility=0.8,
                    learning_potential=0.7,
                ),
            ),
        ],
        shortlisted_paths=[
            ShortlistedPath(
                path_title="Path A",
                composite_score=0.85,
                justification="Best overall",
            )
        ],
        discarded_paths=[],
        ask_questions_used=[],
        next_experiment="Implement Path A prototype",
        confidence_level=0.8,
    )
    assert len(output.explored_paths) == 1
    assert output.shortlisted_paths[0].composite_score == 0.85
    data = output.model_dump()
    assert data["creative_work_type"] == "new_feature"
