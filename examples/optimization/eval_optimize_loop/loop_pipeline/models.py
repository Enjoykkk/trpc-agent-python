"""Stable, serializable models used by the optimization pipeline."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects accidental report/config schema drift."""

    model_config = ConfigDict(extra="forbid")


class ExecutionMode(str, Enum):
    FAKE = "fake"
    TRACE = "trace"
    REAL = "real"


class FailureCategory(str, Enum):
    EXECUTION_ERROR = "execution_error"
    WRONG_TOOL_CALL = "wrong_tool_call"
    WRONG_TOOL_ARGUMENTS = "wrong_tool_arguments"
    KNOWLEDGE_RECALL_INSUFFICIENT = "knowledge_recall_insufficient"
    FORMAT_VIOLATION = "format_violation"
    LLM_RUBRIC_FAILED = "llm_rubric_failed"
    FINAL_RESPONSE_MISMATCH = "final_response_mismatch"
    UNKNOWN_METRIC_FAILURE = "unknown_metric_failure"


class CaseChange(str, Enum):
    NEWLY_PASSED = "newly_passed"
    NEWLY_FAILED = "newly_failed"
    SCORE_IMPROVED = "score_improved"
    SCORE_REGRESSED = "score_regressed"
    UNCHANGED = "unchanged"


class GateDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class MetricSpec(StrictModel):
    metric_name: str = Field(min_length=1)
    threshold: float = Field(ge=0.0, le=1.0)


class AcceptanceMetrics(StrictModel):
    metrics: list[MetricSpec] = Field(min_length=1)
    num_runs: int = Field(default=1, ge=1)


class FailureReason(StrictModel):
    category: FailureCategory
    message: str
    evidence: str = ""


class CaseEvaluationRecord(StrictModel):
    case_id: str
    passed: bool
    aggregate_score: float
    metric_scores: dict[str, float] = Field(default_factory=dict)
    actual_response: str = ""
    expected_response: str = ""
    actual_tool_calls: list[dict] = Field(default_factory=list)
    expected_tool_calls: list[dict] = Field(default_factory=list)
    failure_reasons: list[FailureReason] = Field(default_factory=list)


class DatasetEvaluationSummary(StrictModel):
    dataset_id: str
    cases: list[CaseEvaluationRecord]

    @property
    def average_score(self) -> float:
        return sum(item.aggregate_score for item in self.cases) / len(self.cases) if self.cases else 0.0

    @property
    def pass_rate(self) -> float:
        return sum(item.passed for item in self.cases) / len(self.cases) if self.cases else 0.0


class CaseDelta(StrictModel):
    case_id: str
    change: CaseChange
    score_delta: float
    baseline_passed: bool
    candidate_passed: bool


class GateRuleResult(StrictModel):
    name: str
    passed: bool
    reason: str


class GateResult(StrictModel):
    decision: GateDecision
    rules: list[GateRuleResult]
    reasons: list[str] = Field(default_factory=list)
