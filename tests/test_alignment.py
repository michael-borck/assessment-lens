"""alignment-check: evidence gathering, coverage, and (mocked) narration."""

from __future__ import annotations

from assessment_lens import alignment, llm
from assessment_lens.models import Coverage, Criterion, Evidence, Rubric

CRITERION = Criterion(
    id="critical-thinking",
    description="Evidence of critical engagement",
    signals_of_interest=["conversation.critical_thinking"],
)
BUNDLE = {
    "files": [
        {
            "path": "chat.json",
            "routed_to": "conversation-analyser",
            "result": {"critical_thinking": 62},
        }
    ]
}


def test_narrate_returns_empty_when_llm_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm, "get_api_key", lambda: None)
    note = alignment.narrate(
        CRITERION, [Evidence(signal="conversation.critical_thinking", value=62)], Coverage.PRESENT
    )
    assert note == ""


def test_narrate_uses_llm_complete(monkeypatch):
    captured = {}

    def fake_complete(prompt, *, system, model, max_tokens):
        captured.update(prompt=prompt, system=system, model=model)
        return "Pushback on 3 of 11 turns; sustained critical engagement with the model."

    monkeypatch.setattr(llm, "complete", fake_complete)
    evidence = [Evidence(signal="conversation.critical_thinking", value=62)]
    note = alignment.narrate(CRITERION, evidence, Coverage.PRESENT)

    assert note.startswith("Pushback")
    assert "conversation.critical_thinking" in captured["prompt"]
    assert "62" in captured["prompt"]
    assert "present" in captured["prompt"]
    # The system prompt carries the core invariant.
    assert "NEVER" in captured["system"] and "mark" in captured["system"]


def test_narrate_swallows_api_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulated API failure")

    monkeypatch.setattr(llm, "complete", boom)
    note = alignment.narrate(CRITERION, [], Coverage.ABSENT)
    assert note == ""


def test_observe_criterion_without_llm_flag_never_calls_llm(monkeypatch):
    def boom(*args, **kwargs):  # would fail the test if reached
        raise AssertionError("LLM called without --llm")

    monkeypatch.setattr(llm, "complete", boom)
    obs = alignment.observe_criterion(CRITERION, BUNDLE)
    assert obs.note == ""
    assert obs.coverage is not None


def test_observe_submission_threads_llm_flag(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a, **k: "A note bound to evidence.")
    rubric = Rubric(assignment="T", rubric=[CRITERION])
    observations = alignment.observe_submission(rubric, BUNDLE, llm=True)
    assert observations[0].note == "A note bound to evidence."


def test_render_evidence_truncates_huge_values():
    huge = Evidence(signal="document.everything", value={"blob": "x" * 5000})
    rendered = alignment._render_evidence([huge])
    assert "…(truncated)" in rendered
    assert len(rendered) < 1000


def test_narrate_model_env_override(monkeypatch):
    monkeypatch.setenv("ASSESSMENT_LENS_NARRATE_MODEL", "claude-sonnet-4-6")
    assert llm.narrate_model() == "claude-sonnet-4-6"
    monkeypatch.delenv("ASSESSMENT_LENS_NARRATE_MODEL")
    assert llm.narrate_model() == llm.DEFAULT_NARRATE_MODEL
