"""alignment-check — map signals to rubric criteria as Observations.

This is the heart of the lens, and where its core principle is enforced:
**narrate-and-cite, never score.** For each criterion we gather the cited signal
evidence (deterministic) and derive coverage from thresholds where the signals
are pinned (deterministic). The only LLM-touched field is ``note`` — a short
narration *bound to the cited evidence*. The LLM never decides coverage and never
produces a mark.

Narration is opt-in (the ``llm`` flag threaded from the CLI) and degradable:
any LLM failure leaves ``note`` empty — the deterministic evidence + coverage
are never affected.
"""

from __future__ import annotations

import json
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


_NARRATE_SYSTEM = (
    "You write short observations for a lecturer who is marking student work. "
    "Given one rubric criterion, the cited analyser signals with their values, and a "
    "coverage status, write 1-2 plain sentences describing what the cited evidence shows, "
    "referring to signals by name. Rules: NEVER assign, imply, or suggest a mark, grade, "
    "score, percentage, level, or pass/fail judgement — the lecturer does that. Do not "
    "evaluate quality beyond what a signal value literally states. The coverage status is "
    "already determined deterministically; do not contradict or restate it. "
    "Respond with the observation sentences only."
)

_EVIDENCE_VALUE_CHARS = 600  # keep huge nested signal values from bloating the prompt


def _render_evidence(evidence: list[Evidence]) -> str:
    lines = []
    for e in evidence:
        value = json.dumps(e.value, default=str, ensure_ascii=False)
        if len(value) > _EVIDENCE_VALUE_CHARS:
            value = value[:_EVIDENCE_VALUE_CHARS] + "…(truncated)"
        lines.append(f"- {e.signal}: {value}")
    return "\n".join(lines) or "(no signals pinned for this criterion)"


def narrate(criterion: Criterion, evidence: list[Evidence], coverage: Coverage) -> str:
    """Produce a short narration bound to the cited evidence.

    Narrate-and-cite, never score: the LLM sees ONLY the criterion text, the
    cited evidence values, and the already-determined coverage. Degradable —
    any failure (no [llm] extra, no key, API error) returns "" and the
    deterministic observation stands on its own.
    """
    from . import llm

    prompt = (
        f"Criterion: {criterion.description}\n"
        f"Coverage (deterministic, do not contradict): {coverage.value if coverage else 'unknown'}\n"
        f"Cited evidence:\n{_render_evidence(evidence)}"
    )
    try:
        return llm.complete(
            prompt, system=_NARRATE_SYSTEM, model=llm.narrate_model(), max_tokens=300
        )
    except Exception:
        # Narration is an optional layer over a deterministic spine; a per-call
        # failure must never take down a cohort run. Empty note = the documented
        # degraded state.
        return ""


def observe_criterion(
    criterion: Criterion, bundle_result: dict[str, Any], *, llm: bool = False
) -> Observation:
    """Build one Observation for one criterion from one submission's signals."""
    evidence = gather_evidence(criterion, bundle_result)
    coverage = coverage_from_evidence(evidence)
    note = narrate(criterion, evidence, coverage) if llm else ""
    return Observation(
        criterion_id=criterion.id,
        evidence=evidence,
        note=note,
        coverage=coverage,
        coverage_source=CoverageSource.THRESHOLD,
    )


def observe_submission(
    rubric: Rubric, bundle_result: dict[str, Any], *, llm: bool = False
) -> list[Observation]:
    """All criterion observations for one submission."""
    return [observe_criterion(c, bundle_result, llm=llm) for c in rubric.rubric]
