"""Command-line interface: `python -m evaluator <validate|run|report> ...`

Mirrors the suggested interface from the assignment README.
"""

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path

from .loader import ValidationError, load_cases
from .metrics import build_report
from .rules import evaluate_case


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        cases = load_cases(args.csv_path)
    except ValidationError as error:
        print(f"Validation failed:\n{error}", file=sys.stderr)
        return 1

    split_counts = Counter(c.split for c in cases)
    verdict_counts = Counter(c.gold_verdict for c in cases)

    print(f"OK: {len(cases)} cases loaded from {args.csv_path}")
    print(f"  split:   {dict(split_counts)}")
    print(f"  verdict: {dict(verdict_counts)}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        cases = load_cases(args.input)
    except ValidationError as error:
        print(f"Validation failed:\n{error}", file=sys.stderr)
        return 1

    if args.split:
        cases = [c for c in cases if c.split == args.split]
        if not cases:
            print(f"No cases found for split '{args.split}'", file=sys.stderr)
            return 1

    results = [evaluate_case(case.to_input()) for case in cases]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        json.dump([dataclasses.asdict(result) for result in results], stream, indent=2)

    print(f"Wrote {len(results)} predictions to {output_path}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    try:
        cases = load_cases(args.input)
    except ValidationError as error:
        print(f"Validation failed:\n{error}", file=sys.stderr)
        return 1

    try:
        with Path(args.predictions).open(encoding="utf-8") as stream:
            predictions = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read predictions file: {error}", file=sys.stderr)
        return 1

    cases_by_id = {case.case_id: case for case in cases}
    report_markdown = build_report(cases_by_id, predictions)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_markdown, encoding="utf-8")

    print(f"Wrote report to {output_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evaluator", description="AI agent response evaluator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate and summarize a CSV dataset")
    validate_parser.add_argument("csv_path")
    validate_parser.set_defaults(func=_cmd_validate)

    run_parser = subparsers.add_parser("run", help="Evaluate cases and write predictions")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--split", choices=["calibration", "test"], default=None)
    run_parser.add_argument("--output", required=True)
    run_parser.set_defaults(func=_cmd_run)

    report_parser = subparsers.add_parser("report", help="Compare predictions to gold labels")
    report_parser.add_argument("--input", required=True)
    report_parser.add_argument("--predictions", required=True)
    report_parser.add_argument("--output", required=True)
    report_parser.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
