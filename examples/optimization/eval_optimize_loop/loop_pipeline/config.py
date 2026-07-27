"""Strict configuration parsing for pipeline-owned policy."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field, field_validator

from .models import AcceptanceMetrics, FailureCategory, StrictModel


class GateConfig(StrictModel):
    min_validation_score_gain: float = Field(ge=0.0, le=1.0)
    min_validation_pass_rate_gain: float = Field(ge=0.0, le=1.0)
    max_single_metric_regression: float = Field(ge=0.0, le=1.0)
    forbid_new_hard_fail: bool = True
    protected_case_ids: list[str] = Field(default_factory=list)
    protected_metric_names: list[str] = Field(default_factory=list)
    overfit_guard: bool = True
    max_cost_usd: float = Field(ge=0.0)
    max_duration_seconds: float = Field(gt=0.0)


class WritebackConfig(StrictModel):
    enabled: bool = False
    require_explicit_apply: bool = True
    require_source_hash_match: bool = True


class ReportConfig(StrictModel):
    include_raw_trace: bool = True
    max_trace_items_per_case: int = Field(default=20, ge=0)


class PipelineConfig(StrictModel):
    schema_version: str = "v1"
    acceptance_metrics: AcceptanceMetrics
    gate: GateConfig
    hard_fail_categories: list[FailureCategory] = Field(default_factory=list)
    writeback: WritebackConfig = Field(default_factory=WritebackConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)

    @field_validator("hard_fail_categories")
    @classmethod
    def no_duplicate_hard_fail_categories(cls, values: list[FailureCategory]) -> list[FailureCategory]:
        if len(set(values)) != len(values):
            raise ValueError("hard_fail_categories must not contain duplicates")
        return values


def load_pipeline_config(path: Path) -> PipelineConfig:
    """Load one pipeline-owned JSON file with strict validation."""
    return PipelineConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_case_references(
    config: PipelineConfig,
    train_case_ids: set[str],
    val_case_ids: set[str],
) -> None:
    """Ensure protected cases exist and are never training-only references."""
    for case_id in config.gate.protected_case_ids:
        if case_id not in val_case_ids:
            if case_id in train_case_ids:
                raise ValueError(f"protected case {case_id!r} must belong to the validation set")
            raise ValueError(f"protected validation case {case_id!r} was not found")
