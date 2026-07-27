"""Stable JSON and Markdown audit reports."""
from __future__ import annotations
import json
from pathlib import Path


def write_reports(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "optimization_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    gate = report["gate"]
    lines = ["# Optimization Report", "", "## Decision", "", gate["decision"], "", "## Score Summary", "", json.dumps(report["delta"], ensure_ascii=False, indent=2), "", "## Gate Results", ""]
    lines.extend(f"- {reason}" for reason in gate.get("reasons", []))
    (output_dir / "optimization_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_report(report: dict) -> list[str]:
    return [key for key in ("schema_version", "baseline", "candidate", "delta", "failure_attribution", "gate", "audit") if key not in report]
