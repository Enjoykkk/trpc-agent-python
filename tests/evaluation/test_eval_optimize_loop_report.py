"""Optimization report contract tests."""
import json
from pathlib import Path
from examples.optimization.eval_optimize_loop.loop_pipeline.report import validate_report, write_reports


def _report():
    return {"schema_version": "v1", "baseline": {}, "candidate": {}, "delta": {}, "failure_attribution": {}, "gate": {"decision": "REJECT", "reasons": ["validation score delta=0"]}, "audit": {}}


def test_report_has_required_contract_and_human_decision(tmp_path: Path):
    write_reports(_report(), tmp_path)
    payload = json.loads((tmp_path / "optimization_report.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "optimization_report.md").read_text(encoding="utf-8")
    assert validate_report(payload) == []
    assert "## Decision" in markdown and "REJECT" in markdown


def test_report_validator_identifies_missing_top_level_field():
    report = _report(); del report["audit"]
    assert validate_report(report) == ["audit"]
