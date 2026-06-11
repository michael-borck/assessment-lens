"""draft-rubric — free-form Specification -> *proposed* structured Rubric.

Turns a human-readable brief into a proposed Rubric + expected deliverables +
signal->criterion mapping, which the lecturer then **reviews and edits** before
use. LLM-assisted; binary specs (.pdf/.docx/.pptx) are extracted via the
family's canonical extractor (document-analyser, optional extra).

Adapted from the video-analyser @ b3ae7e19 assessment subsystem (rubric_system /
default_rubrics) — but where that code scored (weights, 1-5 scoring guides),
this emits the assessment-lens schema, which has no mark, weight, or level
anywhere. The LLM proposes structure; a human owns every judgement.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from . import llm
from .exceptions import AssessmentLensError
from .models import Rubric

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".tex", ".html", ".htm"}
_BINARY_SUFFIXES = {".pdf", ".docx", ".pptx"}

_DRAFT_SYSTEM = (
    "You convert a free-form assignment specification into a structured assessment "
    "rubric proposal for the assessment-lens tool. The lecturer will review and edit "
    "your proposal before it is used; favour faithful extraction over invention.\n\n"
    "Respond with ONLY a JSON object (no prose, no code fences) with this shape:\n"
    "{\n"
    '  "assignment": "<short assignment name>",\n'
    '  "component": "<plain label like individual/group, or null>",\n'
    '  "expected_deliverables": [\n'
    '    {"id": "<kebab-case>", "description": "<what must be handed in>",\n'
    '     "accepts": ["<content kinds>"]}\n'
    "  ],\n"
    '  "rubric": [\n'
    '    {"id": "<kebab-case>", "description": "<one judged dimension>",\n'
    '     "signals_of_interest": ["<dotted signal paths, OPTIONAL>"]}\n'
    "  ]\n"
    "}\n\n"
    "Content kinds (the only valid `accepts` values): document, video, audio, image, "
    "code, spreadsheet, data, diagram, site.\n\n"
    "HARD RULES:\n"
    "- NEVER include a mark, weight, score, percentage, level, band, or scoring guide "
    "anywhere. The schema has no such field and the tool's core principle is that a "
    "human assigns every mark.\n"
    "- One criterion = one judged dimension from the specification's marking criteria. "
    "If the spec lists criteria, mirror them; do not invent extras.\n"
    "- `signals_of_interest` maps analyser signals to a criterion. Pin a path ONLY if "
    "it appears in the catalogue below and clearly fits; otherwise leave the list "
    "empty (empty is fine — the tool selects signals at runtime).\n\n"
    "Signal catalogue (dotted path — what it measures):\n"
    "- conversation.critical_thinking — 0-100 critical-thinking composite from an AI-chat transcript\n"
    "- conversation.engagement_band — Delegator/Iterative/Critical engagement band\n"
    "- reflection.depth — reflective-writing depth band (descriptive→transformative)\n"
    "- code.complexity — cyclomatic complexity of submitted code\n"
    "- code.lint — lint errors/warnings\n"
    "- code.code_level — beginner/intermediate/advanced estimate\n"
    "- document.integrity_score — 0-100 writing-integrity composite (AI markers, references)\n"
    "- document.readability — readability indices for prose\n"
    "- speech.delivery_score — 0-100 spoken-delivery composite (clarity, pace, fillers)\n"
    "- video.speech_metrics — per-scene speech metrics for a video presentation\n"
    "- git.flags — suspicious-history flags (bulk upload, last-minute dump)\n"
    "- provenance.flags — document-metadata flags (edit time, authorship)\n"
    "- revision.flags — tracked-changes flags (paste bursts, single-session)\n"
    "- spreadsheet.formula_ratio — computed-vs-hard-coded ratio in a workbook\n"
    "- site.accessibility — accessibility coverage for a website\n"
    "- diagram.structure — graph structure of a submitted diagram\n"
)


class DraftRubricUnavailable(AssessmentLensError):
    """Raised when draft-rubric is invoked but the LLM path is unavailable."""


def _read_spec(spec_path: Path) -> str:
    """Read the free-form spec — text directly, binaries via the family extractor."""
    if not spec_path.exists():
        raise AssessmentLensError(f"Specification not found: {spec_path}")
    suffix = spec_path.suffix.lower()
    if suffix in _BINARY_SUFFIXES:
        try:
            from document_analyser import extract_text
        except ImportError as exc:
            raise AssessmentLensError(
                f"Reading {suffix} specs needs document-analyser: "
                "pip install 'assessment-lens[documents]' (or pass a .txt/.md spec)."
            ) from exc
        return extract_text(spec_path)
    if suffix and suffix not in _TEXT_SUFFIXES:
        raise AssessmentLensError(
            f"Unsupported spec format '{suffix}' — use text/markdown or .pdf/.docx/.pptx."
        )
    return spec_path.read_text(encoding="utf-8", errors="replace")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _parse_proposal(raw: str) -> Rubric:
    data = json.loads(_strip_fences(raw))
    rubric = Rubric.model_validate(data)
    if not rubric.rubric:
        raise ValueError("proposal contains no criteria")
    return rubric


def draft_rubric(spec_path: str | Path) -> Rubric:
    """Propose a structured Rubric from a free-form specification file.

    The output is a *proposal* for the lecturer to review — never use it
    unreviewed. Raises DraftRubricUnavailable when the [llm] extra or API key
    is missing; the CLI surfaces that as a friendly message.
    """
    spec = _read_spec(Path(spec_path))
    if not spec.strip():
        raise AssessmentLensError(f"Specification is empty: {spec_path}")

    prompt = f"Assignment specification:\n\n{spec}"
    try:
        raw = llm.complete(prompt, system=_DRAFT_SYSTEM, model=llm.draft_model(), max_tokens=4096)
    except llm.LLMUnavailable as exc:
        raise DraftRubricUnavailable(str(exc)) from exc

    try:
        return _parse_proposal(raw)
    except (json.JSONDecodeError, ValidationError, ValueError) as first_error:
        # One repair round: show the model its own output + the validation error.
        retry_prompt = (
            f"{prompt}\n\nYour previous response was not a valid proposal "
            f"({first_error}):\n{raw}\n\nRespond again with ONLY the corrected JSON object."
        )
        raw = llm.complete(
            retry_prompt, system=_DRAFT_SYSTEM, model=llm.draft_model(), max_tokens=4096
        )
        try:
            return _parse_proposal(raw)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise AssessmentLensError(
                f"draft-rubric could not produce a valid proposal: {exc}"
            ) from exc
