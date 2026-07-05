"""Report rendering — spreadsheet safety and failed-submission surfacing.

The cohort sheet's whole purpose is to be opened in Excel/Sheets, and evidence
values + LLM notes derive from *student-submitted* content — so formula
injection (OWASP CSV injection) is a real threat model here, not a nicety.
"""

from __future__ import annotations

import csv
import io

from assessment_lens.models import (
    AssessmentResult,
    Evidence,
    Observation,
    SubmissionResult,
)
from assessment_lens.report import (
    cohort_sheet_csv,
    student_report_markdown,
    write_reports,
)


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def test_csv_neutralises_formula_prefixes():
    # note and submission_id are the cells an adversarial student can start:
    # notes echo submitted content via the LLM; submission ids are folder names.
    obs = Observation(
        criterion_id="c1",
        evidence=[Evidence(signal="document.title", value='=HYPERLINK("http://evil")')],
        note="=1+1 looks like a formula",
    )
    result = AssessmentResult(
        assignment="t",
        submissions=[SubmissionResult(submission_id="=cmd|calc", observations=[obs])],
    )
    row = _rows(cohort_sheet_csv(result))[1]
    assert row[0] == "'=cmd|calc"  # submission cell neutralised
    assert row[5] == "'=1+1 looks like a formula"  # note cell neutralised
    assert not any(cell.startswith(("=", "+", "@")) for cell in row)


def test_csv_leaves_ordinary_cells_alone():
    obs = Observation(
        criterion_id="c1",
        evidence=[Evidence(signal="code.complexity", value=4)],
        note="Cited complexity is 4.",
    )
    result = AssessmentResult(
        assignment="t",
        submissions=[SubmissionResult(submission_id="alice", observations=[obs])],
    )
    row = _rows(cohort_sheet_csv(result))[1]
    assert row[0] == "alice"
    assert row[4] == "code.complexity=4"
    assert row[5] == "Cited complexity is 4."


def test_failed_submission_gets_an_error_row_and_report(tmp_path):
    result = AssessmentResult(
        assignment="t",
        submissions=[
            SubmissionResult(submission_id="alice"),
            SubmissionResult(submission_id="bob", error="bundle-analyser timed out on bob"),
        ],
    )
    rows = _rows(cohort_sheet_csv(result))
    error_row = next(r for r in rows if r[1] == "error")
    assert error_row[0] == "bob"
    assert error_row[3] == "failed"
    assert "timed out" in error_row[5]

    md = student_report_markdown(result, "bob")
    assert "Analysis failed" in md
    assert "timed out" in md
    assert "observations, not grades" not in md  # no empty observation scaffolding

    # write_reports still emits a report per submission, failed ones included
    out = write_reports(result, tmp_path / "out")
    assert (out / "reports" / "bob.md").exists()
    assert (out / "reports" / "alice.md").exists()
