"""Metrics for comparing evaluator predictions against gold labels. Stdlib only.

Documented dependency note: no external metrics library is used (no scikit-learn).
Accuracy, F1, confusion matrix, precision/recall, and MAE are small enough to
implement directly and verify by hand, which also makes them easy to defend.
"""

from collections import Counter

VERDICTS = ("PASS", "FAIL", "ESCALATE")


def accuracy(golds: list[str], preds: list[str]) -> float:
    if not golds:
        return 0.0
    return sum(g == p for g, p in zip(golds, preds)) / len(golds)


def confusion_matrix(golds: list[str], preds: list[str]) -> dict[str, dict[str, int]]:
    """Rows = gold verdict, columns = predicted verdict."""
    matrix = {gold: {pred: 0 for pred in VERDICTS} for gold in VERDICTS}
    for gold, pred in zip(golds, preds):
        matrix[gold][pred] += 1
    return matrix


def _precision_recall_f1(
    golds: list[str], preds: list[str], label: str
) -> tuple[float, float, float]:
    true_positive = sum(g == label and p == label for g, p in zip(golds, preds))
    false_positive = sum(g != label and p == label for g, p in zip(golds, preds))
    false_negative = sum(g == label and p != label for g, p in zip(golds, preds))
    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive)
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative)
        else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def macro_f1(golds: list[str], preds: list[str]) -> float:
    per_label_f1 = [_precision_recall_f1(golds, preds, label)[2] for label in VERDICTS]
    return sum(per_label_f1) / len(per_label_f1)


def policy_violation_precision_recall(
    golds: list[bool], preds: list[bool]
) -> tuple[float, float]:
    true_positive = sum(g and p for g, p in zip(golds, preds))
    false_positive = sum((not g) and p for g, p in zip(golds, preds))
    false_negative = sum(g and (not p) for g, p in zip(golds, preds))
    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive)
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative)
        else 0.0
    )
    return precision, recall


def mean_absolute_error(golds: list[int], preds: list[int]) -> float:
    if not golds:
        return 0.0
    return sum(abs(g - p) for g, p in zip(golds, preds)) / len(golds)


def build_report(cases_by_id: dict, predictions: list[dict]) -> str:
    """Build the Markdown evaluation report for the README's required metrics."""
    matched = [
        (cases_by_id[p["case_id"]], p)
        for p in predictions
        if p["case_id"] in cases_by_id
    ]
    unmatched = [p for p in predictions if p["case_id"] not in cases_by_id]

    gold_verdicts = [case.gold_verdict for case, _ in matched]
    pred_verdicts = [pred["verdict"] for _, pred in matched]
    gold_policy = [case.gold_policy_violation for case, _ in matched]
    pred_policy = [pred["policy_violation"] for _, pred in matched]
    gold_quality = [case.gold_quality for case, _ in matched]
    pred_quality = [pred["quality_score"] for _, pred in matched]

    acc = accuracy(gold_verdicts, pred_verdicts)
    f1 = macro_f1(gold_verdicts, pred_verdicts)
    matrix = confusion_matrix(gold_verdicts, pred_verdicts)
    policy_precision, policy_recall = policy_violation_precision_recall(
        gold_policy, pred_policy
    )
    quality_mae = mean_absolute_error(gold_quality, pred_quality)

    errors = [
        (case, pred)
        for case, pred in matched
        if pred["verdict"] != case.gold_verdict
        or pred["policy_violation"] != case.gold_policy_violation
    ]

    lines = ["# Evaluation Report", ""]
    lines += [
        "## Summary",
        "",
        f"- Total predictions: {len(predictions)}",
        f"- Successfully matched to a known case: {len(matched)}",
        f"- Unmatched (case_id not found in input): {len(unmatched)}",
        "",
        "## Verdict metrics",
        "",
        f"- Accuracy: {acc:.2%}",
        f"- Macro F1 (PASS/FAIL/ESCALATE): {f1:.3f}",
        "",
        "### Confusion matrix (rows = gold, columns = predicted)",
        "",
        "| gold \\ pred | " + " | ".join(VERDICTS) + " |",
        "| --- | " + " | ".join("---" for _ in VERDICTS) + " |",
    ]
    for gold_label in VERDICTS:
        row = [str(matrix[gold_label][pred_label]) for pred_label in VERDICTS]
        lines.append(f"| {gold_label} | " + " | ".join(row) + " |")

    lines += [
        "",
        "## Policy violation metrics",
        "",
        f"- Precision: {policy_precision:.2%}",
        f"- Recall: {policy_recall:.2%}",
        "",
        "## Quality score metrics",
        "",
        f"- Mean absolute error: {quality_mae:.3f}",
        "",
        "## Error examples",
        "",
    ]
    if not errors:
        lines.append("No mismatches between predictions and gold labels.")
    else:
        for case, pred in errors[:5]:
            lines.append(
                f"**{case.case_id}** — predicted `{pred['verdict']}`, gold `{case.gold_verdict}`"
            )
            lines.append(f"  - Evaluator reason: {pred['reason']}")
            lines.append(f"  - Gold rationale: {case.gold_rationale}")
            lines.append("")

    return "\n".join(lines) + "\n"
