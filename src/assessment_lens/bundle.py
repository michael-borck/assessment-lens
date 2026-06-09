"""Thin wrapper over the ``bundle-analyser`` CLI.

assessment-lens composes **only bundle-analyser**, called **once per Submission
subfolder** (preserving the student/group boundary). bundle-analyser handles
per-file routing (via auto-analyser) and aggregation; the lens never talks to
individual analysers or auto-analyser directly.

Verified against bundle-analyser's real schema (BundleAnalysisResult):

    {
      "source": ..., "source_type": "folder", "total_files": N,
      "results": [
        {"file": "chat.txt", "analyser": "conversation-analyser",
         "result": { ...the analyser's output, with routed_to injected... },
         "error": null},
        ...
      ],
      ...
    }

`analyser` is auto-analyser's ``routed_to`` — the full member name, e.g.
``"conversation-analyser"``. A signal path's first segment is the member's short
name (``conversation``); the rest is a dotted path *into that file's result*.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .exceptions import BundleAnalyserError

BUNDLE_CLI = "bundle-analyser"


def is_available() -> bool:
    """True if the bundle-analyser CLI is on PATH."""
    return shutil.which(BUNDLE_CLI) is not None


def run_bundle(folder: Path, *, timeout: int = 1800) -> dict[str, Any]:
    """Run bundle-analyser over one submission folder and return its JSON aggregate.

    Raises BundleAnalyserError if the CLI is missing, fails, or emits non-JSON.
    """
    if not is_available():
        raise BundleAnalyserError(
            f"`{BUNDLE_CLI}` not found on PATH. Install with `pip install assessment-lens[analysers]` "
            "or point at an environment where bundle-analyser is installed."
        )
    # `bundle-analyser <path> --json` prints the BundleAnalysisResult to stdout.
    cmd = [BUNDLE_CLI, str(folder), "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise BundleAnalyserError(f"bundle-analyser timed out on {folder}") from exc

    if proc.returncode != 0:
        raise BundleAnalyserError(
            f"bundle-analyser failed on {folder} (exit {proc.returncode}):\n{proc.stderr.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise BundleAnalyserError(f"bundle-analyser returned non-JSON for {folder}: {exc}") from exc


_MISSING = object()


def _walk(node: Any, parts: list[str]) -> Any:
    """Walk a dotted path into a result value. dict by key, list by int index."""
    for key in parts:
        if isinstance(node, dict) and key in node:
            node = node[key]
        elif isinstance(node, list) and key.isdigit() and int(key) < len(node):
            node = node[int(key)]
        else:
            return _MISSING
    return node


def get_signal(bundle_result: dict[str, Any], dotted_path: str) -> Any:
    """Resolve a signal path (e.g. 'conversation.critical_thinking') from a bundle aggregate.

    The first segment is a member short name; ``{short}-analyser`` must match a
    FileResult's ``analyser`` (auto-analyser's ``routed_to``). The remaining
    segments are a dotted path into that file's ``result`` dict. Returns the
    value, or None if not found.

    First matching file wins. If several artefacts route to the same analyser
    (e.g. multiple code files), only the first is read — a near-term refinement
    is to aggregate across them; for now the rubric author can scope the folder.
    """
    analyser_key, _, rest = dotted_path.partition(".")
    target = f"{analyser_key}-analyser"
    rest_parts = rest.split(".") if rest else []

    for file_result in bundle_result.get("results", []):
        if not isinstance(file_result, dict) or file_result.get("analyser") != target:
            continue
        value = _walk(file_result.get("result"), rest_parts)
        if value is not _MISSING:
            return value
    return None
