import json
from pathlib import Path

import pytest

from evaluator.loader import ValidationError, load_cases

HEADER = (
    "case_id,split,capability,domain,difficulty,language,task,constraints,available_tools,"
    "agent_trajectory,agent_final_answer,gold_verdict,gold_quality,gold_policy_violation,"
    "gold_rationale,trap,state_json"
)


def _row(**overrides) -> str:
    """Build one CSV data row from sensible defaults, overriding only what a test needs."""
    state = {
        "agent_trajectory": "The agent did the thing.",
        "agent_final_answer": "Done.",
    }
    defaults = {
        "case_id": "AE-900",
        "split": "calibration",
        "capability": "instruction_following",
        "domain": "customer_support",
        "difficulty": "easy",
        "language": "en",
        "task": "Do the thing.",
        "constraints": "No constraints.",
        "available_tools": "none",
        "agent_trajectory": "",
        "agent_final_answer": "",
        "gold_verdict": "PASS",
        "gold_quality": "4",
        "gold_policy_violation": "false",
        "gold_rationale": "Looks fine.",
        "trap": "none",
        "state_json": json.dumps(state),
    }
    defaults.update(overrides)
    fields = HEADER.split(",")
    values = [defaults[f] for f in fields]
    # json.dumps already produced valid CSV-unsafe characters (quotes/commas); quote every field.
    escaped = [v.replace('"', '""') for v in values]
    return ",".join(f'"{v}"' for v in escaped)


def _write_csv(tmp_path: Path, rows: list[str]) -> Path:
    csv_path = tmp_path / "cases.csv"
    csv_path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return csv_path


def test_valid_row_is_normalized_from_state_json(tmp_path):
    csv_path = _write_csv(tmp_path, [_row()])

    cases = load_cases(csv_path)

    assert len(cases) == 1
    case = cases[0]
    assert case.case_id == "AE-900"
    assert case.agent_trajectory == "The agent did the thing."
    assert case.agent_final_answer == "Done."
    assert case.gold_quality == 4
    assert case.gold_policy_violation is False
    assert case.available_tools == []


def test_top_level_columns_take_priority_over_state_json(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                agent_trajectory="top-level trajectory",
                agent_final_answer="top-level answer",
            )
        ],
    )

    cases = load_cases(csv_path)

    assert cases[0].agent_trajectory == "top-level trajectory"
    assert cases[0].agent_final_answer == "top-level answer"


def test_malformed_json_raises_clear_validation_error(tmp_path):
    csv_path = _write_csv(tmp_path, [_row(state_json="{not valid json")])

    with pytest.raises(ValidationError) as excinfo:
        load_cases(csv_path)

    assert "malformed state_json" in str(excinfo.value)


def test_duplicate_case_id_is_rejected(tmp_path):
    csv_path = _write_csv(tmp_path, [_row(case_id="AE-900"), _row(case_id="AE-900")])

    with pytest.raises(ValidationError) as excinfo:
        load_cases(csv_path)

    assert "duplicate case_id" in str(excinfo.value)


def test_invalid_gold_verdict_is_rejected(tmp_path):
    csv_path = _write_csv(tmp_path, [_row(gold_verdict="MAYBE")])

    with pytest.raises(ValidationError) as excinfo:
        load_cases(csv_path)

    assert "gold_verdict" in str(excinfo.value)


def test_real_benchmark_file_loads_all_48_rows():
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / "datasets" / "ai_agent_evaluator_benchmark.csv"

    cases = load_cases(csv_path)

    assert len(cases) == 48
    assert sum(c.split == "calibration" for c in cases) == 12
    assert sum(c.split == "test" for c in cases) == 36
