"""Shared LLM plumbing for the lens's two LLM touchpoints (narrate, draft-rubric).

Key resolution is harvested + adapted from video-analyser @ b3ae7e19
``utils/api_keys.py`` (env var first, then a simple .env fallback). Provider is
Anthropic-only for now — the same choice conversation-analyser made; the
provider hook stays here so multi-provider can land later without touching
callers.

Everything LLM-shaped is opt-in and degradable: callers gate on ``available()``
or catch ``LLMUnavailable`` and fall back to the deterministic path.
"""

from __future__ import annotations

import os
from pathlib import Path

from .exceptions import AssessmentLensError

ENV_VAR = "ANTHROPIC_API_KEY"

# Narration is a high-volume 1-2 sentence task (cohort x criteria calls) ->
# Haiku, matching conversation-analyser's classifier choice. Drafting a rubric
# is one quality-sensitive call per assignment -> Opus. Both env-overridable.
DEFAULT_NARRATE_MODEL = "claude-haiku-4-5"
DEFAULT_DRAFT_MODEL = "claude-opus-4-8"


class LLMUnavailable(AssessmentLensError):
    """The [llm] extra is not installed or no API key is configured."""


def narrate_model() -> str:
    return os.getenv("ASSESSMENT_LENS_NARRATE_MODEL", DEFAULT_NARRATE_MODEL)


def draft_model() -> str:
    return os.getenv("ASSESSMENT_LENS_DRAFT_MODEL", DEFAULT_DRAFT_MODEL)


def _load_env_file() -> None:
    """Minimal .env loader (cwd upward) — no python-dotenv dependency."""
    for parent in [Path.cwd(), *Path.cwd().parents]:
        env_file = parent / ".env"
        if env_file.exists():
            try:
                for line in env_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
            except OSError:
                pass
            return


def get_api_key() -> str | None:
    if key := os.getenv(ENV_VAR):
        return key
    _load_env_file()
    return os.getenv(ENV_VAR)


def available() -> bool:
    """Is the LLM path usable (SDK installed + key resolvable)? Never raises."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return get_api_key() is not None


def complete(prompt: str, *, system: str, model: str, max_tokens: int = 1024) -> str:
    """One narrate-style completion. Raises LLMUnavailable when the path is off."""
    try:
        import anthropic
    except ImportError as exc:
        raise LLMUnavailable(
            "LLM features need the [llm] extra: pip install 'assessment-lens[llm]'"
        ) from exc
    api_key = get_api_key()
    if not api_key:
        raise LLMUnavailable(f"No API key found — set {ENV_VAR} (env or .env).")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
