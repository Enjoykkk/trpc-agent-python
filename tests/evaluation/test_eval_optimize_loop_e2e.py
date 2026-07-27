# Tencent is pleased to support the open source community by making tRPC-Agent-Python available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
"""End-to-end contracts for the evaluation optimization loop example."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from examples.optimization.eval_optimize_loop.agent.agent import (
    SKILL_PROMPT_PATH,
    SYSTEM_PROMPT_PATH,
    read_instruction,
)
from examples.optimization.eval_optimize_loop.loop_pipeline.prompt_workspace import PromptWorkspace
from examples.optimization.eval_optimize_loop.run_pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[2] / "examples" / "optimization" / "eval_optimize_loop"


def test_prompt_instruction_is_reloaded_from_disk():
    original = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    try:
        SYSTEM_PROMPT_PATH.write_text("new system instruction", encoding="utf-8")
        assert "new system instruction" in read_instruction()
    finally:
        SYSTEM_PROMPT_PATH.write_text(original, encoding="utf-8")


def test_public_train_and_validation_sets_have_six_unique_case_ids():
    ids: list[str] = []
    for name in ("train.evalset.json", "val.evalset.json"):
        payload = json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
        ids.extend(case["eval_id"] for case in payload["eval_cases"])

    assert len(ids) == 6
    assert len(set(ids)) == 6
    assert {"val_critical_refund", "train_json_output"}.issubset(ids)
    assert SKILL_PROMPT_PATH.exists()


@pytest.mark.asyncio
async def test_workspace_restores_baseline_and_rejects_stale_writeback(tmp_path: Path):
    system, skill = tmp_path / "system.md", tmp_path / "skill.md"
    system.write_text("baseline system", encoding="utf-8")
    skill.write_text("baseline skill", encoding="utf-8")
    workspace = PromptWorkspace({"system_prompt": system, "skill_prompt": skill})

    baseline_hashes = await workspace.hashes()
    await workspace.apply_candidate({"system_prompt": "candidate system", "skill_prompt": "candidate skill"})
    await workspace.restore_baseline()

    assert system.read_text(encoding="utf-8") == "baseline system"
    system.write_text("external edit", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        await workspace.writeback({"system_prompt": "accepted", "skill_prompt": "accepted"}, baseline_hashes)


@pytest.mark.asyncio
async def test_fake_mode_rejects_prompt_writeback_request():
    args = type("Args", (), {"mode": "fake", "scenario": "improve", "output_dir": None, "seed": 42, "apply": True})()
    with pytest.raises(ValueError, match="real"):
        await run_pipeline(args)


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,decision", [("improve", "ACCEPT"), ("no_effect", "REJECT"), ("overfit", "REJECT")])
async def test_fake_scenarios_produce_expected_gate_decision(tmp_path: Path, scenario: str, decision: str):
    args = type("Args", (), {"mode": "fake", "scenario": scenario, "output_dir": str(tmp_path / scenario), "seed": 42, "apply": False})()
    report = await run_pipeline(args)
    assert report["gate"]["decision"] == decision
    assert (tmp_path / scenario / "optimization_report.json").exists()
