"""Thin wrapper over the ``bundle-analyser`` CLI.

assessment-lens composes **only bundle-analyser**, called **once per Submission
subfolder** (preserving the student/group boundary). bundle-analyser handles
per-file routing (via auto-analyser) and aggregation; the lens never talks to
individual analysers or auto-analyser directly.

NOTE (integration point — verify against the real CLI): the exact JSON shape
bundle-analyser emits, and the invocation flags, must be confirmed against the
installed bundle-analyser. The resolver below walks the aggregate defensively so
a shape change degrades to "signal not found" rather than crashing.
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
    # TODO(integration): confirm the flag for JSON-to-stdout against bundle-analyser --help.
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


def get_signal(bundle_result: dict[str, Any], dotted_path: str) -> Any:
    """Resolve a dotted signal path (e.g. 'conversation.critical_thinking') from a bundle aggregate.

    Returns the value, or None if the path is not present. Defensive by design:
    walks nested dicts and, where a level is a list of per-file results, searches
    each entry. The first match wins.

    NOTE (integration point): the precise nesting (analyser name -> result ->
    signal) must be aligned with bundle-analyser's real output schema; this is a
    best-effort walk meant to be tightened once that schema is pinned.
    """
    parts = dotted_path.split(".")

    def walk(node: Any, remaining: list[str]) -> Any:
        if not remaining:
            return node
        key, rest = remaining[0], remaining[1:]
        if isinstance(node, dict):
            if key in node:
                return walk(node[key], rest)
            # try one level down through common container keys
            for container in ("results", "analysers", "signals", "files"):
                if container in node:
                    found = walk(node[container], remaining)
                    if found is not _MISSING:
                        return found
            return _MISSING
        if isinstance(node, list):
            for item in node:
                found = walk(item, remaining)
                if found is not _MISSING:
                    return found
            return _MISSING
        return _MISSING

    result = walk(bundle_result, parts)
    return None if result is _MISSING else result
