"""Core data models for assessment-lens.

These are the central contract described in the scoping doc
(lens-analysers/docs/ASSESSMENT-LENS-SCOPING.md). The design rule that shapes
every model here: **the lens narrates and cites; it never scores.** Signals
(deterministic, from analysers) are the anchor; an Observation maps a signal or
few to a Criterion with cited evidence and threshold-derived coverage. There is
deliberately no "mark" / "score" field anywhere in this module — a human assigns
every mark from the observations.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# --- Content kinds -----------------------------------------------------------
# The submission modes the analyser family routes by. An ExpectedDeliverable
# declares which kinds satisfy it; deliverable reconciliation matches a
# submission's artefacts to deliverables by these.
class ContentKind(str, Enum):
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    CODE = "code"
    SPREADSHEET = "spreadsheet"
    DATA = "data"
    DIAGRAM = "diagram"
    SITE = "site"


class Coverage(str, Enum):
    """Is the evidence there? NOT a mark.

    Threshold-derived where ``signals_of_interest`` are pinned; an LLM-suggested
    coverage is always flagged as a suggestion (see Observation.coverage_source).
    """

    PRESENT = "present"
    PARTIAL = "partial"
    ABSENT = "absent"


# --- Rubric side (input) -----------------------------------------------------
class ExpectedDeliverable(BaseModel):
    """A thing the Specification requires a student to hand in."""

    id: str
    description: str
    accepts: list[ContentKind] = Field(
        default_factory=list,
        description="Content kinds that satisfy this deliverable.",
    )


class Criterion(BaseModel):
    """One judged dimension of the Rubric."""

    id: str
    description: str
    signals_of_interest: list[str] = Field(
        default_factory=list,
        description=(
            "OPTIONAL dotted signal paths (e.g. 'conversation.critical_thinking') "
            "mapping signals to this criterion. Pinned -> deterministic coverage. "
            "Blank -> alignment-check selects signals at runtime and shows its choice."
        ),
    )


class Rubric(BaseModel):
    """A rubric for one assignment (or one component of it).

    ``component`` is a plain label (e.g. 'individual' / 'group'); ``assess``
    ignores it. Group/individual awareness lives at the rubric stage, never in
    the assess pipeline.
    """

    assignment: str
    component: str | None = None
    expected_deliverables: list[ExpectedDeliverable] = Field(default_factory=list)
    rubric: list[Criterion] = Field(default_factory=list, description="The marking criteria.")

    def criterion(self, criterion_id: str) -> Criterion | None:
        return next((c for c in self.rubric if c.id == criterion_id), None)


# --- Observation side (output) ----------------------------------------------
class Evidence(BaseModel):
    """A cited signal + its value — the deterministic anchor for an Observation."""

    signal: str
    value: object | None = None


class CoverageSource(str, Enum):
    THRESHOLD = "threshold"  # deterministic, from pinned signals_of_interest
    SUGGESTED = "suggested"  # LLM-suggested; treat as a suggestion, not a fact


class Observation(BaseModel):
    """A Signal (or few) mapped to a Criterion. Never a grade."""

    criterion_id: str
    evidence: list[Evidence] = Field(default_factory=list)
    note: str = Field(
        default="",
        description="LLM narration, bound to the cited evidence. Empty until alignment-check narrates.",
    )
    coverage: Coverage | None = None
    coverage_source: CoverageSource = CoverageSource.THRESHOLD


class DeliverableObservation(BaseModel):
    """A deterministic Observation about whether an expected deliverable is present."""

    deliverable_id: str
    status: str = Field(description="present | missing | wrong-type")
    note: str = ""
    matched_artefacts: list[str] = Field(default_factory=list)


class SubmissionResult(BaseModel):
    """All observations for one Submission (one subfolder = one student/group)."""

    submission_id: str
    observations: list[Observation] = Field(default_factory=list)
    deliverables: list[DeliverableObservation] = Field(default_factory=list)


class AssessmentResult(BaseModel):
    """The source-of-truth structured result for a whole cohort run."""

    assignment: str
    component: str | None = None
    submissions: list[SubmissionResult] = Field(default_factory=list)
