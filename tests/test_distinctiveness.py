"""Cohort distinctiveness — pooling, multi-space comparison, neutral framing, degradation."""

from __future__ import annotations

import importlib.util

import pytest

from assessment_lens import distinctiveness as dn
from assessment_lens.models import (
    Distinctiveness,
    Evidence,
    Observation,
    SpaceDistinctiveness,
    SubmissionResult,
)

_HAVE = importlib.util.find_spec("numpy") is not None
_HAVE_LE = importlib.util.find_spec("lens_embed") is not None


def _bundle_with(*embeddings: list[float] | None) -> dict:
    """Fake bundle aggregate: one file-result per embedding (None = no embedding)."""
    results = []
    for emb in embeddings:
        res = {"routed_to": "x-analyser"}
        if emb is not None:
            res["embedding"] = emb
        results.append({"file": "f", "analyser": "x-analyser", "result": res, "error": None})
    return {"results": results}


def _sub(sid: str, **signals: float) -> SubmissionResult:
    """A submission carrying numeric evidence under one criterion, for the signal space."""
    obs = Observation(
        criterion_id="c1",
        evidence=[Evidence(signal=k, value=v) for k, v in signals.items()],
    )
    return SubmissionResult(submission_id=sid, observations=[obs])


# --- model shape -------------------------------------------------------------


def test_model_default_none_on_submission():
    assert "distinctiveness" in SubmissionResult.model_fields
    assert SubmissionResult.model_fields["distinctiveness"].default is None


def test_distinctiveness_space_lookup():
    d = Distinctiveness(spaces=[SpaceDistinctiveness(space="text", nearest_submission_id="bob")])
    assert d.space("text").nearest_submission_id == "bob"
    assert d.space("signal") is None


# --- text-vector pooling -----------------------------------------------------


def test_no_embeddings_yields_no_vector():
    assert dn.submission_text_vector(_bundle_with(None, None)) is None
    assert dn.submission_text_vector({"results": []}) is None


def test_ignores_wrong_dim_embeddings():
    # A 512-d (image/CLIP) vector must not be pooled with text vectors.
    assert dn.submission_text_vector(_bundle_with([0.1] * 512)) is None


@pytest.mark.skipif(not _HAVE, reason="needs numpy")
def test_pools_text_embeddings():
    vec = dn.submission_text_vector(_bundle_with([1.0] + [0.0] * 383, [0.0, 1.0] + [0.0] * 382))
    assert isinstance(vec, list) and len(vec) == 384
    # mean of two orthogonal unit vectors, renormalised → both components ~0.707
    assert vec[0] == pytest.approx(0.7071, abs=1e-3)
    assert vec[1] == pytest.approx(0.7071, abs=1e-3)


# --- cohort annotation (text space) ------------------------------------------


@pytest.mark.skipif(not _HAVE_LE, reason="needs lens-embed")
def test_annotate_cohort_finds_nearest_neighbour():
    results = [SubmissionResult(submission_id=sid) for sid in ("alice", "bob", "carol")]
    vectors = {
        "alice": [1.0, 0.0, 0.0],
        "bob": [0.99, 0.14, 0.0],  # very close to alice
        "carol": [0.0, 0.0, 1.0],  # orthogonal to both
    }
    dn.annotate_cohort(results, vectors)
    by_id = {r.submission_id: r for r in results}

    a_text = by_id["alice"].distinctiveness.space("text")
    b_text = by_id["bob"].distinctiveness.space("text")
    c_text = by_id["carol"].distinctiveness.space("text")
    assert a_text.nearest_submission_id == "bob"
    assert b_text.nearest_submission_id == "alice"
    assert a_text.nearest_similarity > 0.98
    assert c_text.nearest_similarity < 0.2
    # framing is neutral — never an accusation
    assert "collusion" not in by_id["alice"].distinctiveness.note.lower()


@pytest.mark.skipif(not _HAVE_LE, reason="needs lens-embed")
def test_relative_flags_need_a_big_enough_cohort():
    # Below _MIN_FOR_RELATIVE submissions: report similarities, but no strong flags.
    results = [SubmissionResult(submission_id=sid) for sid in ("a", "b", "c")]
    vectors = {"a": [1.0, 0.0], "b": [0.99, 0.14], "c": [0.0, 1.0]}
    dn.annotate_cohort(results, vectors)
    for r in results:
        t = r.distinctiveness.space("text")
        assert t.stands_apart is False
        assert t.notably_similar is False


@pytest.mark.skipif(not _HAVE_LE, reason="needs lens-embed")
def test_relative_outlier_surfaces_in_a_large_cohort():
    # Five tightly-clustered submissions + one orthogonal outlier. The outlier
    # should stand apart; the cluster should not all trip.
    cluster = {
        "s1": [1.0, 0.0, 0.0],
        "s2": [0.98, 0.20, 0.0],
        "s3": [0.97, 0.24, 0.0],
        "s4": [0.99, 0.10, 0.0],
        "s5": [0.96, 0.28, 0.0],
    }
    vectors = {**cluster, "loner": [0.0, 0.0, 1.0]}
    results = [SubmissionResult(submission_id=sid) for sid in vectors]
    dn.annotate_cohort(results, vectors)
    by_id = {r.submission_id: r for r in results}

    assert by_id["loner"].distinctiveness.space("text").stands_apart is True
    assert "apart" in by_id["loner"].distinctiveness.note.lower()
    # the tight cluster shouldn't be flagged as standing apart
    assert all(not by_id[s].distinctiveness.space("text").stands_apart for s in cluster)


@pytest.mark.skipif(not _HAVE_LE, reason="needs lens-embed")
def test_annotate_cohort_signal_space():
    # No text vectors at all — distinctiveness still computes from numeric signals.
    results = [
        _sub("a", words=100.0, depth=0.9),
        _sub("b", words=105.0, depth=0.88),
        _sub("c", words=98.0, depth=0.91),
        _sub("d", words=500.0, depth=0.1),  # very different profile
    ]
    dn.annotate_cohort(results, {sid: None for sid in ("a", "b", "c", "d")})
    # every submission has a signal space, and no text space (no vectors)
    for r in results:
        assert r.distinctiveness is not None
        assert r.distinctiveness.space("signal") is not None
        assert r.distinctiveness.space("text") is None


@pytest.mark.skipif(not _HAVE_LE, reason="needs lens-embed")
def test_annotate_cohort_combined_space_when_both_present():
    results = [
        _sub("a", words=100.0),
        _sub("b", words=105.0),
        _sub("c", words=98.0),
    ]
    vectors = {"a": [1.0, 0.0], "b": [0.99, 0.14], "c": [0.0, 1.0]}
    dn.annotate_cohort(results, vectors)
    a = {r.submission_id: r for r in results}["a"].distinctiveness
    assert a.space("text") is not None
    assert a.space("signal") is not None
    assert a.space("combined") is not None


def test_annotate_cohort_noop_below_two_comparable():
    results = [SubmissionResult(submission_id="solo")]
    dn.annotate_cohort(results, {"solo": [1.0, 0.0]})
    assert results[0].distinctiveness is None


def test_annotate_cohort_skips_submissions_without_vectors():
    results = [SubmissionResult(submission_id=s) for s in ("a", "b")]
    dn.annotate_cohort(results, {"a": None, "b": None})
    assert all(r.distinctiveness is None for r in results)
