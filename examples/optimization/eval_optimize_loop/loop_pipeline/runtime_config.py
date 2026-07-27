"""Explicit real-mode environment loading without recording secret values."""

from __future__ import annotations

from pathlib import Path


_REQUIRED = (
    "AFTERSALE_AGENT_MODEL_NAME", "AFTERSALE_AGENT_API_KEY", "AFTERSALE_AGENT_BASE_URL",
    "AFTERSALE_JUDGE_MODEL_NAME", "AFTERSALE_JUDGE_API_KEY", "AFTERSALE_JUDGE_BASE_URL",
    "AFTERSALE_OPTIMIZER_MODEL_NAME", "AFTERSALE_OPTIMIZER_API_KEY", "AFTERSALE_OPTIMIZER_BASE_URL",
)


def _read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"real-mode environment file is missing: {path}")
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def load_real_mode_environment(agent_env: Path, evaluator_env: Path) -> dict[str, str]:
    """Load role-separated settings and fail before any model request when incomplete."""
    values = _read_env(agent_env)
    values.update(_read_env(evaluator_env))
    missing = [key for key in _REQUIRED if not values.get(key)]
    if missing:
        raise ValueError(f"real-mode environment is missing: {', '.join(missing)}")
    return values
