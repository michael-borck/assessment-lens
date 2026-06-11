# assessment-lens

Part of the [lens family](https://github.com/michael-borck/lens-analysers).

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Signals-based assessment.** Analysers generate signals about student
submissions; this lens maps those signals to a rubric as **observations, not
grades**. A lecturer reads the observations, weighs them, and assigns the mark.
The AI **narrates and cites; it never scores.** A human stays in the loop.

> `assessment-lens` is a **lens** (an assessment-aware product), not an
> `-analyser`. Analysers are assessment-agnostic signal generators; lenses sit
> above them. It *consumes* analysers (via `bundle-analyser`); it never generates
> signals. See [ADR-0001](https://github.com/michael-borck/lens-analysers/blob/main/docs/adr/0001-alignment-lives-in-assessment-lens.md).

## Why "observations, not grades"

LLMs are inconsistent at the precise act of *marking*. So the lens keeps them off
it. The deterministic signals (from analysers) are the anchor; an **Observation**
maps a signal or two to a rubric **Criterion** with **cited evidence**, a short
**narration bound to that evidence**, and a **coverage** (`present` / `partial` /
`absent`) — which is *"is the evidence there?"*, derived from thresholds, **not a
mark**. There is deliberately no score/mark/weight field anywhere in the model.

## Pipeline

```
Specification ──draft-rubric (LLM, reviewed)──▶ Rubric (criteria + mapping) + deliverables  [YAML]
Submissions root ──discover──▶ one Submission per subfolder
each Submission folder ──bundle-analyser──▶ Signals
Signals + Criteria + Deliverables ──alignment-check──▶ Observations
                                                         └─▶ cohort triage sheet + per-student reports
lecturer reads observations → assigns marks → writes feedback
```

`assess` is **folder-dumb**: one rubric + one folder of submission subfolders.
Group/individual splits and mark-combining are handled outside (pre/post) or by
running `assess` per folder.

## Two commands

- **`assess`** — structured rubric + a submissions folder → observations (cohort
  sheet + per-student reports). Add `--llm` for evidence-bound narration on each
  observation (opt-in; needs the `[llm]` extra + `ANTHROPIC_API_KEY`).
- **`draft-rubric`** — free-form specification → a *proposed* structured rubric
  for the lecturer to **review/edit before use**. LLM-assisted; reads text/markdown
  directly and `.pdf`/`.docx`/`.pptx` via the `[documents]` extra.

## Install

```bash
# from source (family layout)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# pull the whole analyser stack into the same env (for `assess` to run for real):
uv pip install -e ".[dev,analysers]"

# opt-in LLM features (narration + draft-rubric):
uv pip install -e ".[llm]"     # + export ANTHROPIC_API_KEY=...
```

`assess` shells out to the `bundle-analyser` CLI (it must be on `PATH`). The
`[analysers]` extra installs it; or point `assessment-lens` at an environment
where it is already installed.

## Quick start

```bash
# 1. author a structured rubric (or start from the example)
cp examples/data-viz-rubric.yaml my-rubric.yaml

# 2. lay out submissions: one subfolder per student/group
#    submissions/alice/{report.pdf,demo.mp4}  submissions/bob/...

# 3. assess (add --llm for narrated observations)
assessment-lens assess my-rubric.yaml submissions/ -o out/
#    -> out/cohort-sheet.csv         (row per submission × criterion, sortable)
#    -> out/reports/<id>.md          (per-student observation sheet, no marks)

# or draft a rubric from a free-form spec, then review/edit it
assessment-lens draft-rubric assignment-brief.md -o my-rubric.yaml
```

## Rubric schema (the central contract)

```yaml
assignment: "Data-Viz Project"
component: individual                 # plain label; assess ignores it
expected_deliverables:
  - id: report
    description: "Written report (~2000 words)"
    accepts: [document]               # content kinds that satisfy it
  - id: demo
    description: "≤5-min recorded demo"
    accepts: [video]
rubric:
  - id: critical-thinking
    description: "Evidence of critical engagement / analysis"
    signals_of_interest: [conversation.critical_thinking, reflection.depth]  # OPTIONAL mapping
```

`signals_of_interest` is the **signal→criterion mapping**, and it's **optional**.
Pinned → deterministic coverage. Blank → `alignment-check` selects signals at
runtime and shows its choice (near-term).

## Status

**v0.2.** Working today:

- ✅ Rubric load/validate; deliverable reconciliation; submission discovery
- ✅ `assess` orchestration + evidence-bound observations + threshold coverage
- ✅ cohort sheet (CSV) + per-student reports (Markdown)
- ✅ `bundle-analyser` integration — verified against the real CLI output schema
- ✅ LLM narration (`assess --llm`) — narrate-and-cite, bound to evidence; degrades
  to empty notes when the `[llm]` extra/key is missing
- ✅ `draft-rubric` — proposes a rubric from a free-form spec (always review before use)
- 📋 Runtime signal selection when `signals_of_interest` is blank — deferred

## Development

```bash
ruff format . && ruff check . && pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
