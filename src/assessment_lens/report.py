"""Render an AssessmentResult into the two deliverables from the scoping doc.

1. **cohort triage sheet** — one row per (submission x criterion), sortable
   (e.g. all `coverage: absent` first), for 300-cohort scale. Emitted as CSV.
2. **per-student observation reports** — one readable sheet per submission, for
   the marking + feedback moment. Emitted as Markdown.

Neither contains a mark. They are reading aids for the human who marks.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from .models import AssessmentResult


def cohort_sheet_csv(result: AssessmentResult) -> str:
    """One row per (submission x criterion) + per (submission x deliverable)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["submission", "kind", "id", "coverage_or_status", "evidence", "note"])
    for sub in result.submissions:
        for obs in sub.observations:
            evidence = "; ".join(f"{e.signal}={e.value}" for e in obs.evidence)
            writer.writerow(
                [
                    sub.submission_id,
                    "criterion",
                    obs.criterion_id,
                    obs.coverage.value if obs.coverage else "",
                    evidence,
                    obs.note,
                ]
            )
        for dlv in sub.deliverables:
            writer.writerow(
                [sub.submission_id, "deliverable", dlv.deliverable_id, dlv.status, "", dlv.note]
            )
        if sub.distinctiveness is not None and sub.distinctiveness.spaces:
            d = sub.distinctiveness
            apart = any(s.stands_apart for s in d.spaces)
            close = any(s.notably_similar for s in d.spaces)
            status = "stands-apart" if apart else ("notably-similar" if close else "typical")
            ev = "; ".join(
                f"{s.space}: nearest={s.nearest_similarity}({s.nearest_submission_id}), mean={s.mean_similarity}"
                for s in d.spaces
            )
            writer.writerow([sub.submission_id, "distinctiveness", "cohort", status, ev, d.note])
    return buf.getvalue()


def student_report_markdown(result: AssessmentResult, submission_id: str) -> str:
    """A readable per-student observation sheet (no marks)."""
    sub = next((s for s in result.submissions if s.submission_id == submission_id), None)
    if sub is None:
        raise KeyError(f"No submission '{submission_id}' in result.")

    lines: list[str] = [
        f"# Observations — {submission_id}",
        f"_Assignment: {result.assignment}"
        + (f" ({result.component})_" if result.component else "_"),
        "",
        "> These are **observations, not grades**. Evidence is cited from analyser "
        "signals; you weigh it and assign the mark.",
        "",
        "## Deliverables",
    ]
    for dlv in sub.deliverables:
        mark = {"present": "✓", "missing": "✗", "wrong-type": "!"}.get(dlv.status, "?")
        detail = f" — {dlv.note}" if dlv.note else ""
        matched = f" ({', '.join(dlv.matched_artefacts)})" if dlv.matched_artefacts else ""
        lines.append(f"- {mark} **{dlv.deliverable_id}**: {dlv.status}{matched}{detail}")

    lines += ["", "## Criteria"]
    for obs in sub.observations:
        cov = obs.coverage.value if obs.coverage else "—"
        lines.append(f"### {obs.criterion_id} — coverage: {cov}")
        if obs.evidence:
            for e in obs.evidence:
                lines.append(f"- `{e.signal}` = {e.value}")
        else:
            lines.append("- _(no pinned signals; runtime selection not yet enabled)_")
        if obs.note:
            lines.append("")
            lines.append(obs.note)
        lines.append("")

    if sub.distinctiveness is not None and sub.distinctiveness.spaces:
        d = sub.distinctiveness
        lines += [
            "## Cohort comparison",
            "",
            "> A neutral, **direction-agnostic** observation — **not** a verdict. "
            "Standing apart can mean an out-of-the-box answer *or* a thin one; the "
            "criteria above carry the quality signal. High similarity is a prompt to "
            "*look*, never a finding of collusion.",
            "",
            d.note,
            "",
        ]
        for s in d.spaces:
            flags = []
            if s.stands_apart:
                flags.append("stands apart")
            if s.notably_similar:
                flags.append(f"notably close to `{s.nearest_submission_id}`")
            tail = f" — {', '.join(flags)}" if flags else ""
            lines.append(
                f"- **{s.space}**: nearest `{s.nearest_submission_id}` "
                f"({s.nearest_similarity}), cohort mean {s.mean_similarity}{tail}"
            )
        lines.append("")
    return "\n".join(lines)


def write_reports(result: AssessmentResult, out_dir: str | Path) -> Path:
    """Write the cohort sheet + one markdown report per submission into ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cohort-sheet.csv").write_text(cohort_sheet_csv(result), encoding="utf-8")
    reports = out / "reports"
    reports.mkdir(exist_ok=True)
    for sub in result.submissions:
        (reports / f"{sub.submission_id}.md").write_text(
            student_report_markdown(result, sub.submission_id), encoding="utf-8"
        )
    return out
