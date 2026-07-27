"""Configuration-driven candidate acceptance."""
from .config import GateConfig
from .models import CaseChange, DatasetEvaluationSummary, GateDecision, GateResult, GateRuleResult


def evaluate_gate(config: GateConfig, baseline_train: DatasetEvaluationSummary, baseline_val: DatasetEvaluationSummary, candidate_train: DatasetEvaluationSummary, candidate_val: DatasetEvaluationSummary, deltas, cost: float = 0.0, duration: float = 0.0) -> GateResult:
    rules = []
    gain = candidate_val.average_score - baseline_val.average_score
    rules.append(GateRuleResult(name="validation_score_gain", passed=gain >= config.min_validation_score_gain, reason=f"validation score delta={gain:.3f}"))
    new_hard = [d.case_id for d in deltas if d.change == CaseChange.NEWLY_FAILED]
    rules.append(GateRuleResult(name="no_new_hard_fail", passed=not new_hard or not config.forbid_new_hard_fail, reason=f"new failures={new_hard}"))
    protected = [d.case_id for d in deltas if d.case_id in config.protected_case_ids and d.change in {CaseChange.NEWLY_FAILED, CaseChange.SCORE_REGRESSED}]
    rules.append(GateRuleResult(name="protected_cases", passed=not protected, reason=f"protected regressions={protected}"))
    overfit = candidate_train.average_score > baseline_train.average_score and (candidate_val.average_score < baseline_val.average_score or candidate_val.pass_rate < baseline_val.pass_rate)
    rules.append(GateRuleResult(name="overfit_guard", passed=not config.overfit_guard or not overfit, reason=f"overfit={overfit}"))
    rules.append(GateRuleResult(name="cost", passed=cost <= config.max_cost_usd, reason=f"cost={cost}"))
    rules.append(GateRuleResult(name="duration", passed=duration <= config.max_duration_seconds, reason=f"duration={duration}"))
    failed = [rule.reason for rule in rules if not rule.passed]
    return GateResult(decision=GateDecision.ACCEPT if not failed else GateDecision.REJECT, rules=rules, reasons=failed)
