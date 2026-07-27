# Evaluation Optimization Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible order-support-agent example that evaluates, attributes failures, optimizes two prompts, regresses candidates, gates acceptance, and audits the run.

**Architecture:** `run_pipeline.py` orchestrates five independent evaluation phases. `loop_pipeline` owns stable data models and policy logic; `agent` owns the hot-reloaded order-support behavior; SDK evaluator/optimizer calls are isolated behind adapters. `optimizer.json` remains SDK-only while `pipeline.json` owns acceptance metrics and pipeline policy.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest/pytest-asyncio, tRPC-Agent `AgentEvaluator`, `AgentOptimizer`, `TargetPrompt`.

## Global Constraints

- Do not modify `trpc_agent_sdk`.
- Fake and trace modes run without API keys or network access and finish in 180 seconds.
- Always use `AgentOptimizer.optimize(..., update_source=False)`.
- Gate accepts only when every enabled rule passes; `--apply` is real-only and checks prompt hashes.
- Evaluate baseline train, baseline validation, candidate train, and candidate validation independently.
- Join regression records by `case_id`; missing or duplicate IDs are errors.
- Do not persist secrets, authorization headers, environment dumps, or thought text.

---

### Task 1: Scaffold configuration, stable models, and test contracts

**Files:**
- Create: `examples/optimization/eval_optimize_loop/{__init__.py,optimizer.json,pipeline.json}`
- Create: `examples/optimization/eval_optimize_loop/loop_pipeline/{__init__.py,models.py,config.py}`
- Create: `tests/evaluation/test_eval_optimize_loop_config.py`

**Interfaces:**
- Produces `ExecutionMode`, `FailureCategory`, `CaseChange`, `GateDecision`, `CaseEvaluationRecord`, `DatasetEvaluationSummary`, `CaseDelta`, `GateResult`, and `OptimizationReport` Pydantic models.
- Produces `load_pipeline_config(path: Path) -> PipelineConfig` and `validate_case_references(config, train_case_ids, val_case_ids) -> None`.

- [ ] Write tests for a valid two-file configuration, unknown-field rejection, negative budget rejection, invalid hard-fail category, and missing protected validation case.
- [ ] Run `pytest tests/evaluation/test_eval_optimize_loop_config.py -q`; verify the tests fail because the module does not exist.
- [ ] Implement strict Pydantic `extra="forbid"` models. Put acceptance metrics, gate, hard-fail categories, writeback, and report settings in `pipeline.json`; keep only SDK keys in `optimizer.json`.
- [ ] Re-run the focused test file and verify it passes.

### Task 2: Add deterministic order-support assets and evaluation data

**Files:**
- Create: `examples/optimization/eval_optimize_loop/agent/{__init__.py,tools.py,agent.py,fake_models.py}`
- Create: `examples/optimization/eval_optimize_loop/agent/prompts/{system.md,skill.md}`
- Create: `examples/optimization/eval_optimize_loop/data/{train.evalset.json,val.evalset.json,trace_baseline.evalset.json,trace_candidate.evalset.json}`
- Create: `tests/evaluation/test_eval_optimize_loop_e2e.py`

**Interfaces:**
- Produces deterministic `get_order(order_id: str) -> dict` and `search_refund_policy(question: str) -> dict`.
- Produces `create_agent(mode: ExecutionMode)`, `SYSTEM_PROMPT_PATH`, and `SKILL_PROMPT_PATH`; the factory rereads both files on every call.
- Evaluation data uses IDs `train_order_status`, `train_refund_policy`, `train_json_output`, `val_generalize_order_id`, `val_missing_order_id`, and `val_critical_refund`.

- [ ] Write failing tests asserting source prompts are read per factory invocation and that the six IDs are present and unique.
- [ ] Run the focused tests and verify expected failures.
- [ ] Implement fixed A100/A200 tool data, reasonable-but-incomplete baseline prompts, the three train and three validation cases, and trace conversations aligned by case ID.
- [ ] Implement fake Agent/Judge/Reflection registration. Reflection returns prompt candidates, never scores; behavior comes from candidate prompt directives and is re-evaluated.
- [ ] Re-run focused tests and verify pass.

### Task 3: Normalize full evaluations and attribute every failed case

**Files:**
- Create: `examples/optimization/eval_optimize_loop/loop_pipeline/{evaluator.py,attribution.py}`
- Create: `tests/evaluation/test_eval_optimize_loop_attribution.py`

**Interfaces:**
- Produces `async evaluate_dataset(dataset_path, metrics, mode, output_dir, ...) -> DatasetEvaluationSummary`.
- Produces `attribute_case_failure(case: CaseEvaluationRecord) -> list[FailureReason]`.

- [ ] Write at least twelve synthetic tests covering execution error, wrong tool, wrong arguments, missing knowledge recall, format violation, rubric failure, final response mismatch, and unknown fallback; assert every failed case has a reason.
- [ ] Run the attribution test file and observe it fails before implementation.
- [ ] Implement SDK-result/trace normalization and deterministic priority rules: execution, tool name, tool arguments, knowledge, format, rubric, final response, fallback. Preserve bounded evidence and a primary reason.
- [ ] Run the focused tests and confirm pass.

### Task 4: Implement prompt workspace and regression comparisons

**Files:**
- Create: `examples/optimization/eval_optimize_loop/loop_pipeline/{prompt_workspace.py,regression.py}`
- Create: `tests/evaluation/test_eval_optimize_loop_regression.py`

**Interfaces:**
- Produces async `PromptWorkspace.snapshot()`, `hashes()`, `apply_candidate()`, `restore_baseline()`, and guarded `writeback()`.
- Produces `compare_cases(baseline, candidate) -> list[CaseDelta]`, `compare_datasets(...) -> DatasetDelta`, and `evaluate_candidate(...)`.

- [ ] Write failing regression tests for newly-passed, newly-failed, score-improved, score-regressed, unchanged, reordered cases, mismatched IDs, and unchanged pass rate with metric regression.
- [ ] Run the regression tests and verify expected missing-symbol failures.
- [ ] Implement atomic prompt writes/restoration and case-ID maps. Record per-metric deltas even if aggregate scores tie; raise on duplicate or unequal case sets.
- [ ] Run focused tests and confirm pass.

### Task 5: Implement policy gates

**Files:**
- Create: `examples/optimization/eval_optimize_loop/loop_pipeline/gates.py`
- Create: `tests/evaluation/test_eval_optimize_loop_gates.py`

**Interfaces:**
- Produces `evaluate_gate(config, baseline_train, baseline_val, candidate_train, candidate_val, val_case_deltas, optimize_result, pipeline_duration_seconds) -> GateResult`.

- [ ] Write a 10–12 row decision matrix: clean validation gain, insufficient gain, new hard fail, protected-case regression, protected-metric regression, overfit, cost budget, duration budget, and unavailable cost.
- [ ] Run the gate tests and verify they fail before logic exists.
- [ ] Implement independent `GateRuleResult`s and AND aggregation. Gate code may inspect IDs/configuration and deltas, never case prose or execution mode.
- [ ] Run focused tests and confirm pass.

### Task 6: Wrap optimizer and render auditable reports

**Files:**
- Create: `examples/optimization/eval_optimize_loop/loop_pipeline/{optimizer_runner.py,report.py}`
- Create: `tests/evaluation/test_eval_optimize_loop_report.py`

**Interfaces:**
- Produces `async run_optimizer(...) -> OptimizeResult` using two `TargetPrompt.add_path` fields and `update_source=False`.
- Produces `build_report`, `write_reports`, `render_markdown`, and `validate_report`.

- [ ] Write failing report-contract tests for required top-level JSON fields, failure reasons, rejection reasons, prompt hashes, Markdown decision/score/delta sections, and malformed report detection.
- [ ] Run report tests and observe failure.
- [ ] Implement atomic JSON/Markdown writing, artifact index, compact prompt references/hashes, and human-readable ACCEPT/REJECT first section. Preserve raw SDK optimizer artifacts under the run directory.
- [ ] Run focused tests and confirm pass.

### Task 7: Build the CLI orchestration and real-mode configuration loading

**Files:**
- Create: `examples/optimization/eval_optimize_loop/run_pipeline.py`
- Create: `examples/optimization/eval_optimize_loop/{agent/.env,loop_pipeline/.env,runs/.gitignore}`
- Modify: `.gitignore`

**Interfaces:**
- Produces `async run_pipeline(args) -> OptimizationReport` and `async main() -> None`.
- CLI: `--mode`, `--scenario`, `--output-dir`, `--apply`, `--seed`, `--check-report`, `--verbose`.

- [ ] Write failing E2E tests for fake improve ACCEPT, no-effect REJECT, overfit REJECT, trace improve/overfit, no-key operation, prompt restoration, and under-180-second duration.
- [ ] Run E2E tests and verify they fail because the CLI orchestrator is absent.
- [ ] Implement phase order, independent audit paths, loading `agent/.env` and `loop_pipeline/.env` only in real mode, candidate handling, `finally` restoration, report checking, and exit codes (REJECT is zero; invalid config/execution/report check is one).
- [ ] Add scoped ignores so both `.env` files and generated `runs/*` remain untracked while `runs/.gitignore` remains committed.
- [ ] Run E2E tests and confirm pass.

### Task 8: Write usage/docs and generate sample reports

**Files:**
- Create: `examples/optimization/eval_optimize_loop/{README.md,DESIGN.md}`
- Create: `examples/optimization/eval_optimize_loop/sample_output/{improve,no_effect,overfit}/optimization_report.{json,md}`

- [ ] Write a failing test that validates every committed sample report with `validate_report` and verifies its expected decision.
- [ ] Run the test and observe absent samples.
- [ ] Document installation, all modes, all scenarios, `--apply`, reports, two `.env` files, test command, known limits, and real-agent replacement points. Write 300–500 Chinese characters in `DESIGN.md` covering attribution, acceptance, anti-overfit, and audit.
- [ ] Generate samples by executing fake scenarios; copy only validated compact reports into `sample_output`.
- [ ] Run the sample test and verify pass.

### Task 9: Full verification and review

**Files:**
- Verify all files introduced above.

- [ ] Run `pytest tests/evaluation/test_eval_optimize_loop_*.py -q` and verify no failures.
- [ ] Run all three fake commands and two trace commands in fresh output directories; inspect their reports for expected ACCEPT/REJECT outcomes.
- [ ] Run `git diff --check` and `git status --short`; ensure no `.env` content or generated `runs/<run_id>` artifact is tracked.
- [ ] Commit the completed example only after the preceding evidence is clean.
