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


def test_cli_draft_rubric_friendly_when_llm_unavailable(tmp_path, monkeypatch):
    from assessment_lens import llm

    def unavailable(*args, **kwargs):
        raise llm.LLMUnavailable("no key")

    monkeypatch.setattr(llm, "complete", unavailable)
    spec = tmp_path / "spec.txt"
    spec.write_text("do a thing")
    assert main(["draft-rubric", str(spec)]) == 2  # graceful, not a crash


def test_cli_draft_rubric_writes_reviewed_proposal(tmp_path, monkeypatch):
    import json

    from assessment_lens import llm

    proposal = {
        "assignment": "T",
        "expected_deliverables": [],
        "rubric": [{"id": "c1", "description": "One judged dimension"}],
    }
    monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(proposal))
    spec = tmp_path / "spec.txt"
    spec.write_text("do a thing, marked on one judged dimension")
    out = tmp_path / "rubric.yaml"
    assert main(["draft-rubric", str(spec), "-o", str(out)]) == 0
    text = out.read_text()
    assert text.startswith("# PROPOSED rubric")
    assert load_rubric(out).rubric[0].id == "c1"


def test_assess_end_to_end_with_stubbed_bundle(tmp_path, monkeypatch):
    # Stub bundle-analyser with its REAL aggregate shape (BundleAnalysisResult)
    # so the deterministic spine + signal resolver run without the analyser stack.
    fake_bundle = {
        "source": "alice",
        "source_type": "folder",
        "total_files": 3,
        "results": [
            {
                "file": "chat.txt",
                "analyser": "conversation-analyser",
                "result": {"critical_thinking": 62, "routed_to": "conversation-analyser"},
                "error": None,
            },
            {
                "file": "journal.md",
                "analyser": "reflection-analyser",
                "result": {"depth": "dialogic"},
                "error": None,
            },
            {
                "file": "main.py",
                "analyser": "code-analyser",
                "result": {"complexity": 4, "lint": 0, "code_level": "intermediate"},
                "error": None,
            },
        ],
    }
    monkeypatch.setattr("assessment_lens.assess.bundle.run_bundle", lambda folder: fake_bundle)

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


def test_get_signal_resolves_against_real_bundle_shape():
    from assessment_lens.bundle import get_signal

    bundle = {
        "results": [
            {
                "file": "main.py",
                "analyser": "code-analyser",
                "result": {"complexity": 4, "nested": {"score": 9}},
                "error": None,
            },
            {"file": "img.png", "analyser": None, "result": None, "error": None},
        ]
    }
    assert get_signal(bundle, "code.complexity") == 4
    assert get_signal(bundle, "code.nested.score") == 9  # dotted path into result
    assert get_signal(bundle, "code.missing") is None
    assert get_signal(bundle, "reflection.depth") is None  # no such analyser routed
    assert get_signal({"results": []}, "code.complexity") is None
