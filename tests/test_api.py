"""HTTP API plumbing — the assess engine is stubbed; these test the contract a UI relies on."""

from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi", reason="needs the [serve] extra")
pytest.importorskip("lens_contract", reason="needs the [serve] extra")

from fastapi.testclient import TestClient  # noqa: E402  (guarded by importorskip above)

from assessment_lens import api  # noqa: E402
from assessment_lens.models import AssessmentResult, SubmissionResult  # noqa: E402


def _wait(client: TestClient, run_id: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/assessments/{run_id}").json()
        if status["status"] in ("done", "failed"):
            return status
        time.sleep(0.02)
    raise AssertionError("run did not finish in time")


def test_health_and_manifest():
    client = TestClient(api.app)
    assert client.get("/health").status_code == 200
    manifest = client.get("/manifest").json()
    assert manifest["name"] == "assessment-lens"
    assert manifest["role"] == "lens"


def test_assess_run_end_to_end(monkeypatch):
    # Stub the engine: no analyser stack, no rubric on disk.
    result = AssessmentResult(assignment="t", submissions=[SubmissionResult(submission_id="alice")])
    monkeypatch.setattr(api, "load_rubric", lambda _p: object())

    def fake_assess(_rubric, _subs, *, only=None, llm=False, progress=None):
        if progress:
            progress("assessing alice (1/1)")
        return result

    monkeypatch.setattr(api, "assess", fake_assess)

    client = TestClient(api.app)
    started = client.post("/assessments", json={"rubric": "r.yaml", "submissions": "subs"})
    assert started.status_code == 202
    run_id = started.json()["id"]

    status = _wait(client, run_id)
    assert status["status"] == "done"
    assert status["name"] == "r"
    assert any("assessing alice" in line for line in status["progress"])

    got = client.get(f"/assessments/{run_id}/result")
    assert got.status_code == 200
    assert got.json()["submissions"][0]["submission_id"] == "alice"

    # the run shows up in the list
    assert run_id in {r["id"] for r in client.get("/assessments").json()}


def test_unknown_run_404():
    client = TestClient(api.app)
    assert client.get("/assessments/nope").status_code == 404
    assert client.get("/assessments/nope/result").status_code == 404


def test_failed_run_surfaces_error(monkeypatch):
    monkeypatch.setattr(api, "load_rubric", lambda _p: object())

    def boom(*_a, **_k):
        raise RuntimeError("bad rubric")

    monkeypatch.setattr(api, "assess", boom)

    client = TestClient(api.app)
    run_id = client.post("/assessments", json={"rubric": "r.yaml", "submissions": "subs"}).json()[
        "id"
    ]
    status = _wait(client, run_id)
    assert status["status"] == "failed"
    assert "bad rubric" in status["error"]
    assert client.get(f"/assessments/{run_id}/result").status_code == 500
