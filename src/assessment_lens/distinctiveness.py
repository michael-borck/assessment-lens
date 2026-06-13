"""Cohort-relative distinctiveness — how each submission compares to the others.

A **neutral, direction-agnostic** observation for a human to interpret, **never**
a collusion/plagiarism verdict and never a quality judgement. Standing apart can
mean an out-of-the-box answer or a thin one; distinctiveness doesn't decide which
— the per-criterion observations carry the quality signal, and the marker reads
both.

Three comparison spaces, each a cosine similarity:
  - **text**   — pooled artefact embeddings the analysers already produced
                 (Phase 2): *how* the submission is written/said.
  - **signal** — z-normalised numeric signal values: its metric profile.
  - **combined** — the mean of the two (where both exist).

Flags are **relative to the cohort's own distribution** (z-scores), not absolute
thresholds — so a tightly-clustered cohort (a prescriptive or weak task) doesn't
trip everyone, and a genuine outlier still surfaces. Relative flags need a cohort
big enough for the distribution to mean something; below that we report the raw
similarities without strong flags.

assessment-lens is a pure *consumer* here — only lens-embed's numpy core is
needed for the maths. Degradable: no lens-embed, or no embeddings/signals →
distinctiveness is simply left empty.
"""

from __future__ import annotations

from typing import Any

from .models import Distinctiveness, SpaceDistinctiveness, SubmissionResult

_TEXT_DIM = 384  # the family's pinned text model (all-MiniLM-L6-v2)
_MIN_FOR_RELATIVE = 5  # below this the cohort distribution is too small for z-flags
_Z_APART = 1.5  # mean-similarity this many SDs BELOW cohort → "stands apart"
_Z_CLOSE = 2.0  # nearest-similarity this many SDs ABOVE cohort → "notably similar"


# --- text space: reuse the analysers' embeddings -----------------------------


def submission_text_vector(bundle_result: dict[str, Any]) -> list[float] | None:
    """Mean-pool a submission's text-modality artefact embeddings into one vector."""
    embs = [
        res["embedding"]
        for fr in bundle_result.get("results", [])
        if isinstance(fr, dict)
        and isinstance((res := fr.get("result")), dict)
        and isinstance(res.get("embedding"), list)
        and len(res["embedding"]) == _TEXT_DIM
    ]
    if not embs:
        return None
    try:
        import numpy as np
    except ImportError:
        return None
    mean = np.asarray(embs, dtype=np.float64).mean(axis=0)
    norm = np.linalg.norm(mean)
    if norm:
        mean = mean / norm
    return mean.tolist()


# --- signal space: z-normalised numeric signal values ------------------------


def _numeric_signals(result: SubmissionResult) -> dict[str, float]:
    """Numeric evidence values for one submission, keyed by criterion:signal."""
    out: dict[str, float] = {}
    for obs in result.observations:
        for e in obs.evidence:
            if isinstance(e.value, (int, float)) and not isinstance(e.value, bool):
                out[f"{obs.criterion_id}:{e.signal}"] = float(e.value)
    return out


def _signal_vectors(results: list[SubmissionResult]) -> dict[str, list[float]]:
    """Per-submission z-normalised numeric-signal vectors (only submissions with signals)."""
    try:
        import numpy as np
    except ImportError:
        return {}
    maps = {r.submission_id: _numeric_signals(r) for r in results}
    maps = {sid: m for sid, m in maps.items() if m}  # need at least one numeric signal
    features = sorted({k for m in maps.values() for k in m})
    if len(maps) < 2 or not features:
        return {}
    ids = list(maps)
    # impute missing features with the column mean so a missing signal reads as
    # "typical", not as an extreme.
    col_means = {
        f: (lambda vals: sum(vals) / len(vals) if vals else 0.0)(
            [maps[i][f] for i in ids if f in maps[i]]
        )
        for f in features
    }
    mat = np.array(
        [[maps[i].get(f, col_means[f]) for f in features] for i in ids], dtype=np.float64
    )
    mu = mat.mean(axis=0)
    sd = mat.std(axis=0)
    sd[sd == 0] = 1.0  # a constant signal carries no distinguishing information
    z = (mat - mu) / sd
    return {ids[k]: z[k].tolist() for k in range(len(ids))}


# --- generic pairwise analysis over a similarity function --------------------


def _analyse_space(
    space: str, ids: list[str], sim: dict[frozenset, float]
) -> dict[str, SpaceDistinctiveness]:
    """Per-submission nearest/mean + RELATIVE outlier flags for one space."""
    if len(ids) < 2:
        return {}
    nearest: dict[str, tuple[str, float]] = {}
    mean_sim: dict[str, float] = {}
    for a in ids:
        pairs = [(b, sim[frozenset((a, b))]) for b in ids if b != a]
        pairs.sort(key=lambda p: p[1], reverse=True)
        nearest[a] = pairs[0]
        mean_sim[a] = sum(s for _, s in pairs) / len(pairs)

    relative = len(ids) >= _MIN_FOR_RELATIVE
    apart_cut = close_cut = None
    if relative:
        import numpy as np

        means = np.array(list(mean_sim.values()))
        nears = np.array([n[1] for n in nearest.values()])
        apart_cut = means.mean() - _Z_APART * (means.std() or 1.0)
        close_cut = nears.mean() + _Z_CLOSE * (nears.std() or 1.0)

    out: dict[str, SpaceDistinctiveness] = {}
    for a in ids:
        nid, nsim = nearest[a]
        out[a] = SpaceDistinctiveness(
            space=space,
            nearest_submission_id=nid,
            nearest_similarity=round(nsim, 4),
            mean_similarity=round(mean_sim[a], 4),
            stands_apart=bool(relative and mean_sim[a] < apart_cut),
            notably_similar=bool(relative and nsim > close_cut),
        )
    return out


def _pairwise(vectors: dict[str, list[float]], cosine) -> tuple[list[str], dict[frozenset, float]]:
    ids = list(vectors)
    sim: dict[frozenset, float] = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            sim[frozenset((ids[i], ids[j]))] = cosine(vectors[ids[i]], vectors[ids[j]])
    return ids, sim


def _note(spaces: list[SpaceDistinctiveness]) -> str:
    apart = [s.space for s in spaces if s.stands_apart]
    close = [s for s in spaces if s.notably_similar]
    parts: list[str] = []
    if apart:
        parts.append(
            f"Stands apart from the cohort ({', '.join(apart)}) — distinctive, "
            "for better or worse; read the criteria to see why."
        )
    if close:
        c = close[0]
        parts.append(
            f"Unusually close to '{c.nearest_submission_id}' ({c.space}) — worth a look, not a verdict."
        )
    if not parts:
        parts.append("Typical of the cohort.")
    return " ".join(parts)


def annotate_cohort(
    results: list[SubmissionResult],
    text_vectors: dict[str, list[float] | None],
) -> None:
    """Attach per-space Distinctiveness to each comparable submission.

    No-op (leaves distinctiveness None) if lens-embed is absent or no space has
    ≥2 comparable submissions.
    """
    try:
        from lens_embed import cosine_similarity
    except ImportError:
        return

    spaces: dict[str, dict[str, SpaceDistinctiveness]] = {}

    # text space
    tvecs = {sid: v for sid, v in text_vectors.items() if v is not None}
    if len(tvecs) >= 2:
        ids, sim = _pairwise(tvecs, cosine_similarity)
        spaces["text"] = _analyse_space("text", ids, sim)

    # signal space
    svecs = _signal_vectors(results)
    sim_signal: dict[frozenset, float] = {}
    if len(svecs) >= 2:
        ids, sim_signal = _pairwise(svecs, cosine_similarity)
        spaces["signal"] = _analyse_space("signal", ids, sim_signal)

    # combined space: mean of text + signal similarity for pairs present in both
    tvec_sim: dict[frozenset, float] = {}
    if len(tvecs) >= 2:
        _, tvec_sim = _pairwise(tvecs, cosine_similarity)
    common = [sid for sid in (set(tvecs) & set(svecs))]
    if len(common) >= 2:
        combined_sim = {
            key: (tvec_sim[key] + sim_signal[key]) / 2
            for i in range(len(common))
            for j in range(i + 1, len(common))
            if (key := frozenset((common[i], common[j]))) in tvec_sim and key in sim_signal
        }
        if combined_sim:
            spaces["combined"] = _analyse_space("combined", common, combined_sim)

    if not spaces:
        return

    for sr in results:
        per_space = [s[sr.submission_id] for s in spaces.values() if sr.submission_id in s]
        if per_space:
            sr.distinctiveness = Distinctiveness(spaces=per_space, note=_note(per_space))
