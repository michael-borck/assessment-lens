"""Tests for rubric loading + content-kind mapping + deliverable reconciliation."""

from __future__ import annotations

from pathlib import Path

import pytest

from assessment_lens.assess import discover_submissions, reconcile_deliverables
from assessment_lens.exceptions import RubricError, SubmissionError
from assessment_lens.models import ContentKind
from assessment_lens.rubric import content_kind_for, load_rubric, save_rubric

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "data-viz-rubric.yaml"


def test_load_example_rubric():
    rubric = load_rubric(EXAMPLE)
    assert rubric.assignment == "Data-Viz Project"
    assert {d.id for d in rubric.expected_deliverables} == {"report", "demo"}
    assert rubric.criterion("critical-thinking").signals_of_interest


def test_load_rubric_missing_file():
    with pytest.raises(RubricError):
        load_rubric("/no/such/rubric.yaml")


def test_load_rubric_rejects_non_mapping(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n")
    with pytest.raises(RubricError):
        load_rubric(bad)


def test_save_then_load_roundtrip(tmp_path):
    rubric = load_rubric(EXAMPLE)
    out = tmp_path / "copy.yaml"
    save_rubric(rubric, out)
    assert load_rubric(out) == rubric


def test_content_kind_for():
    assert content_kind_for(Path("a.pdf")) is ContentKind.DOCUMENT
    assert content_kind_for(Path("a.MP4")) is ContentKind.VIDEO
    assert content_kind_for(Path("a.py")) is ContentKind.CODE
    assert content_kind_for(Path("a.unknownext")) is None


def test_discover_submissions(tmp_path):
    (tmp_path / "alice").mkdir()
    (tmp_path / "bob").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "loose.txt").write_text("x")
    subs = discover_submissions(tmp_path)
    assert [s.name for s in subs] == ["alice", "bob"]


def test_discover_submissions_empty(tmp_path):
    with pytest.raises(SubmissionError):
        discover_submissions(tmp_path)


def test_reconcile_deliverables_present_and_missing(tmp_path):
    rubric = load_rubric(EXAMPLE)
    folder = tmp_path / "alice"
    folder.mkdir()
    (folder / "report.pdf").write_text("x")  # satisfies 'report' (document)
    # no video -> 'demo' missing
    obs = reconcile_deliverables(rubric, folder)
    by_id = {o.deliverable_id: o for o in obs}
    assert by_id["report"].status == "present"
    assert by_id["report"].matched_artefacts == ["report.pdf"]
    assert by_id["demo"].status == "missing"
