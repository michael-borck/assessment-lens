"""The `assess` pipeline — structured rubric + submissions folder -> observations.

Folder-dumb by design: ``assess`` only ever sees one rubric + one folder of
submission subfolders. It runs bundle-analyser once per subfolder, owns the
deterministic deliverable-reconciliation step itself, and asks alignment-check
for the per-criterion observations.

    submissions_root/
      alice/   <- one Submission (artefacts inside)
      bob/
      group-3/
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from . import alignment, bundle, distinctiveness
from .exceptions import SubmissionError
from .models import (
    AssessmentResult,
    DeliverableObservation,
    Rubric,
    SubmissionResult,
)
from .rubric import content_kind_for


def discover_submissions(root: str | Path) -> list[Path]:
    """One Submission per immediate subfolder of ``root`` (sorted, hidden skipped)."""
    r = Path(root)
    if not r.is_dir():
        raise SubmissionError(f"Submissions root is not a directory: {r}")
    subs = sorted(p for p in r.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not subs:
        raise SubmissionError(
            f"No submission subfolders found in {r}. Expect one subfolder per student/group."
        )
    return subs


def _artefacts(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and not p.name.startswith("."))


def reconcile_deliverables(rubric: Rubric, folder: Path) -> list[DeliverableObservation]:
    """Deterministically map a submission's artefacts to expected_deliverables.

    The lens owns this — it is not a signal and not an LLM judgement. For each
    expected deliverable, find artefacts whose content kind is in ``accepts``.
    Emits present / missing observations (wrong-type handling can grow here).
    """
    artefacts = _artefacts(folder)
    kinds = {p: content_kind_for(p) for p in artefacts}
    out: list[DeliverableObservation] = []
    for deliverable in rubric.expected_deliverables:
        accepted = set(deliverable.accepts)
        matched = [p for p, k in kinds.items() if k is not None and k in accepted]
        if matched:
            out.append(
                DeliverableObservation(
                    deliverable_id=deliverable.id,
                    status="present",
                    matched_artefacts=[p.name for p in matched],
                )
            )
        else:
            accepts_label = ", ".join(k.value for k in deliverable.accepts) or "any"
            out.append(
                DeliverableObservation(
                    deliverable_id=deliverable.id,
                    status="missing",
                    note=f"Expected a {accepts_label} artefact for '{deliverable.description}'; none found.",
                )
            )
    return out


def _assess_one(
    rubric: Rubric, folder: Path, *, llm: bool = False
) -> tuple[SubmissionResult, dict[str, Any]]:
    """One submission → its result + the raw bundle aggregate (kept for cohort steps)."""
    bundle_result = bundle.run_bundle(folder)
    observations = alignment.observe_submission(rubric, bundle_result, llm=llm)
    deliverables = reconcile_deliverables(rubric, folder)
    result = SubmissionResult(
        submission_id=folder.name,
        observations=observations,
        deliverables=deliverables,
    )
    return result, bundle_result


def assess_submission(rubric: Rubric, folder: Path, *, llm: bool = False) -> SubmissionResult:
    """Run the full pipeline for one submission folder."""
    result, _ = _assess_one(rubric, folder, llm=llm)
    return result


def assess(
    rubric: Rubric,
    submissions_root: str | Path,
    *,
    only: Iterable[str] | None = None,
    llm: bool = False,
    progress: Callable[[str], None] | None = None,
) -> AssessmentResult:
    """Assess a whole cohort. ``only`` optionally restricts to named submission ids.

    ``progress`` is an optional callable(str) for CLI/UI status lines (one per
    submission, then the cohort post-pass).
    """
    say = progress or (lambda _msg: None)
    submissions = discover_submissions(submissions_root)
    if only is not None:
        wanted = set(only)
        submissions = [s for s in submissions if s.name in wanted]

    results: list[SubmissionResult] = []
    vectors: dict[str, list[float] | None] = {}
    for i, folder in enumerate(submissions, start=1):
        say(f"assessing {folder.name} ({i}/{len(submissions)})")
        result, bundle_result = _assess_one(rubric, folder, llm=llm)
        results.append(result)
        vectors[result.submission_id] = distinctiveness.submission_text_vector(bundle_result)

    # Cohort post-pass: distinctiveness is relative, so it can only run once every
    # submission's vector is in hand. No-op if embeddings/lens-embed are absent.
    say("computing cohort distinctiveness")
    distinctiveness.annotate_cohort(results, vectors)

    return AssessmentResult(
        assignment=rubric.assignment,
        component=rubric.component,
        submissions=results,
    )
