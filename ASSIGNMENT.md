# Junior Engineering Assignment: AI Agent Response Evaluator

## Overview

Build a small application that evaluates the quality and safety of an AI agent's work. The evaluator receives an agent task, the constraints it was expected to follow, its tool-use trajectory, and its final answer. It must return a verdict and a short explanation.

This assignment is designed for a junior software or AI engineer. We are looking for clear reasoning, reliable data handling, sensible tests, and readable code. A simple, well-explained solution is better than an unnecessarily complex one.

**Suggested effort:** 4–6 hours  
**Recommended language:** Python or TypeScript  
**Submission format:** Git repository or ZIP file

## Use case

An operations team runs AI agents across workflows such as customer support, finance, travel, healthcare, and IT operations. Before an agent action is trusted, the team needs an automated evaluator that answers four questions:

1. Did the agent complete the requested task?
2. Did it follow the stated constraints and authority limits?
3. Did it use tools and evidence appropriately?
4. Should the result pass, fail, or be escalated to a human?

Your application will evaluate historical examples and produce a consistent result for each case.

## Expected outcome

The completed solution should:

- Load and validate the supplied CSV data.
- Extract the agent trajectory and final answer from `state_json` when the corresponding top-level columns are empty.
- Evaluate each case and return:
  - `verdict`: `PASS`, `FAIL`, or `ESCALATE`
  - `quality_score`: integer from `0` to `4`
  - `policy_violation`: `true` or `false`
  - `reason`: a concise human-readable explanation
- Process a complete CSV file in batch mode.
- Generate a summary containing record counts, verdict distribution, accuracy, macro F1 score, and a confusion matrix.
- Include automated tests for important parsing and evaluation behavior.
- Explain the approach and trade-offs in the submission README.

A command-line application is sufficient. A REST API or user interface is optional.

## Datasets

All supplied data is synthetic and does not represent real customers, accounts, transactions, or people.

### 1. `datasets/ai_agent_evaluator_benchmark.csv`

This is the primary dataset and contains 48 labeled examples:

- 12 calibration records and 36 test records
- 16 `PASS`, 16 `FAIL`, and 16 `ESCALATE` outcomes
- 16 easy, 16 medium, and 16 hard examples
- 8 capabilities with 6 examples each

The capabilities are groundedness, human oversight, instruction following, privacy and safety, prompt injection, recovery efficiency, tool selection, and transaction correctness.

Important fields:

| Field | Description |
| --- | --- |
| `case_id` | Unique case identifier |
| `split` | `calibration` or `test` |
| `capability` | Primary behavior being evaluated |
| `domain` | Business domain for the scenario |
| `difficulty` | `easy`, `medium`, or `hard` |
| `task` | Work the agent was asked to perform |
| `constraints` | Rules, limits, or required output format |
| `available_tools` | Tools the agent was allowed to use |
| `state_json` | Nested source data containing the trajectory and final answer |
| `gold_verdict` | Expected verdict used for scoring |
| `gold_quality` | Expected quality score from 0 to 4 |
| `gold_policy_violation` | Expected policy-violation flag |
| `gold_rationale` | Reference explanation for the label |
| `trap` | Main failure mode represented by the case |

The top-level `agent_trajectory` and `agent_final_answer` fields are intentionally empty. Read those values from `state_json` as part of normalization.

### 2. `datasets/judge_framework_calibration.csv`

This optional extension dataset contains 8 labeled claim-evaluation examples. Labels are balanced across `present`, `partial`, `missing`, and `contradicted`.

### 3. `datasets/judge_framework_holdout.csv`

This optional extension dataset contains 8 unseen claim-evaluation examples with the same balanced label set. Use the calibration file to develop the extension and the holdout file only for final evaluation.

For both extension datasets, `Metadata` is a JSON string. It contains the candidate `response`, supporting `context`, expected `benchmark_label`, and explanatory notes.

## Required work

### 1. Data loading and validation

Create a loader that:

- Reads the primary CSV without losing quoted text or JSON content.
- Verifies that `case_id` is present and unique.
- Parses `state_json` and reports malformed JSON clearly.
- Confirms that verdict, quality, and policy labels use allowed values.
- Produces normalized records for the evaluator.

Do not silently skip invalid rows.

### 2. Evaluation logic

Implement an evaluator using one of these approaches:

- Deterministic rules and keyword checks
- A lightweight statistical or machine-learning model
- An LLM-based evaluator, if you already have access to an API
- A documented combination of the above

The application must run without exposing API keys in the repository. If an external model is optional, provide a local fallback or clear instructions for running the data and test pipeline without it.

Use only the 12 `calibration` records while developing or tuning the evaluator. Treat `gold_*`, `gold_rationale`, and `trap` as labels. They must not be included in the input used to predict a verdict. Run against the 36 `test` records only after the approach is fixed.

### 3. Batch output

Write one result per input case to CSV or JSON. Each output record should follow this shape:

```json
{
  "case_id": "AE-001",
  "verdict": "PASS",
  "quality_score": 4,
  "policy_violation": false,
  "reason": "The response follows the requested format and stays within the stated constraints."
}
```

Keep `reason` short and tie it to evidence in the task, constraints, trajectory, or final answer.

### 4. Evaluation report

For the `test` split, report:

- Total evaluated, successful, and failed records
- Accuracy for `verdict`
- Macro F1 score across `PASS`, `FAIL`, and `ESCALATE`
- Confusion matrix
- Precision and recall for `policy_violation`
- Mean absolute error for `quality_score`
- At least three error examples with a brief explanation

You may use a standard metrics library or implement the calculations yourself. Document any dependency you add.

### 5. Tests

Include automated tests for at least the following:

- A valid row is normalized correctly from `state_json`.
- Malformed JSON returns a clear validation error.
- Duplicate `case_id` values are rejected.
- A straightforward passing case receives `PASS`.
- A clear policy or authority breach does not receive `PASS`.
- Batch output preserves the input `case_id`.

## Deliverables

Submit:

1. Source code.
2. Dependency file such as `requirements.txt`, `pyproject.toml`, or `package.json`.
3. Instructions to install and run the solution.
4. Automated tests and the command used to run them.
5. Generated predictions for the 36 test records.
6. Evaluation report in Markdown, JSON, or HTML.
7. A short note describing assumptions, limitations, and what you would improve next.

Do not commit credentials, local virtual environments, dependency folders, or generated caches.

## Suggested interface

The exact command names are up to you. A submission may expose commands similar to:

```bash
# Validate and summarize the data
python -m evaluator validate datasets/ai_agent_evaluator_benchmark.csv

# Evaluate the test split and write predictions
python -m evaluator run \
  --input datasets/ai_agent_evaluator_benchmark.csv \
  --split test \
  --output outputs/predictions.json

# Compare predictions with the labels and create a report
python -m evaluator report \
  --input datasets/ai_agent_evaluator_benchmark.csv \
  --predictions outputs/predictions.json \
  --output outputs/report.md
```

Equivalent TypeScript commands are acceptable.

## Acceptance criteria

A valid submission must:

- Run from a clean environment using the documented commands.
- Parse all 48 primary records successfully.
- Keep gold labels out of evaluator inputs.
- Produce exactly one result for every selected input row.
- Return only the allowed verdicts and quality scores.
- Calculate the requested metrics correctly.
- Pass its automated tests.
- Handle errors with useful messages instead of crashing silently.

There is no required model accuracy threshold. We will assess whether the approach is appropriate for the assignment level, implemented correctly, evaluated honestly, and explained clearly.

## Review rubric

| Area | Weight |
| --- | ---: |
| Data loading, normalization, and validation | 20% |
| Evaluation logic and evidence-based reasoning | 25% |
| Metrics and error analysis | 20% |
| Tests and reliability | 20% |
| Code quality and documentation | 15% |

## Optional extension

Use `judge_framework_calibration.csv` and `judge_framework_holdout.csv` to add a second evaluation mode that labels an individual claim as `present`, `partial`, `missing`, or `contradicted`.

If you attempt this extension:

- Develop only against the calibration file.
- Evaluate once against the holdout file.
- Report accuracy and a confusion matrix.
- Explain how the logic distinguishes an omitted qualifier (`partial`) from an absent claim (`missing`) and an opposing claim (`contradicted`).

The optional extension should not reduce the quality of the required solution.
