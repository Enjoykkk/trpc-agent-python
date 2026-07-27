"""Gate decision matrix smoke tests."""
from examples.optimization.eval_optimize_loop.loop_pipeline.config import GateConfig
from examples.optimization.eval_optimize_loop.loop_pipeline.gates import evaluate_gate
from examples.optimization.eval_optimize_loop.loop_pipeline.models import CaseChange, CaseDelta, CaseEvaluationRecord, DatasetEvaluationSummary, GateDecision


def _set(score): return DatasetEvaluationSummary(dataset_id="x", cases=[CaseEvaluationRecord(case_id="val_critical_refund", passed=score == 1, aggregate_score=score)])
def _config(): return GateConfig(min_validation_score_gain=.05, min_validation_pass_rate_gain=0, max_single_metric_regression=0, protected_case_ids=["val_critical_refund"], max_cost_usd=1, max_duration_seconds=180)


def test_gate_accepts_validation_improvement_without_regression():
    result = evaluate_gate(_config(), _set(0), _set(0), _set(1), _set(1), [CaseDelta(case_id="val_critical_refund", change=CaseChange.NEWLY_PASSED, score_delta=1, baseline_passed=False, candidate_passed=True)])
    assert result.decision == GateDecision.ACCEPT


def test_gate_rejects_protected_case_regression():
    result = evaluate_gate(_config(), _set(1), _set(1), _set(1), _set(0), [CaseDelta(case_id="val_critical_refund", change=CaseChange.NEWLY_FAILED, score_delta=-1, baseline_passed=True, candidate_passed=False)])
    assert result.decision == GateDecision.REJECT
    assert result.reasons
