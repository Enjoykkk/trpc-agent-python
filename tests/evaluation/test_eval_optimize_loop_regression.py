"""Case-id regression comparison tests."""
import pytest
from examples.optimization.eval_optimize_loop.loop_pipeline.models import CaseChange, CaseEvaluationRecord, DatasetEvaluationSummary
from examples.optimization.eval_optimize_loop.loop_pipeline.regression import compare_cases


def _summary(*records): return DatasetEvaluationSummary(dataset_id="set", cases=list(records))
def _record(case_id, passed, score): return CaseEvaluationRecord(case_id=case_id, passed=passed, aggregate_score=score)


def test_compare_cases_uses_case_id_not_order():
    deltas = compare_cases(_summary(_record("a", False, 0), _record("b", True, 1)), _summary(_record("b", True, 1), _record("a", True, 1)))
    assert {item.case_id: item.change for item in deltas}["a"] == CaseChange.NEWLY_PASSED


def test_compare_cases_rejects_mismatched_sets():
    with pytest.raises(ValueError, match="case IDs"):
        compare_cases(_summary(_record("a", False, 0)), _summary(_record("b", False, 0)))
