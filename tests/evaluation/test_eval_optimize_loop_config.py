# Tencent is pleased to support the open source community by making tRPC-Agent-Python available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Agent-Python is licensed under Apache-2.0.
"""Configuration contract tests for the evaluation optimization loop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from examples.optimization.eval_optimize_loop.loop_pipeline.config import (
    load_pipeline_config,
    validate_case_references,
)
from examples.optimization.eval_optimize_loop.loop_pipeline.runtime_config import load_real_mode_environment


def _payload() -> dict:
    return {
        "schema_version": "v1",
        "acceptance_metrics": {
            "metrics": [
                {"metric_name": "final_response_avg_score", "threshold": 1.0},
                {"metric_name": "tool_trajectory_avg_score", "threshold": 1.0},
            ],
            "num_runs": 1,
        },
        "gate": {
            "min_validation_score_gain": 0.05,
            "min_validation_pass_rate_gain": 0.0,
            "max_single_metric_regression": 0.0,
            "forbid_new_hard_fail": True,
            "protected_case_ids": ["val_critical_refund"],
            "protected_metric_names": ["tool_trajectory_avg_score"],
            "overfit_guard": True,
            "max_cost_usd": 0.1,
            "max_duration_seconds": 180,
        },
        "hard_fail_categories": ["execution_error", "wrong_tool_call", "wrong_tool_arguments"],
        "writeback": {
            "enabled": False,
            "require_explicit_apply": True,
            "require_source_hash_match": True,
        },
        "report": {"include_raw_trace": True, "max_trace_items_per_case": 20},
    }


def _write_config(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loads_strict_pipeline_configuration(tmp_path: Path):
    config = load_pipeline_config(_write_config(tmp_path, _payload()))

    assert config.gate.min_validation_score_gain == 0.05
    assert config.acceptance_metrics.metrics[1].metric_name == "tool_trajectory_avg_score"


def test_rejects_unknown_pipeline_configuration_field(tmp_path: Path):
    payload = _payload()
    payload["misspelled_gate"] = True

    with pytest.raises(ValidationError, match="misspelled_gate"):
        load_pipeline_config(_write_config(tmp_path, payload))


def test_rejects_negative_cost_budget(tmp_path: Path):
    payload = _payload()
    payload["gate"]["max_cost_usd"] = -0.1

    with pytest.raises(ValidationError, match="max_cost_usd"):
        load_pipeline_config(_write_config(tmp_path, payload))


def test_rejects_protected_case_outside_validation_set(tmp_path: Path):
    config = load_pipeline_config(_write_config(tmp_path, _payload()))

    with pytest.raises(ValueError, match="val_critical_refund"):
        validate_case_references(config, {"train_order_status"}, {"val_generalize_order_id"})


def test_rejects_unknown_hard_fail_category(tmp_path: Path):
    payload = _payload()
    payload["hard_fail_categories"] = ["misspelled_category"]

    with pytest.raises(ValidationError, match="hard_fail_categories"):
        load_pipeline_config(_write_config(tmp_path, payload))


def test_real_mode_loads_agent_and_evaluator_env_files(tmp_path: Path):
    agent_env, evaluator_env = tmp_path / "agent.env", tmp_path / "evaluator.env"
    agent_env.write_text("AFTERSALE_AGENT_MODEL_NAME=agent\nAFTERSALE_AGENT_API_KEY=agent-key\nAFTERSALE_AGENT_BASE_URL=http://agent\n", encoding="utf-8")
    evaluator_env.write_text("AFTERSALE_JUDGE_MODEL_NAME=judge\nAFTERSALE_JUDGE_API_KEY=judge-key\nAFTERSALE_JUDGE_BASE_URL=http://judge\nAFTERSALE_OPTIMIZER_MODEL_NAME=optimizer\nAFTERSALE_OPTIMIZER_API_KEY=optimizer-key\nAFTERSALE_OPTIMIZER_BASE_URL=http://optimizer\n", encoding="utf-8")

    values = load_real_mode_environment(agent_env, evaluator_env)
    assert values["AFTERSALE_AGENT_MODEL_NAME"] == "agent"
    assert values["AFTERSALE_OPTIMIZER_MODEL_NAME"] == "optimizer"
