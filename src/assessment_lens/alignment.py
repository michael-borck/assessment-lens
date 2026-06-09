"""alignment-check — map signals to rubric criteria as Observations.

This is the heart of the lens, and where its core principle is enforced:
**narrate-and-cite, never score.** For each criterion we gather the cited signal
evidence (deterministic) and derive coverage from thresholds where the signals
are pinned (deterministic). The only LLM-touched field is ``note`` — a short
narration *bound to the cited evidence*. The LLM never decides coverage and never
produces a mark.

Status: the evidence-gathering and threshold-coverage are implemented; the LLM
narration is a clearly-marked stub (`narrate`) so the deterministic spine works
end-to-end today and the narration drops in without reshaping anything.
"""

from __future__ import annotations

from typing import Any

from .models import (
    Coverage,
    CoverageSource,
    Criterion,
    Evidence,
    Observation,
    Rubric,
)


def _is_present(value: Any) -> bool:
    """Is a signal value 'there' at all? (presence, not quality)."""
    if value is None:
        return False
    if isinstance(value, (str, list, dict)):
        return len(value) > 0
    return True


def coverage_from_evidence(evidence: list[Evidence]) -> Coverage:
    """Deterministic coverage from *presence* of the pinned signals.

    Not a mark — purely "is the evidence there?". A criterion with all its
    pinned signals present -> PRESENT; some present -> PARTIAL; none -> ABSENT.

    NOTE: per-signal numeric thresholds (e.g. critical_thinking >= 60 counts as
    'present') belong here too — deferred until the rubric schema grows a place
    for the lecturer to set them (see scoping doc open questions). For now
    coverage is presence-based, which is honest and deterministic.
    """
    if not evidence:
        return Coverage.ABSENT
    present = sum(1 for e in evidence if _is_present(e.value))
    if present == 0:
        return Coverage.ABSENT
    if present == len(evidence):
        return Coverage.PRESENT
    return Coverage.PARTIAL


def gather_evidence(criterion: Criterion, bundle_result: dict[str, Any]) -> list[Evidence]:
    """Collect cited signal values for a criterion from one submission's bundle.

    Uses the criterion's pinned ``signals_of_interest`` (the deterministic anchor).
    When none are pinned, returns [] — runtime signal selection is a near-term
    enhancement (the LLM would pick signals and we'd surface its choice here).
    """
    from .bundle import get_signal  # local import keeps bundle optional at import time

    evidence: list[Evidence] = []
    for signal_path in criterion.signals_of_interest:
        evidence.append(Evidence(signal=signal_path, value=get_signal(bundle_result, signal_path)))
    return evidence


def narrate(criterion: Criterion, evidence: list[Evidence], coverage: Coverage) -> str:
    """Produce a short narration bound to the cited evidence.

    STUB: returns "" today. When the [llm] extra lands, this becomes a
    narrate-and-cite call — given ONLY the criterion text + the cited evidence
    values + the coverage, write 1-2 sentences that *describe what the evidence
    shows*, citing the signals, and explicitly forbidding any mark/grade/score.
    The deterministic coverage above is passed in, not asked for.
    """
    # Intentionally not implemented — see docstring. The pipeline runs without it.
    return ""


def observe_criterion(criterion: Criterion, bundle_result: dict[str, Any]) -> Observation:
    """Build one Observation for one criterion from one submission's signals."""
    evidence = gather_evidence(criterion, bundle_result)
    coverage = coverage_from_evidence(evidence)
    note = narrate(criterion, evidence, coverage)
    return Observation(
        criterion_id=criterion.id,
        evidence=evidence,
        note=note,
        coverage=coverage,
        coverage_source=CoverageSource.THRESHOLD,
    )


def observe_submission(rubric: Rubric, bundle_result: dict[str, Any]) -> list[Observation]:
    """All criterion observations for one submission."""
    return [observe_criterion(c, bundle_result) for c in rubric.rubric]
