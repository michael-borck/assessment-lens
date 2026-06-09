"""Exception hierarchy for assessment-lens."""

from __future__ import annotations


class AssessmentLensError(Exception):
    """Base class for all assessment-lens errors."""


class RubricError(AssessmentLensError):
    """A rubric could not be loaded, parsed, or validated."""


class BundleAnalyserError(AssessmentLensError):
    """bundle-analyser could not be invoked or returned an error."""


class SubmissionError(AssessmentLensError):
    """A submissions folder was missing or malformed."""
