"""draft-rubric: spec reading, proposal parsing, the no-marks invariant."""

from __future__ import annotations

import json

import pytest

from assessment_lens import llm
from assessment_lens.draft_rubric import (
    DraftRubricUnavailable,
    _parse_proposal,
    _read_spec,
    draft_rubric,
)
from assessment_lens.exceptions import AssessmentLensError

PROPOSAL = {
    "assignment": "Data-Viz Project",
    "component": "individual",
    "expected_deliverables": [
        {"id": "report", "description": "Written report", "accepts": ["document"]}
    ],
    "rubric": [
        {
            "id": "critical-thinking",
            "description": "Evidence of critical engagement",
            "signals_of_interest": ["conversation.critical_thinking"],
        }
    ],
}


def _spec(tmp_path, text="Build a data-viz project. Marked on critical thinking."):
    spec = tmp_path / "spec.md"
    spec.write_text(text)
    return spec


def test_draft_rubric_happy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(PROPOSAL))
    rubric = draft_rubric(_spec(tmp_path))
    assert rubric.assignment == "Data-Viz Project"
    assert rubric.rubric[0].id == "critical-thinking"


def test_draft_rubric_strips_code_fences(tmp_path, monkeypatch):
    fenced = "```json\n" + json.dumps(PROPOSAL) + "\n```"
    monkeypatch.setattr(llm, "complete", lambda *a, **k: fenced)
    rubric = draft_rubric(_spec(tmp_path))
    assert rubric.assignment == "Data-Viz Project"


def test_draft_rubric_retries_once_on_invalid_json(tmp_path, monkeypatch):
    responses = iter(["not json at all", json.dumps(PROPOSAL)])
    calls = []

    def fake_complete(prompt, **kwargs):
        calls.append(prompt)
        return next(responses)

    monkeypatch.setattr(llm, "complete", fake_complete)
    rubric = draft_rubric(_spec(tmp_path))
    assert rubric.assignment == "Data-Viz Project"
    assert len(calls) == 2
    assert "not a valid proposal" in calls[1]


def test_draft_rubric_gives_up_after_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a, **k: "still not json")
    with pytest.raises(AssessmentLensError, match="could not produce a valid proposal"):
        draft_rubric(_spec(tmp_path))


def test_draft_rubric_unavailable_without_llm(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise llm.LLMUnavailable("no key")

    monkeypatch.setattr(llm, "complete", unavailable)
    with pytest.raises(DraftRubricUnavailable):
        draft_rubric(_spec(tmp_path))


def test_empty_spec_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(PROPOSAL))
    with pytest.raises(AssessmentLensError, match="empty"):
        draft_rubric(_spec(tmp_path, text="   "))


def test_read_spec_missing_file(tmp_path):
    with pytest.raises(AssessmentLensError, match="not found"):
        _read_spec(tmp_path / "nope.md")


def test_read_spec_unsupported_suffix(tmp_path):
    weird = tmp_path / "spec.exe"
    weird.write_text("hi")
    with pytest.raises(AssessmentLensError, match="Unsupported spec format"):
        _read_spec(weird)


def test_proposal_with_no_criteria_rejected():
    empty = dict(PROPOSAL, rubric=[])
    with pytest.raises(ValueError, match="no criteria"):
        _parse_proposal(json.dumps(empty))


def test_schema_has_no_mark_fields():
    """The core invariant: a proposal that smuggles in marks must not validate into marks."""
    smuggled = json.loads(json.dumps(PROPOSAL))
    smuggled["rubric"][0]["weight"] = 2.0
    smuggled["rubric"][0]["score"] = 5
    rubric = _parse_proposal(json.dumps(smuggled))
    dumped = rubric.model_dump()
    assert "weight" not in json.dumps(dumped)
    assert "score" not in json.dumps(dumped)
