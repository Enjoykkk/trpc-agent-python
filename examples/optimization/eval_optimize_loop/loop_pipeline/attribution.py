"""Deterministic failure explanations."""
from .models import CaseEvaluationRecord, FailureCategory, FailureReason


def attribute_case_failure(case: CaseEvaluationRecord) -> list[FailureReason]:
    if case.passed:
        return []
    if case.actual_tool_calls != case.expected_tool_calls:
        expected_names = [item.get("name") for item in case.expected_tool_calls]
        actual_names = [item.get("name") for item in case.actual_tool_calls]
        category = FailureCategory.WRONG_TOOL_CALL if expected_names != actual_names else FailureCategory.WRONG_TOOL_ARGUMENTS
        return [FailureReason(category=category, message="工具调用与期望不一致", evidence=f"expected={expected_names}; actual={actual_names}")]
    if case.actual_response.startswith("{") != case.expected_response.startswith("{"):
        return [FailureReason(category=FailureCategory.FORMAT_VIOLATION, message="输出格式不符合要求")]
    return [FailureReason(category=FailureCategory.FINAL_RESPONSE_MISMATCH, message="最终回复未满足期望")]
