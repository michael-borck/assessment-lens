"""Provider selection in llm.py — defaults, env overrides, local (Ollama) path.

Pure config logic; no SDK calls or network.
"""

from __future__ import annotations

import pytest

from assessment_lens import llm


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "ASSESSMENT_LENS_PROVIDER",
        "ASSESSMENT_LENS_BASE_URL",
        "ASSESSMENT_LENS_NARRATE_MODEL",
        "ASSESSMENT_LENS_DRAFT_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)


def test_defaults_to_anthropic():
    assert llm.provider() == "anthropic"
    assert llm.base_url() is None  # anthropic uses its own SDK endpoint
    assert llm.narrate_model() == llm.DEFAULT_NARRATE_MODEL
    assert llm.draft_model() == llm.DEFAULT_DRAFT_MODEL


def test_ollama_provider_is_local_and_keyless(monkeypatch):
    monkeypatch.setenv("ASSESSMENT_LENS_PROVIDER", "ollama")
    assert llm.provider() == "ollama"
    assert llm.base_url() == "http://localhost:11434/v1"
    # local models default to the family's curated Ollama model, not a Claude id
    assert llm.narrate_model() == llm.DEFAULT_LOCAL_MODEL
    assert llm.draft_model() == llm.DEFAULT_LOCAL_MODEL
    # keyless: get_api_key returns a non-empty sentinel so the openai SDK is happy
    assert llm.get_api_key("ollama") == "unused"


def test_env_overrides_win(monkeypatch):
    monkeypatch.setenv("ASSESSMENT_LENS_PROVIDER", "ollama")
    monkeypatch.setenv("ASSESSMENT_LENS_BASE_URL", "http://192.168.1.5:11434/v1")
    monkeypatch.setenv("ASSESSMENT_LENS_NARRATE_MODEL", "qwen2.5:7b")
    assert llm.base_url() == "http://192.168.1.5:11434/v1"
    assert llm.narrate_model() == "qwen2.5:7b"


def test_cloud_provider_needs_a_key(monkeypatch):
    monkeypatch.setenv("ASSESSMENT_LENS_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # no key set and (in this repo) no .env with one -> None
    assert llm.get_api_key("openai") in (None, "")


def test_unknown_provider_fails_loudly_not_as_keyless_local(monkeypatch):
    # A typo'd provider must not be treated like Ollama and sent to a default
    # endpoint with a sentinel key — that produces a baffling remote error.
    monkeypatch.setenv("ASSESSMENT_LENS_PROVIDER", "anthropc")
    assert llm.available() is False
    assert llm.get_api_key() is None
    with pytest.raises(llm.LLMUnavailable) as exc:
        llm.complete("x", system="s", model="m")
    message = str(exc.value)
    assert "anthropc" in message  # names the bad value
    assert "anthropic" in message and "ollama" in message  # lists the valid ones
