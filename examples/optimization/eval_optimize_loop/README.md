# Evaluation + Optimization Loop

订单售后助手示例优化 `agent/prompts/system.md` 与 `skill.md`，执行 baseline 评测、失败归因、候选优化、四次回归、Gate 决策与报告审计。

```powershell
pip install -e ".[eval,optimize]"
python examples/optimization/eval_optimize_loop/run_pipeline.py --mode fake --scenario improve
python examples/optimization/eval_optimize_loop/run_pipeline.py --mode fake --scenario no_effect
python examples/optimization/eval_optimize_loop/run_pipeline.py --mode fake --scenario overfit
python examples/optimization/eval_optimize_loop/run_pipeline.py --mode trace --scenario overfit
```

`fake` 不访问网络；`trace` 回放预录轨迹；`real` 读取 `agent/.env`（被测 Agent）和 `loop_pipeline/.env`（Judge 与 reflection LLM）。运行报告写入 `runs/<run-id>/optimization_report.json` 和 `.md`。默认不会写回 prompt；只有 `--mode real --apply` 且 Gate ACCEPT 时才允许写回。
