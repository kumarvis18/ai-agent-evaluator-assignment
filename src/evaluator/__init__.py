"""Deterministic, rule-based evaluation of AI agent responses, plus CSV loading."""

from .loader import ValidationError, load_cases
from .models import Case, EvaluationInput, EvaluationResult
from .rules import evaluate_case

__all__ = ["load_cases", "ValidationError", "Case", "EvaluationInput", "EvaluationResult", "evaluate_case"]
