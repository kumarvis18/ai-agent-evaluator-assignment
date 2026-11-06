"""CSV loading and validation for the AI agent evaluator benchmark.

Design choice: we collect *every* row-level problem before failing, instead of
stopping at the first bad row. That way a malformed CSV never silently loses
rows, and a single run tells you everything that needs fixing.
"""

import csv
import json
from pathlib import Path

from .models import (
    ALLOWED_DIFFICULTIES,
    ALLOWED_QUALITY_SCORES,
    ALLOWED_SPLITS,
    ALLOWED_VERDICTS,
    BenchmarkCase,
)


class ValidationError(Exception):
    """Raised when one or more rows fail validation. Carries every issue found."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        summary = f"{len(issues)} validation issue(s) found:\n" + "\n".join(
            f"  - {issue}" for issue in issues
        )
        super().__init__(summary)


class _RowError(Exception):
    """Internal: a single row failed to parse. Message is human-readable."""


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    """Read and validate the benchmark CSV, returning fully normalized BenchmarkCase objects.

    Raises ValidationError (with every issue listed) if any row is invalid or
    any case_id is duplicated. Never returns a partial/silently-filtered list.
    """
    rows = _read_csv(path)

    issues: list[str] = []
    seen_ids: set[str] = set()
    cases: list[BenchmarkCase] = []

    for row_number, row in enumerate(rows, start=2):  # header is line 1
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            issues.append(f"Row {row_number}: missing case_id")
            continue
        if case_id in seen_ids:
            issues.append(f"Row {row_number}: duplicate case_id '{case_id}'")
            continue

        try:
            case = _parse_row(row_number, case_id, row)
        except _RowError as error:
            issues.append(str(error))
            continue

        seen_ids.add(case_id)
        cases.append(case)

    if issues:
        raise ValidationError(issues)

    return cases


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    # utf-8-sig quietly strips a BOM if present; Excel-exported CSVs often have one.
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _parse_row(row_number: int, case_id: str, row: dict[str, str]) -> BenchmarkCase:
    split = (row.get("split") or "").strip()
    if split not in ALLOWED_SPLITS:
        raise _RowError(
            f"Row {row_number} ({case_id}): split must be one of {sorted(ALLOWED_SPLITS)}, got '{split}'"
        )

    difficulty = (row.get("difficulty") or "").strip()
    if difficulty not in ALLOWED_DIFFICULTIES:
        raise _RowError(
            f"Row {row_number} ({case_id}): difficulty must be one of {sorted(ALLOWED_DIFFICULTIES)}, got '{difficulty}'"
        )

    state = _parse_state_json(row_number, case_id, row.get("state_json") or "")

    agent_trajectory = (row.get("agent_trajectory") or "").strip() or str(
        state.get("agent_trajectory") or ""
    ).strip()
    if not agent_trajectory:
        raise _RowError(
            f"Row {row_number} ({case_id}): agent_trajectory missing from both the column and state_json"
        )

    agent_final_answer = (row.get("agent_final_answer") or "").strip() or str(
        state.get("agent_final_answer") or ""
    ).strip()
    if not agent_final_answer:
        raise _RowError(
            f"Row {row_number} ({case_id}): agent_final_answer missing from both the column and state_json"
        )

    available_tools = _parse_tools(row.get("available_tools") or "")

    gold_verdict = (row.get("gold_verdict") or "").strip().upper()
    if gold_verdict not in ALLOWED_VERDICTS:
        raise _RowError(
            f"Row {row_number} ({case_id}): gold_verdict must be one of {sorted(ALLOWED_VERDICTS)}, got '{gold_verdict}'"
        )

    gold_quality = _parse_quality(row_number, case_id, row.get("gold_quality") or "")
    gold_policy_violation = _parse_bool(
        row_number,
        case_id,
        "gold_policy_violation",
        row.get("gold_policy_violation") or "",
    )

    return BenchmarkCase(
        case_id=case_id,
        split=split,
        capability=(row.get("capability") or "").strip(),
        domain=(row.get("domain") or "").strip(),
        difficulty=difficulty,
        task=(row.get("task") or "").strip(),
        constraints=(row.get("constraints") or "").strip(),
        available_tools=available_tools,
        agent_trajectory=agent_trajectory,
        agent_final_answer=agent_final_answer,
        gold_verdict=gold_verdict,
        gold_quality=gold_quality,
        gold_policy_violation=gold_policy_violation,
        gold_rationale=(row.get("gold_rationale") or "").strip(),
        trap=(row.get("trap") or "").strip(),
    )


def _parse_state_json(row_number: int, case_id: str, raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise _RowError(
            f"Row {row_number} ({case_id}): malformed state_json ({error.msg} at position {error.pos})"
        ) from error


def _parse_tools(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw or raw.lower() == "none":
        return []
    return [tool.strip() for tool in raw.split(",") if tool.strip()]


def _parse_quality(row_number: int, case_id: str, raw: str) -> int:
    try:
        value = int(raw.strip())
    except ValueError as error:
        raise _RowError(
            f"Row {row_number} ({case_id}): gold_quality must be an integer, got '{raw}'"
        ) from error
    if value not in ALLOWED_QUALITY_SCORES:
        raise _RowError(
            f"Row {row_number} ({case_id}): gold_quality must be 0-4, got {value}"
        )
    return value


def _parse_bool(row_number: int, case_id: str, field_name: str, raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in ("true", "false"):
        return normalized == "true"
    raise _RowError(
        f"Row {row_number} ({case_id}): {field_name} must be true/false, got '{raw}'"
    )
