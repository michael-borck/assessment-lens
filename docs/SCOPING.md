# Scoping

The canonical scope for `assessment-lens` lives with the family architecture docs:

- **Scope & design** — `lens-analysers/docs/ASSESSMENT-LENS-SCOPING.md`
  (glossary, pipeline, the two commands, rubric + observation schemas,
  composition, principles, MVP boundary, harvest map).
- **Why a lens, not an analyser** —
  `lens-analysers/docs/adr/0001-alignment-lives-in-assessment-lens.md`.
- **Signals it consumes** — `lens-analysers/docs/SIGNAL-CATALOGUE.md`.

## The one-paragraph version

Tools generate signals about student submissions; this lens maps those signals
to a rubric as **observations, not grades**. The lecturer reads them, weighs
them, and assigns the mark. The AI **narrates and cites; it never scores** — a
human stays in the loop. `assess` is folder-dumb: one rubric + one folder of
submission subfolders, `bundle-analyser` once per subfolder, then
`alignment-check` turns signals into evidence-bound observations with
threshold-derived coverage.

## Build state vs scope

The deterministic spine (rubric → discover → reconcile deliverables → gather
evidence → coverage → reports) is implemented. The two pieces still to land:

1. **LLM narration** (`alignment.narrate`) — the only LLM-touched field
   (`Observation.note`); arrives with the `[llm]` extra.
2. **`draft-rubric`** — free-form spec → proposed rubric; harvest + adapt the
   rubric/key code from `video-analyser` @ `b3ae7e19`.

> Reminder recorded in family memory: `video-analyser` 0.10.0 (grading removed)
> is on `main` but **held from PyPI** until this lens reborns the grading, so
> users get a migration path.
