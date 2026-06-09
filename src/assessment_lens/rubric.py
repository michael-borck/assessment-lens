"""Load, validate, and save Rubrics (the structured-rubric contract).

A Rubric is supplied as YAML or JSON (the MVP takes it as input; ``draft-rubric``
will later *propose* one from a free-form spec). The shape is in
ASSESSMENT-LENS-SCOPING.md and modelled in :mod:`assessment_lens.models`.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from .exceptions import RubricError
from .models import ContentKind, Rubric

# Extension -> content kind. Mirrors the analyser family's routing so deliverable
# reconciliation can decide which artefacts satisfy an ExpectedDeliverable.
# Kept intentionally small/obvious; extend as the family's coverage grows.
_EXT_TO_KIND: dict[str, ContentKind] = {
    # documents
    ".pdf": ContentKind.DOCUMENT,
    ".docx": ContentKind.DOCUMENT,
    ".doc": ContentKind.DOCUMENT,
    ".pptx": ContentKind.DOCUMENT,
    ".txt": ContentKind.DOCUMENT,
    ".md": ContentKind.DOCUMENT,
    ".rtf": ContentKind.DOCUMENT,
    # video
    ".mp4": ContentKind.VIDEO,
    ".mov": ContentKind.VIDEO,
    ".avi": ContentKind.VIDEO,
    ".webm": ContentKind.VIDEO,
    ".mkv": ContentKind.VIDEO,
    # audio
    ".mp3": ContentKind.AUDIO,
    ".wav": ContentKind.AUDIO,
    ".m4a": ContentKind.AUDIO,
    ".flac": ContentKind.AUDIO,
    ".ogg": ContentKind.AUDIO,
    # image
    ".png": ContentKind.IMAGE,
    ".jpg": ContentKind.IMAGE,
    ".jpeg": ContentKind.IMAGE,
    ".gif": ContentKind.IMAGE,
    ".webp": ContentKind.IMAGE,
    # code
    ".py": ContentKind.CODE,
    ".ipynb": ContentKind.CODE,
    ".js": ContentKind.CODE,
    ".ts": ContentKind.CODE,
    ".html": ContentKind.CODE,
    ".css": ContentKind.CODE,
    ".sql": ContentKind.CODE,
    ".java": ContentKind.CODE,
    ".cpp": ContentKind.CODE,
    ".c": ContentKind.CODE,
    # spreadsheet
    ".xlsx": ContentKind.SPREADSHEET,
    ".xlsm": ContentKind.SPREADSHEET,
    # data
    ".csv": ContentKind.DATA,
    ".json": ContentKind.DATA,
    ".parquet": ContentKind.DATA,
    ".sqlite": ContentKind.DATA,
    # diagram
    ".mmd": ContentKind.DIAGRAM,
    ".puml": ContentKind.DIAGRAM,
    ".dot": ContentKind.DIAGRAM,
    ".drawio": ContentKind.DIAGRAM,
}


def content_kind_for(path: Path) -> ContentKind | None:
    """Best-effort content kind for an artefact, by extension. None if unknown."""
    return _EXT_TO_KIND.get(path.suffix.lower())


def load_rubric(path: str | Path) -> Rubric:
    """Load and validate a Rubric from a YAML or JSON file."""
    p = Path(path)
    if not p.is_file():
        raise RubricError(f"Rubric file not found: {p}")

    raw = p.read_text(encoding="utf-8")
    try:
        if p.suffix.lower() == ".json":
            data = json.loads(raw)
        else:
            data = yaml.safe_load(raw)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise RubricError(f"Could not parse rubric {p}: {exc}") from exc

    if not isinstance(data, dict):
        raise RubricError(
            f"Rubric {p} must be a mapping at the top level, got {type(data).__name__}."
        )

    try:
        return Rubric.model_validate(data)
    except ValidationError as exc:
        raise RubricError(f"Rubric {p} failed validation:\n{exc}") from exc


def save_rubric(rubric: Rubric, path: str | Path) -> None:
    """Write a Rubric to disk as YAML (the human-reviewable form)."""
    p = Path(path)
    data = rubric.model_dump(mode="json", exclude_none=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
