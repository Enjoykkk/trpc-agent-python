"""SDK optimizer adapter; pipeline policy remains outside the SDK."""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from trpc_agent_sdk.evaluation import AgentOptimizer, TargetPrompt


async def run_optimizer(config_path: Path, train_path: Path, validation_path: Path, output_dir: Path,
                        call_agent: Callable[[str], Awaitable[str]], prompt_paths: dict[str, Path]):
    """Generate candidates only; source prompts are never updated here."""
    target = TargetPrompt()
    for name, path in prompt_paths.items():
        target.add_path(name, str(path))
    return await AgentOptimizer.optimize(
        config_path=str(config_path), call_agent=call_agent, target_prompt=target,
        train_dataset_path=str(train_path), validation_dataset_path=str(validation_path),
        output_dir=str(output_dir), update_source=False, verbose=0,
    )
