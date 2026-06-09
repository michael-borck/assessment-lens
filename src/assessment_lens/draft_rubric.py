"""draft-rubric — free-form Specification -> *proposed* structured Rubric.

NEAR-TERM WORKSTREAM (not v1). Free-form specs are the common case, so this
turns a human-readable brief into a proposed Rubric + expected deliverables +
signal->criterion mapping, which the lecturer then **reviews and edits** before
use. LLM-assisted; reuses document-analyser text extraction for binary specs.

Status: STUB. The function shape and contract are fixed so the CLI command and
the review flow can be built around it; the LLM body lands with the [llm] extra.

When implemented, harvest from video-analyser @ b3ae7e19:
  - utils/api_keys.py         -> multi-provider LLM key management
  - analysis/default_rubrics.py -> starter rubrics / few-shot exemplars
The prompt must emit our schema (assignment / expected_deliverables / rubric with
optional signals_of_interest) — and must NOT invent marks or weights.
"""

from __future__ import annotations

from pathlib import Path

from .exceptions import AssessmentLensError
from .models import Rubric


def draft_rubric(spec_path: str | Path) -> Rubric:
    """Propose a structured Rubric from a free-form specification file.

    Raises NotImplementedError until the LLM step is built. Callers (the CLI)
    should surface this as a friendly "coming soon" rather than a crash.
    """
    raise NotImplementedError(
        "draft-rubric is a near-term workstream and not implemented yet. "
        "For now, author the structured rubric by hand (see examples/) and pass it to `assess`."
    )


class DraftRubricUnavailable(AssessmentLensError):
    """Raised when draft-rubric is invoked before the LLM step is built."""
