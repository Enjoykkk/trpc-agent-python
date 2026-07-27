"""CLI entry point for fake, trace, and real evaluation optimization runs."""
from __future__ import annotations
import argparse, asyncio, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from loop_pipeline.attribution import attribute_case_failure
from loop_pipeline.config import load_pipeline_config
from loop_pipeline.gates import evaluate_gate
from loop_pipeline.models import CaseEvaluationRecord, DatasetEvaluationSummary, ExecutionMode
from loop_pipeline.regression import compare_cases
from loop_pipeline.report import write_reports
from loop_pipeline.runtime_config import load_real_mode_environment
from agent.agent import read_instruction
from agent.fake_models import invoke_fake_agent

def _fake_candidate(prompt: str, scenario: str) -> str:
    if scenario == "improve":
        return prompt.replace("guess_when_missing", "strict").replace("refund_policy_mode = optional", "refund_policy_mode = required").replace("json_output_mode = prose", "json_output_mode = strict_json")
    if scenario == "overfit":
        return prompt.replace("guess_when_missing", "strict").replace("refund_policy_mode = optional", "refund_policy_mode = required").replace("json_output_mode = prose", "json_output_mode = strict_json") + "\n<!-- overfit: completed orders can always refund -->"
    return prompt


async def _fake_summary(path: Path, phase: str, scenario: str) -> DatasetEvaluationSummary:
    payload=json.loads(path.read_text(encoding="utf-8")); prompt=read_instruction()
    if phase == "candidate": prompt=_fake_candidate(prompt, scenario)
    records=[]
    for item in payload["eval_cases"]:
        case_id=item["eval_id"]; invocation=item["conversation"][0]; query=invocation["user_content"]["parts"][0]["text"]; expected=invocation["final_response"]["parts"][0]["text"]
        result=await invoke_fake_agent(query, prompt)
        passed = ({"train_order_status": "已发货" in result.response, "train_refund_policy": bool(result.tool_calls), "train_json_output": result.response.startswith("{"), "val_generalize_order_id": "已完成" in result.response, "val_missing_order_id": "请提供订单号" in result.response, "val_critical_refund": "不支持无条件退款" in result.response}[case_id])
        if scenario == "overfit" and phase == "candidate" and case_id.startswith("val_"):
            passed=False
        record=CaseEvaluationRecord(case_id=case_id, passed=passed, aggregate_score=float(passed), metric_scores={"final_response_avg_score": float(passed)}, actual_response=result.response, expected_response=expected, actual_tool_calls=result.tool_calls)
        record.failure_reasons=attribute_case_failure(record); records.append(record)
    return DatasetEvaluationSummary(dataset_id=path.stem, cases=records)


def _summary(path: Path, phase: str, scenario: str, trace_path: Path | None = None) -> DatasetEvaluationSummary:
    payload = json.loads(path.read_text(encoding="utf-8")); records=[]
    trace_actual = {}
    if trace_path is not None:
        for trace_case in json.loads(trace_path.read_text(encoding="utf-8"))["eval_cases"]:
            conversation = trace_case.get("actual_conversation") or []
            if conversation:
                parts = conversation[-1].get("final_response", {}).get("parts", [])
                trace_actual[trace_case["eval_id"]] = parts[0].get("text", "") if parts else ""
    for item in payload["eval_cases"]:
        case_id=item["eval_id"]; expected=item["conversation"][0]["final_response"]["parts"][0]["text"]
        good = phase == "candidate" and scenario == "improve"
        if scenario == "no_effect": good=False
        if scenario == "overfit": good = (phase == "candidate" and "train_" in case_id) or (phase == "baseline" and case_id == "val_critical_refund")
        actual = trace_actual.get(case_id, expected if good else "无法确认")
        if trace_path is not None:
            good = actual == expected
        record=CaseEvaluationRecord(case_id=case_id, passed=good, aggregate_score=1.0 if good else 0.0, metric_scores={"final_response_avg_score": 1.0 if good else 0.0}, actual_response=actual, expected_response=expected)
        record.failure_reasons=attribute_case_failure(record); records.append(record)
    return DatasetEvaluationSummary(dataset_id=path.stem, cases=records)


async def run_pipeline(args) -> dict:
    if args.apply and args.mode != ExecutionMode.REAL.value:
        raise ValueError("--apply is allowed only in real mode")
    if args.mode == ExecutionMode.REAL.value:
        load_real_mode_environment(HERE / "agent" / ".env", HERE / "loop_pipeline" / ".env")
    config=load_pipeline_config(HERE / "pipeline.json"); start=time.monotonic()
    trace_baseline = HERE / "data" / "trace_baseline.evalset.json" if args.mode == ExecutionMode.TRACE.value else None
    trace_candidate = HERE / "data" / "trace_candidate.evalset.json" if args.mode == ExecutionMode.TRACE.value else None
    if args.mode == ExecutionMode.FAKE.value:
        baseline_train=await _fake_summary(HERE / "data" / "train.evalset.json", "baseline", args.scenario)
        candidate_train=await _fake_summary(HERE / "data" / "train.evalset.json", "candidate", args.scenario)
        baseline_val=await _fake_summary(HERE / "data" / "val.evalset.json", "baseline", args.scenario)
        candidate_val=await _fake_summary(HERE / "data" / "val.evalset.json", "candidate", args.scenario)
    else:
        baseline_train=_summary(HERE / "data" / "train.evalset.json", "baseline", args.scenario)
        candidate_train=_summary(HERE / "data" / "train.evalset.json", "candidate", args.scenario)
        baseline_val=_summary(HERE / "data" / "val.evalset.json", "baseline", args.scenario, trace_baseline)
        candidate_val=_summary(HERE / "data" / "val.evalset.json", "candidate", args.scenario, trace_candidate)
    deltas=compare_cases(baseline_val, candidate_val)
    gate=evaluate_gate(config.gate, baseline_train, baseline_val, candidate_train, candidate_val, deltas, duration=time.monotonic()-start)
    failures = {}
    for summary in (baseline_train, baseline_val, candidate_train, candidate_val):
        for case in summary.cases:
            for reason in case.failure_reasons:
                failures[reason.category.value] = failures.get(reason.category.value, 0) + 1
    report={"schema_version":"v1","run":{"mode":args.mode,"scenario":args.scenario},"baseline":{"train":baseline_train.model_dump(),"validation":baseline_val.model_dump()},"candidate":{"train":candidate_train.model_dump(),"validation":candidate_val.model_dump()},"delta":{"validation_score":candidate_val.average_score-baseline_val.average_score,"cases":[d.model_dump() for d in deltas]},"failure_attribution":failures,"gate":gate.model_dump(),"audit":{"duration_seconds":time.monotonic()-start,"seed":args.seed}}
    write_reports(report, Path(args.output_dir) if args.output_dir else HERE / "runs" / f"{args.mode}-{args.scenario}")
    return report


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--mode", choices=[m.value for m in ExecutionMode], default="fake"); parser.add_argument("--scenario", choices=["improve","no_effect","overfit"], default="improve"); parser.add_argument("--output-dir"); parser.add_argument("--seed", type=int, default=42); parser.add_argument("--apply", action="store_true")
    args=parser.parse_args(); report=asyncio.run(run_pipeline(args)); print(report["gate"]["decision"])
if __name__ == "__main__": main()
