"""Tests for the core models + the rule that they carry no marks."""

from __future__ import annotations

from assessment_lens.models import (
    AssessmentResult,
    ContentKind,
    Coverage,
    CoverageSource,
    Criterion,
    Evidence,
    ExpectedDeliverable,
    Observation,
    Rubric,
    SubmissionResult,
)


def test_rubric_roundtrips_through_dict():
    rubric = Rubric(
        assignment="Demo",
        component="individual",
        expected_deliverables=[
            ExpectedDeliverable(
                id="report", description="2000 words", accepts=[ContentKind.DOCUMENT]
            )
        ],
        rubric=[Criterion(id="ct", description="critical thinking", signals_of_interest=["a.b"])],
    )
    again = Rubric.model_validate(rubric.model_dump())
    assert again == rubric
    assert again.criterion("ct") is not None
    assert again.criterion("missing") is None


def test_observation_has_no_score_field():
    # The whole design: observations never carry a mark.
    fields = set(Observation.model_fields)
    for forbidden in ("score", "mark", "grade", "points", "weight"):
        assert forbidden not in fields


def test_observation_defaults_are_evidence_bound():
    obs = Observation(
        criterion_id="ct",
        evidence=[Evidence(signal="conversation.critical_thinking", value=62)],
        coverage=Coverage.PARTIAL,
    )
    assert obs.note == ""  # narration empty until alignment-check fills it
    assert obs.coverage_source is CoverageSource.THRESHOLD


def test_assessment_result_nesting():
    result = AssessmentResult(
        assignment="Demo",
        submissions=[SubmissionResult(submission_id="alice")],
    )
    assert result.submissions[0].submission_id == "alice"
