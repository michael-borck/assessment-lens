"""CLI entry point for assessment-lens.

A lens is a consumer, not an analyser — so there is no `serve`/`manifest`
contract here. Two commands matter: `assess` (rubric + folder -> observations)
and `draft-rubric` (free-form spec -> proposed rubric; near-term).
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
    p_assess.set_defaults(func=_cmd_assess)

    p_draft = sub.add_parser(
        "draft-rubric",
        help="Propose a structured rubric from a free-form specification (near-term).",
    )
    p_draft.add_argument("spec", help="Path to the free-form specification.")
    p_draft.add_argument("-o", "--out", help="Where to write the proposed rubric (.yaml).")
    p_draft.set_defaults(func=_cmd_draft_rubric)

    args = parser.parse_args(argv)
    return args.func(args)


def _cmd_assess(args: argparse.Namespace) -> int:
    from rich.console import Console

    from .assess import assess
    from .exceptions import AssessmentLensError
    from .report import write_reports
    from .rubric import load_rubric

    console = Console(stderr=True)
    try:
        rubric = load_rubric(args.rubric)
        console.print(
            f"[bold]{rubric.assignment}[/bold]"
            + (f" ({rubric.component})" if rubric.component else "")
            + f" — {len(rubric.rubric)} criteria, {len(rubric.expected_deliverables)} deliverables"
        )
        result = assess(rubric, args.submissions, only=args.only)
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
    from rich.console import Console

    console = Console(stderr=True)
    try:
        from .draft_rubric import draft_rubric

        draft_rubric(args.spec)
    except NotImplementedError as exc:
        console.print(f"[yellow]Not yet available:[/yellow] {exc}")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
