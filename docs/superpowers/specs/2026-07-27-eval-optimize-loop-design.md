# 订单售后助手评测优化闭环设计

## 目录与职责

```text
examples/optimization/eval_optimize_loop/
├── README.md                         # 用法、模式、场景、报告与限制
├── DESIGN.md                         # 300–500 字中文设计说明
├── run_pipeline.py                   # 唯一 CLI 编排入口
├── optimizer.json                    # AgentOptimizer 原生配置
├── pipeline.json                     # Gate、预算、写回、报告配置
├── agent/
│   ├── __init__.py
│   ├── agent.py                      # 每次创建时重读 system/skill
│   ├── tools.py                      # get_order、search_refund_policy
│   ├── fake_models.py                # fake agent/judge/reflection 注册
│   ├── .env                          # real 被测 Agent 配置，不提交
│   └── prompts/{system.md,skill.md}  # TargetPrompt 的两个字段
├── loop_pipeline/
│   ├── __init__.py
│   ├── .env                          # real judge/reflection 配置，不提交
│   ├── config.py                     # 严格 Pydantic 配置与 case 引用校验
│   ├── models.py                     # 稳定的报告与中间数据模型
│   ├── prompt_workspace.py            # 快照、临时应用、恢复和安全写回
│   ├── evaluator.py                  # AgentEvaluator 结果标准化
│   ├── attribution.py                # 确定性失败归因
│   ├── optimizer_runner.py            # AgentOptimizer 封装
│   ├── regression.py                 # 四次评估与 case-id delta
│   ├── gates.py                      # 接受/拒绝规则
│   └── report.py                     # JSON、Markdown、契约校验
├── data/{train,val,trace_baseline,trace_candidate}.evalset.json
├── sample_output/{improve,no_effect,overfit}/
│   └── optimization_report.{json,md}
└── runs/.gitignore

tests/evaluation/
├── test_eval_optimize_loop_config.py
├── test_eval_optimize_loop_attribution.py
├── test_eval_optimize_loop_regression.py
├── test_eval_optimize_loop_gates.py
├── test_eval_optimize_loop_report.py
└── test_eval_optimize_loop_e2e.py
```

`agent/` 仅提供订单售后 Agent、确定性工具与可优化 prompt；`loop_pipeline/` 仅提供配置、标准化评估、归因、优化器适配、回归、Gate 和报告；根目录 `tests/evaluation/` 承载 pytest 测试。真实模式由 `--mode real` 控制；被测 Agent 使用 `agent/.env`，Judge 与 reflection LLM 使用 `loop_pipeline/.env`，两份文件均不提交。

## 目标

在 `examples/optimization/eval_optimize_loop/` 提供可复现的评测—归因—优化—回归—审计示例，不修改 SDK。它优化订单售后助手的 `system.md` 与 `skill.md`，并以独立验证集决定是否接受候选，而不是直接采纳优化器结果。

## 架构与数据流

入口提供 `--mode fake|trace|real`。所有模式依次执行 baseline train、baseline val、候选生成、candidate train、candidate val 五个阶段；评估适配层将 SDK 的 `EvaluateResult` 归一为带 metric、pass/fail、轨迹摘要的 case 记录。归因模块按执行异常、工具错误、参数错误、知识召回不足、格式违规、rubric 失败和最终回复不匹配分类。回归模块按 `case_id` 对比四次评估，产出新增通过、新增失败及逐 metric 的升降。

`fake` 模式使用读取 prompt 的确定性模拟 Agent；候选 prompt 必须真实改变其工具调用或回复，不能按场景伪造得分。`trace` 模式从预录轨迹回放，不调用 Agent，且禁止写回。`real` 模式调用 `AgentEvaluator` 和 `AgentOptimizer`；被测 Agent 从 `agent/.env` 读取模型配置，judge 与 reflection LLM 从 `loop_pipeline/.env` 读取独立配置。两份 `.env` 均不提交、不进入报告或运行快照。

Gate 对所有启用规则取 AND：验证总分至少提升配置阈值、无新增 hard fail、受保护 case 或受保护 metric 不退化、无训练集提升且验证集总分或通过率下降的过拟合、成本与耗时未超预算。候选评估异常、case 集合不一致和缺少必填成本字段均按配置明确拒绝或报错，绝不静默通过。`--apply` 默认关闭，仅限 real 模式且需要优化成功、Gate ACCEPT、源 prompt 哈希未变化后才写回。

每次运行写入独立 `runs/<run_id>/`：输入配置快照、prompt 哈希与候选、四次原始评测、优化器原始产物、`optimization_report.json` 和 Markdown 报告。报告包含 baseline/candidate/delta、逐 case 差异、失败归因统计、gate 的每条规则、成本耗时与接受理由；不保存密钥、认证头、完整环境变量或模型思考文本。样例覆盖 improve、no-effect、overfit 三场景，包含 3 条训练与 3 条验证 case，其中退款关键 case 受保护，以验证过拟合拒绝逻辑。

## 配置、数据与验收契约

- 配置按运行者分离：`optimizer.json` 只满足 `AgentOptimizer` schema；`pipeline.json` 保存完整回归指标、Gate、hard fail、protected case、预算和写回策略。完整回归指标不进入 `optimizer.json`，避免 SDK 严格 schema 拒绝未知字段。
- 优化器仅用轻量最终回复指标生成 `best_prompts`，且始终 `update_source=False`；Pipeline 则用 `AgentEvaluator` 的完整轨迹执行四次独立回归，二者不能相互替代。
- 归因采用用户方案列出的确定性优先级：执行异常、错工具、错参数、知识召回、格式、rubric、最终回复、未知兜底；每个失败 case 都有主原因和受限大小的证据。
- `runs/` 只保存本次独立审计目录，Git 忽略；提交由真实运行产生并经契约校验的 `sample_output/improve`、`no_effect`、`overfit` 三份报告。
- 测试覆盖 config、attribution、regression、gates、report、e2e 六组文件，并验证无 Key 离线运行、prompt 恢复、trace 复用同一 Gate，以及 180 秒预算。

训练集固定三条：订单 A100 状态、已发货退款政策、A100 的 JSON 输出；验证集固定三条：A200 泛化查询、缺失订单号澄清、受保护的 A200 已完成退款。三种样例的预期结论分别为：improve 从 Train/Val `1/3` 提升到 `3/3` 并 ACCEPT；no-effect 保持 `1/3` 并因提升不足 REJECT；overfit 从 Train `1/3` 提升至 `3/3`、Val 从 `1/3` 退化至 `0/3`，因验证退化、受保护 case、新增 hard fail 和过拟合规则 REJECT。Trace 数据记录同一批 case 的 baseline/candidate 实际轨迹，并复用评价、归因、回归、Gate 和报告实现。

## 测试

单元测试覆盖配置校验、至少 12 条归因样本、case-id 回归比较、gate 决策矩阵与报告契约；端到端测试覆盖三种 fake 场景、trace 场景、无 API Key、prompt 恢复和 180 秒内完成。所有新增生产逻辑遵循先写失败测试、再实现的顺序。
