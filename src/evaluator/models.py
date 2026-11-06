"""Data structures shared across the loader, evaluator, and reporting code."""

from dataclasses import dataclass

ALLOWED_SPLITS = {"calibration", "test"}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_VERDICTS = {"PASS", "FAIL", "ESCALATE"}
ALLOWED_QUALITY_SCORES = {0, 1, 2, 3, 4}


@dataclass(frozen=True)
class EvaluationInput:
    """Everything the evaluator is allowed to see. No gold/label fields here on purpose,
    so the evaluator cannot accidentally depend on the answer it is trying to predict."""

    case_id: str
    capability: str
    domain: str
    difficulty: str
    task: str
    constraints: str
    available_tools: list[str]
    agent_trajectory: str
    agent_final_answer: str


@dataclass(frozen=True)
class Case:
    """A fully validated and normalized dataset row, including gold labels used for scoring."""

    case_id: str
    split: str
    capability: str
    domain: str
    difficulty: str
    task: str
    constraints: str
    available_tools: list[str]
    agent_trajectory: str
    agent_final_answer: str
    gold_verdict: str
    gold_quality: int
    gold_policy_violation: bool
    gold_rationale: str
    trap: str

    def to_input(self) -> EvaluationInput:
        """Strip gold labels before handing the case to the evaluator."""
        return EvaluationInput(
            case_id=self.case_id,
            capability=self.capability,
            domain=self.domain,
            difficulty=self.difficulty,
            task=self.task,
            constraints=self.constraints,
            available_tools=self.available_tools,
            agent_trajectory=self.agent_trajectory,
            agent_final_answer=self.agent_final_answer,
        )


@dataclass(frozen=True)
class EvaluationResult:
    """One evaluator output record, matching the README's required output shape."""

    case_id: str
    verdict: str
    quality_score: int
    policy_violation: bool
    reason: str
