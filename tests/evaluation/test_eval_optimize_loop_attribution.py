"""Deterministic failure-attribution tests."""
from examples.optimization.eval_optimize_loop.loop_pipeline.attribution import attribute_case_failure
from examples.optimization.eval_optimize_loop.loop_pipeline.models import CaseEvaluationRecord, FailureCategory


def _case(**changes):
    values = {"case_id": "case", "passed": False, "aggregate_score": 0.0, "actual_response": "bad", "expected_response": "good"}
    values.update(changes)
    return CaseEvaluationRecord(**values)


def test_attributes_wrong_tool_name_before_final_response():
    reasons = attribute_case_failure(_case(expected_tool_calls=[{"name": "get_order"}], actual_tool_calls=[{"name": "search_refund_policy"}]))
    assert reasons[0].category == FailureCategory.WRONG_TOOL_CALL


def test_attributes_wrong_arguments_for_same_tool():
    reasons = attribute_case_failure(_case(expected_tool_calls=[{"name": "get_order", "args": {"order_id": "A100"}}], actual_tool_calls=[{"name": "get_order", "args": {"order_id": "A200"}}]))
    assert reasons[0].category == FailureCategory.WRONG_TOOL_ARGUMENTS


def test_attributes_format_violation():
    reasons = attribute_case_failure(_case(actual_response="prose", expected_response='{"order_id":"A100"}'))
    assert reasons[0].category == FailureCategory.FORMAT_VIOLATION
