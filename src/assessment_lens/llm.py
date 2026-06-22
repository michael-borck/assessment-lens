"""Shared LLM plumbing for the lens's two LLM touchpoints (narrate, draft-rubric).

Multi-provider, defaulting to **Anthropic** but supporting a **local LLM via
Ollama** (and any OpenAI-compatible endpoint) for the privacy-first desktop use
case — student work never has to leave the machine. Provider registry adapted
from assessment-bench's `providers.py`: Anthropic via its own SDK; Ollama /
OpenAI / OpenRouter through the openai SDK (OpenAI-compatible endpoints reached
via base_url). Key resolution follows the family pattern — env var first, then a
minimal .env fallback.

Select the provider with ``ASSESSMENT_LENS_PROVIDER`` (anthropic | ollama |
openai | openrouter | grok | gemini; default anthropic). Override the endpoint with
``ASSESSMENT_LENS_BASE_URL`` and the models with ``ASSESSMENT_LENS_NARRATE_MODEL``
/ ``ASSESSMENT_LENS_DRAFT_MODEL``.

Everything LLM-shaped is opt-in and degradable: callers gate on ``available()``
or catch ``LLMUnavailable`` and fall back to the deterministic path.
"""

from __future__ import annotations

import os
from pathlib import Path

from .exceptions import AssessmentLensError

DEFAULT_PROVIDER = "anthropic"

# env var per provider; Ollama is local and needs no key.
PROVIDER_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": None,
    "grok": "XAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

DEFAULT_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "grok": "https://api.x.ai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}

# Narration is a high-volume 1-2 sentence task (cohort x criteria) -> a small
# model; drafting a rubric is one quality-sensitive call -> a strong model. The
# Anthropic defaults match conversation-analyser; for local/compatible providers
# we default to the family's curated Ollama model (override per the env vars).
DEFAULT_NARRATE_MODEL = "claude-haiku-4-5"
DEFAULT_DRAFT_MODEL = "claude-opus-4-8"
DEFAULT_LOCAL_MODEL = "llama3.2:3b"


class LLMUnavailable(AssessmentLensError):
    """The [llm] extra is not installed or no API key is configured."""


def provider() -> str:
    return os.getenv("ASSESSMENT_LENS_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def base_url() -> str | None:
    if url := os.getenv("ASSESSMENT_LENS_BASE_URL"):
        return url
    return DEFAULT_BASE_URLS.get(provider())


def narrate_model() -> str:
    if env := os.getenv("ASSESSMENT_LENS_NARRATE_MODEL"):
        return env
    return DEFAULT_NARRATE_MODEL if provider() == "anthropic" else DEFAULT_LOCAL_MODEL


def draft_model() -> str:
    if env := os.getenv("ASSESSMENT_LENS_DRAFT_MODEL"):
        return env
    return DEFAULT_DRAFT_MODEL if provider() == "anthropic" else DEFAULT_LOCAL_MODEL


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


def get_api_key(prov: str | None = None) -> str | None:
    """Resolve the API key for ``prov`` (default: current provider).

    Ollama is local and keyless — returns a non-empty sentinel so the openai SDK
    (which requires a non-empty key) is satisfied and ``available()`` reads true.
    """
    prov = prov or provider()
    env_var = PROVIDER_KEYS.get(prov)
    if env_var is None:  # ollama (or unknown local) — no key needed
        return "unused"
    if key := os.getenv(env_var):
        return key
    _load_env_file()
    return os.getenv(env_var)


def available() -> bool:
    """Is the LLM path usable (SDK installed + key resolvable)? Never raises."""
    prov = provider()
    try:
        if prov == "anthropic":
            import anthropic  # noqa: F401
        else:
            import openai  # noqa: F401
    except ImportError:
        return False
    return get_api_key(prov) is not None


def complete(prompt: str, *, system: str, model: str, max_tokens: int = 1024) -> str:
    """One narrate-style completion against the configured provider.

    Raises LLMUnavailable when the path is off (missing SDK or key).
    """
    prov = provider()
    api_key = get_api_key(prov)
    if not api_key:
        raise LLMUnavailable(
            f"No API key for {prov} — set {PROVIDER_KEYS.get(prov)} (env or .env)."
        )
    if prov == "anthropic":
        return _complete_anthropic(
            prompt, system=system, model=model, max_tokens=max_tokens, api_key=api_key
        )
    return _complete_openai_compatible(
        prompt, system=system, model=model, max_tokens=max_tokens, api_key=api_key
    )


def _complete_anthropic(
    prompt: str, *, system: str, model: str, max_tokens: int, api_key: str
) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise LLMUnavailable(
            "LLM features need the [llm] extra: pip install 'assessment-lens[llm]'"
        ) from exc
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _complete_openai_compatible(
    prompt: str, *, system: str, model: str, max_tokens: int, api_key: str
) -> str:
    try:
        import openai
    except ImportError as exc:
        raise LLMUnavailable(
            "Local/OpenAI-compatible providers need the [llm] extra: "
            "pip install 'assessment-lens[llm]'"
        ) from exc
    client = openai.OpenAI(api_key=api_key, base_url=base_url())
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()
