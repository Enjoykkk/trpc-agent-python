"""Prompt paths and runtime prompt loading for the order-support agent."""

from __future__ import annotations

from pathlib import Path


HERE = Path(__file__).resolve().parent
SYSTEM_PROMPT_PATH = HERE / "prompts" / "system.md"
SKILL_PROMPT_PATH = HERE / "prompts" / "skill.md"


def read_instruction() -> str:
    """Read both editable prompt files at invocation time, never at import time."""
    system = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    skill = SKILL_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return f"{system}\n\n## Order Support Skill\n{skill}"
