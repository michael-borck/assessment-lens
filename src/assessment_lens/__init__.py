"""assessment-lens — signals-based assessment for the lens family.

A *lens* (assessment-aware product) that consumes analyser signals and maps them
to a rubric as **observations, not grades**. The AI narrates and cites; a human
assigns every mark. See docs/SCOPING.md.
"""

from .exceptions import AssessmentLensError
from .models import (
    AssessmentResult,
    Coverage,
    Criterion,
    DeliverableObservation,
    Evidence,
    ExpectedDeliverable,
    Observation,
    Rubric,
    SubmissionResult,
)

__version__ = "0.1.0"

__all__ = [
    "AssessmentLensError",
    "AssessmentResult",
    "Coverage",
    "Criterion",
    "DeliverableObservation",
    "Evidence",
    "ExpectedDeliverable",
    "Observation",
    "Rubric",
    "SubmissionResult",
    "__version__",
]
