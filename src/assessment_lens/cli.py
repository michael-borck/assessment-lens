"""CLI entry point for assessment-lens.

A lens is a *consumer*, not a routable analyser. Core commands: `assess`
(rubric + folder -> observations) and `draft-rubric` (free-form spec ->
proposed rubric). It also offers an opt-in `serve` (HTTP API behind the
`[serve]` extra) so a desktop shell / UI can drive it — same `/health` +
`/manifest` contract as the analysers, but it still never scores.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="assessment-lens",
        description=(
            "Signals-based assessment: map analyser signals to a rubric as observations, "
            "never grades. A human assigns every mark."
        ),
    )
    parser.add_argument("--version", action="version", version=f"assessment-lens {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_assess = sub.add_parser(
        "assess",
        help="Assess a folder of submissions against a structured rubric.",
    )
    p_assess.add_argument("rubric", help="Path to a structured rubric (.yaml/.json).")
    p_assess.add_argument("submissions", help="Folder containing one subfolder per submission.")
    p_assess.add_argument(
        "-o", "--out", default="assessment-out", help="Output dir for sheet + reports."
    )
    p_assess.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        help="Restrict to these submission ids (subfolder names).",
    )
    p_assess.add_argument(
        "--llm",
        action="store_true",
        help=(
            "Narrate each observation with an LLM (narrate-and-cite; never scores). "
            "Needs the [llm] extra + ANTHROPIC_API_KEY; off by default."
        ),
    )
    p_assess.set_defaults(func=_cmd_assess)

    p_draft = sub.add_parser(
        "draft-rubric",
        help="Propose a structured rubric from a free-form specification (review before use).",
    )
    p_draft.add_argument("spec", help="Path to the free-form specification.")
    p_draft.add_argument("-o", "--out", help="Where to write the proposed rubric (.yaml).")
    p_draft.set_defaults(func=_cmd_draft_rubric)

    p_serve = sub.add_parser(
        "serve",
        help="Run the HTTP API (for the desktop shell / UIs). Needs the [serve] extra.",
    )
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8021)
    p_serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


def _cmd_serve(args: argparse.Namespace) -> int:
    from rich.console import Console

    console = Console(stderr=True)
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]serve needs the [serve] extra:[/red] pip install 'assessment-lens[serve]'"
        )
        return 1
    uvicorn.run("assessment_lens.api:app", host=args.host, port=args.port)
    return 0


def _cmd_assess(args: argparse.Namespace) -> int:
    from rich.console import Console

    from .assess import assess
    from .exceptions import AssessmentLensError
    from .report import write_reports
    from .rubric import load_rubric

    console = Console(stderr=True)
    use_llm = args.llm
    if use_llm:
        from . import llm

        if not llm.available():
            console.print(
                "[yellow]LLM narration unavailable[/yellow] (missing [llm] extra or "
                "ANTHROPIC_API_KEY) — continuing with deterministic observations only."
            )
            use_llm = False
    try:
        rubric = load_rubric(args.rubric)
        console.print(
            f"[bold]{rubric.assignment}[/bold]"
            + (f" ({rubric.component})" if rubric.component else "")
            + f" — {len(rubric.rubric)} criteria, {len(rubric.expected_deliverables)} deliverables"
        )
        result = assess(rubric, args.submissions, only=args.only, llm=use_llm)
        out = write_reports(result, args.out)
    except AssessmentLensError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    console.print(
        f"[green]✓[/green] {len(result.submissions)} submissions assessed → "
        f"[bold]{out}/cohort-sheet.csv[/bold] + per-student reports in [bold]{out}/reports/[/bold]"
    )
    return 0


def _cmd_draft_rubric(args: argparse.Namespace) -> int:
    import yaml
    from rich.console import Console

    from .draft_rubric import DraftRubricUnavailable, draft_rubric
    from .exceptions import AssessmentLensError

    console = Console(stderr=True)
    try:
        proposal = draft_rubric(args.spec)
    except DraftRubricUnavailable as exc:
        console.print(
            f"[yellow]draft-rubric needs the LLM path:[/yellow] {exc}\n"
            "For now you can author the rubric by hand — see examples/."
        )
        return 2
    except AssessmentLensError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    rendered = yaml.safe_dump(
        proposal.model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
    )
    header = (
        "# PROPOSED rubric — drafted by assessment-lens from your specification.\n"
        "# Review and edit before use; the tool never assigns marks and neither should this file.\n"
    )
    if args.out:
        from pathlib import Path

        Path(args.out).write_text(header + rendered, encoding="utf-8")
        console.print(
            f"[green]✓[/green] Proposed rubric written to [bold]{args.out}[/bold] — review before use."
        )
    else:
        print(header + rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
