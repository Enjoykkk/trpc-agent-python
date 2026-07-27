"""Unified evaluation adapter for offline and SDK-backed execution."""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from trpc_agent_sdk.evaluation import AgentEvaluator, EvalConfig, EvalSet

from .attribution import attribute_case_failure
from .models import CaseEvaluationRecord, DatasetEvaluationSummary, ExecutionMode


async def evaluate_with_call_agent(dataset_path: Path, call_agent: Callable[[str], Awaitable[str]]) -> DatasetEvaluationSummary:
    """Evaluate response-based data through the SDK and normalize each case."""
    eval_set = EvalSet.model_validate_json(dataset_path.read_text(encoding="utf-8"))
    config = EvalConfig(criteria={"final_response_avg_score": 1.0})
    _, _, _, raw = await AgentEvaluator.evaluate_eval_set(
        eval_set, call_agent=call_agent, eval_config=config, print_detailed_results=False,
    )
    cases = []
    for case in eval_set.eval_cases:
        invocation = case.conversation[-1]
        expected = invocation.final_response.parts[0].text if invocation.final_response else ""
        result = raw[case.eval_id]
        actual = ""
        if getattr(result, "actual_final_response", None):
            actual = result.actual_final_response.parts[0].text or ""
        passed = bool(getattr(result, "passed", actual == expected))
        record = CaseEvaluationRecord(case_id=case.eval_id, passed=passed, aggregate_score=1.0 if passed else 0.0,
                                      metric_scores={"final_response_avg_score": 1.0 if passed else 0.0}, actual_response=actual, expected_response=expected)
        record.failure_reasons = attribute_case_failure(record)
        cases.append(record)
    return DatasetEvaluationSummary(dataset_id=eval_set.eval_set_id, cases=cases)


async def evaluate_dataset(dataset_path: Path, mode: ExecutionMode, call_agent: Callable[[str], Awaitable[str]] | None = None) -> DatasetEvaluationSummary:
    """Route real execution through SDK; trace/fake callers supply their adapter upstream."""
    if mode == ExecutionMode.REAL:
        if call_agent is None:
            raise ValueError("real evaluation requires an async call_agent")
        return await evaluate_with_call_agent(dataset_path, call_agent)
    raise ValueError(f"{mode.value} evaluation is handled by the deterministic pipeline adapter")
