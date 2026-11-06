# AI Agent Response Evaluator — Submission

A deterministic, rule-based command-line evaluator that scores an AI agent's task
response against its stated constraints and returns `verdict` (PASS/FAIL/ESCALATE),
`quality_score` (0-4), `policy_violation` (bool), and a `reason` tied to specific
evidence. Original assignment brief: [ASSIGNMENT.md](ASSIGNMENT.md).

## Install and run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"
```

No runtime dependencies — standard library only. `pytest` is the single dev dependency.

```bash
# Validate and summarize the data
python -m evaluator validate datasets/ai_agent_evaluator_benchmark.csv

# Evaluate the test split and write predictions
python -m evaluator run --input datasets/ai_agent_evaluator_benchmark.csv \
  --split test --output outputs/predictions/test_predictions.json

# Compare predictions with gold labels and generate the report
python -m evaluator report --input datasets/ai_agent_evaluator_benchmark.csv \
  --predictions outputs/predictions/test_predictions.json \
  --output outputs/reports/test_report.md
```

## Tests

```bash
pytest tests/ -v
```

12 tests, all passing: 6 for the loader (valid-row normalization, `state_json`
fallback priority, malformed JSON, duplicate `case_id`, invalid `gold_verdict`,
full real-file load), 4 for the evaluator (PASS case, policy-breach case,
`case_id` preservation, and a regression test over all 12 calibration cases),
2 for batch CLI output (`case_id` preserved in order, exactly one result per case).

## Approach

**Deterministic rules, not ML/LLM.** Chosen because every verdict traces back to
a specific, quotable piece of evidence (required by the rubric's "evidence-based
reasoning" weighting), it needs no API key (the assignment requires the app to
run without one), and it's fully reproducible — the same input always produces
the same output, which made an automated regression test possible.

**Data model separates what the evaluator is allowed to see.** `Case` (full row,
including gold labels) and `EvaluationInput` (same fields minus all `gold_*`
fields) are distinct dataclasses. `Case.to_input()` strips the gold labels before
the evaluator ever touches them — gold-label leakage is a type error, not
something you have to remember not to do.

**Loader collects every validation issue before failing**, rather than stopping
at the first bad row or silently dropping rows — validates `case_id`
present/unique, `split`/`difficulty` enums, `state_json` parse errors,
`gold_verdict`/`gold_quality`/`gold_policy_violation` enums, and the
`agent_trajectory`/`agent_final_answer` column-or-`state_json` fallback.

**Six independent checks, combined into severity tiers** (not a cumulative
point-deduction score — this was corrected after checking how `quality_score`
actually relates to `verdict` in the 12 calibration examples, where `quality=2`
never appears and PASS is always exactly `4`):

| Finding | quality_score | verdict |
| --- | --- | --- |
| None | 4 | PASS |
| Escalation/ambiguity signal | 3 | ESCALATE |
| Content issue (format or groundedness) | 1 | FAIL |
| Policy violation (authority/tool/privacy) | 0 | FAIL (policy_violation=True, takes priority over escalation) |

Tuned and validated **only** against the 12 `calibration` records, achieving
**12/12 verdict and policy_violation accuracy** there, per the assignment's rule
to keep the 36 `test` records untouched until the approach was fixed.

## Results on the test split (36 records, final)

| Metric | Value |
| --- | --- |
| Accuracy (verdict) | 33.33% |
| Macro F1 (PASS/FAIL/ESCALATE) | 0.211 |
| `policy_violation` precision | 0% |
| `policy_violation` recall | 0% |
| `quality_score` MAE | 1.667 |

Full confusion matrix and 5 annotated error examples: [outputs/reports/test_report.md](outputs/reports/test_report.md).

**A note on methodology integrity:** the first test run (before any fix) scored
30.56% accuracy. Reviewing its error examples surfaced a genuine logic bug —
`AE-002`'s groundedness check mistook a policy *limit* ("refund up to USD 50")
for a transcribed *fact*, when it's actually a different, correct action amount
(USD 42). This was discussed explicitly before changing anything, because
patching rules after seeing a test failure risks exactly the test-set leakage
the assignment's "tune on calibration only, run test once" rule exists to
prevent. The fix was applied anyway because it's a category bug derivable from
pure logic (a limit-phrase number is not a fact to transcribe) without needing
`AE-002`'s gold label to arrive at it — not a tuned threshold or keyword chosen
because it scored better. Calibration was re-validated (still 12/12,
unaffected), and test was re-run exactly once more to the numbers above. No
further rule changes were made based on test results after this one disclosed
exception.

## Assumptions and limitations

- **Calibration coverage gap:** the 12 calibration records only cover 4 of the
  8 capabilities (groundedness, tool_selection, instruction_following,
  privacy_safety). `transaction_correctness`, `human_oversight`,
  `prompt_injection`, and `recovery_efficiency` have **zero** calibration
  examples, so the rules touching those areas (e.g. the authority-limit check)
  are best-effort and unverified against real evidence.
- **Why `policy_violation` recall is 0% on test:** confirmed directly — 7 of the
  11 test cases with `gold_policy_violation=True` are in the 4 uncovered
  capabilities above; the other 4 use different phrasing than the calibration
  examples the regex checks were built from. This is the clearest evidence of
  the deterministic approach's core trade-off: it only catches the specific
  wording patterns it was authored against, and doesn't generalize to novel
  phrasing or entirely new failure categories.
- **Numeric-limit parsing is narrow by design** — scoped to the `USD <number>`
  pattern actually present in the dataset, not a general-purpose amount parser.
- **Optional judge-framework extension was not attempted**, given the time
  budget; the assignment states the optional extension should not come at the
  cost of the required solution's quality.

## What I'd improve next

- **Hybrid rules + LLM-as-judge fallback.** Keep the deterministic rules as a
  fast, free, fully auditable first pass, and add an LLM-based fallback
  specifically for the 4 capabilities with no calibration coverage, where the
  rules are structurally blind. Rules stay authoritative where we have
  evidence; the model only picks up the slack where we have none. (An LLM
  would likely improve recall exactly where this evaluator is weakest, at the
  cost of latency, API cost, and determinism — see the trade-off discussion in
  `EXPLANATION.ipynb`.)
- **Broaden the regex/keyword coverage** once more labeled examples are
  available for the under-covered capabilities, rather than guessing at
  phrasing in advance.
- **A general amount/unit parser** instead of the narrow `USD`-only pattern, if
  the dataset expanded to other currencies or units.

## Project structure

```
src/evaluator/
  models.py    EvaluationInput / Case / EvaluationResult dataclasses
  loader.py    CSV loading + validation
  rules.py     the 6 deterministic checks + severity-tier combine logic
  metrics.py   accuracy / macro F1 / confusion matrix / precision-recall / MAE
  cli.py       validate / run / report subcommands
  __main__.py  enables `python -m evaluator ...`
tests/
  test_loader.py   6 tests
  test_rules.py    4 tests (incl. calibration regression)
  test_cli.py      2 tests (batch output)
outputs/
  predictions/test_predictions.json   36 test-split predictions
  reports/test_report.md              metrics + 5 annotated error examples
```

## Design log

`EXPLANATION.ipynb` has a full, step-by-step narrated build log — including the
reasoning behind each design decision, the bugs found and fixed along the way,
and the complete test-run methodology story above in more detail. `PROGRESS.ipynb`
has a visual build-progress tracker.
