"""CLI smoke tests + the deterministic spine end-to-end (no bundle-analyser, no LLM)."""

from __future__ import annotations

import pytest

from assessment_lens import alignment
from assessment_lens.assess import assess
from assessment_lens.cli import main
from assessment_lens.models import Coverage
from assessment_lens.report import cohort_sheet_csv, student_report_markdown
from assessment_lens.rubric import load_rubric
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "data-viz-rubric.yaml"


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "assessment-lens" in capsys.readouterr().out


def test_cli_draft_rubric_is_friendly_not_yet(tmp_path):
    spec = tmp_path / "spec.txt"
    spec.write_text("do a thing")
    assert main(["draft-rubric", str(spec)]) == 2  # graceful "not yet"


def test_assess_end_to_end_with_stubbed_bundle(tmp_path, monkeypatch):
    # Stub bundle-analyser so the deterministic spine runs without the analyser stack.
    fake_signals = {
        "conversation": {"critical_thinking": 62},
        "reflection": {"depth": "dialogic"},
        "code": {"complexity": 4, "lint": 0, "code_level": "intermediate"},
    }
    monkeypatch.setattr("assessment_lens.assess.bundle.run_bundle", lambda folder: fake_signals)

    root = tmp_path / "subs"
    alice = root / "alice"
    alice.mkdir(parents=True)
    (alice / "report.pdf").write_text("x")
    (alice / "demo.mp4").write_text("x")

    rubric = load_rubric(EXAMPLE)
    result = assess(rubric, root)

    assert len(result.submissions) == 1
    sub = result.submissions[0]
    assert sub.submission_id == "alice"

    ct = next(o for o in sub.observations if o.criterion_id == "critical-thinking")
    assert {e.signal for e in ct.evidence} == {"conversation.critical_thinking", "reflection.depth"}
    assert ct.coverage is Coverage.PRESENT  # both pinned signals resolved

    # 'communication' has no pinned signals -> no evidence -> absent
    comm = next(o for o in sub.observations if o.criterion_id == "communication")
    assert comm.coverage is Coverage.ABSENT

    # deliverables both present
    assert {d.status for d in sub.deliverables} == {"present"}

    # reports render
    assert "alice" in cohort_sheet_csv(result)
    md = student_report_markdown(result, "alice")
    assert "observations, not grades" in md


def test_coverage_from_partial_evidence():
    from assessment_lens.models import Evidence

    ev = [Evidence(signal="a", value=10), Evidence(signal="b", value=None)]
    assert alignment.coverage_from_evidence(ev) is Coverage.PARTIAL
    assert alignment.coverage_from_evidence([]) is Coverage.ABSENT
