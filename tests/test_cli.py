import csv
import json
from pathlib import Path

from evaluator.cli import main

HEADER = (
    "case_id,split,capability,domain,difficulty,language,task,constraints,available_tools,"
    "agent_trajectory,agent_final_answer,gold_verdict,gold_quality,gold_policy_violation,"
    "gold_rationale,trap,state_json"
)


def _write_csv(tmp_path: Path, case_ids: list[str]) -> Path:
    """Write a small CSV with one distinct, valid row per given case_id."""
    csv_path = tmp_path / "cases.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADER.split(","))
        for case_id in case_ids:
            writer.writerow(
                [
                    case_id,
                    "test",
                    "instruction_following",
                    "customer_support",
                    "easy",
                    "en",
                    "Do the thing.",
                    "No constraints.",
                    "none",
                    "The agent did the thing.",
                    "Done.",
                    "PASS",
                    "4",
                    "false",
                    "Looks fine.",
                    "none",
                    "{}",
                ]
            )
    return csv_path


def test_batch_run_preserves_case_ids_in_order(tmp_path):
    case_ids = ["AE-901", "AE-902", "AE-903"]
    csv_path = _write_csv(tmp_path, case_ids)
    output_path = tmp_path / "predictions.json"

    exit_code = main(["run", "--input", str(csv_path), "--output", str(output_path)])

    assert exit_code == 0
    predictions = json.loads(output_path.read_text(encoding="utf-8"))
    assert [p["case_id"] for p in predictions] == case_ids


def test_batch_run_produces_exactly_one_result_per_case(tmp_path):
    case_ids = [f"AE-{i}" for i in range(5)]
    csv_path = _write_csv(tmp_path, case_ids)
    output_path = tmp_path / "predictions.json"

    main(["run", "--input", str(csv_path), "--output", str(output_path)])

    predictions = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(predictions) == len(case_ids)
    assert len(set(p["case_id"] for p in predictions)) == len(case_ids)
