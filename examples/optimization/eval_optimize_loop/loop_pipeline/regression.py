"""Case-id based regression comparisons."""
from .models import CaseChange, CaseDelta, DatasetEvaluationSummary


def compare_cases(baseline: DatasetEvaluationSummary, candidate: DatasetEvaluationSummary) -> list[CaseDelta]:
    left = {item.case_id: item for item in baseline.cases}
    right = {item.case_id: item for item in candidate.cases}
    if set(left) != set(right):
        raise ValueError("baseline and candidate case IDs differ")
    result = []
    for case_id, before in left.items():
        after = right[case_id]
        delta = after.aggregate_score - before.aggregate_score
        if not before.passed and after.passed: change = CaseChange.NEWLY_PASSED
        elif before.passed and not after.passed: change = CaseChange.NEWLY_FAILED
        elif delta > 1e-9: change = CaseChange.SCORE_IMPROVED
        elif delta < -1e-9: change = CaseChange.SCORE_REGRESSED
        else: change = CaseChange.UNCHANGED
        result.append(CaseDelta(case_id=case_id, change=change, score_delta=delta, baseline_passed=before.passed, candidate_passed=after.passed))
    return result
