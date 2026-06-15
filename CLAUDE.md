# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

`assessment-lens` is a **lens** — an assessment-aware *product*, not an
`-analyser`. Analysers are assessment-agnostic signal generators; lenses sit
above them and consume their signals. This one maps signals to a rubric as
**observations, not grades**. The core invariant, enforced in the models:

> **The LLM narrates and cites; it never scores.** There is no score/mark/grade/
> weight field anywhere in `models.py`. A human assigns every mark. If you ever
> find yourself adding one, stop — that belongs to the lecturer, not the lens.

It's a CLI consumer that composes **only `bundle-analyser`** (one call per
submission subfolder). It does **not** route by file type (no `auto_routable`),
but it *does* now offer an **opt-in HTTP face** (`serve`, behind the `[serve]`
extra) so a desktop shell / UI can drive it — same `/health` + `/manifest`
contract as the analysers, `role: lens`. The invariant still holds across every
surface: it never scores.

## Architecture

```
cli.py          → argparse: `assess`, `draft-rubric`, `serve`
rubric.py       → load/validate the structured rubric (YAML/JSON) + ext→content-kind
assess.py       → orchestration: discover submissions, reconcile deliverables, run pipeline (+ optional progress hook)
bundle.py       → subprocess wrapper over the bundle-analyser CLI + signal-path resolver
alignment.py    → alignment-check: signals → Observations (evidence + threshold coverage); LLM `narrate` opt-in via --llm
llm.py          → Anthropic plumbing (key resolution, model defaults, `complete`); everything degradable
distinctiveness.py → cohort-relative distinctiveness (three spaces; neutral, never a verdict)
report.py       → cohort sheet (CSV) + per-student reports (Markdown)
draft_rubric.py → free-form spec → proposed rubric (LLM-assisted; lecturer reviews before use)
manifest.py     → MANIFEST (role: lens) for the /manifest contract route   [serve]
api.py          → FastAPI app: POST /assessments + poll progress + GET result [serve]
models.py       → the central contract (Rubric/Criterion/Deliverable, Observation/Coverage)
```

The `bundle.run_bundle` / `bundle.get_signal` integration is pinned to
bundle-analyser's real output schema (verified against the live CLI) — re-verify
if bundle-analyser's aggregate shape changes.

## Toolchain (family standard — run before committing)

```bash
ruff format . && ruff check . && pytest -v
```

`uv` for env/packaging, `pyproject.toml` only. Tests mirror `src/`.

## Provenance

Scoping lives in `lens-analysers/docs/ASSESSMENT-LENS-SCOPING.md` and
[ADR-0001](https://github.com/michael-borck/lens-analysers/blob/main/docs/adr/0001-alignment-lives-in-assessment-lens.md).
The rubric/storage/LLM-key code is being harvested+adapted from `video-analyser`
@ `b3ae7e19` (pre-grading-removal) — see `draft_rubric.py` and the scoping doc's
harvest map. Adapt, don't copy: the old code *scored*; this lens *narrates*.
