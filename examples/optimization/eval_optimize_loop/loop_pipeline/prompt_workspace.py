"""Safe prompt snapshots, temporary candidate application, and guarded writeback."""

from __future__ import annotations

import hashlib
from pathlib import Path


class PromptWorkspace:
    def __init__(self, paths: dict[str, Path]):
        self.paths = dict(paths)
        self._baseline: dict[str, str] | None = None

    async def snapshot(self) -> dict[str, str]:
        if self._baseline is None:
            self._baseline = {name: path.read_text(encoding="utf-8") for name, path in self.paths.items()}
        return dict(self._baseline)

    async def hashes(self) -> dict[str, str]:
        values = await self.snapshot()
        return {name: hashlib.sha256(value.encode("utf-8")).hexdigest() for name, value in values.items()}

    async def apply_candidate(self, prompts: dict[str, str]) -> None:
        await self.snapshot()
        if set(prompts) != set(self.paths):
            raise ValueError("candidate prompt fields do not match workspace")
        for name, path in self.paths.items():
            path.write_text(prompts[name], encoding="utf-8")

    async def restore_baseline(self) -> None:
        baseline = await self.snapshot()
        for name, path in self.paths.items():
            path.write_text(baseline[name], encoding="utf-8")

    async def writeback(self, prompts: dict[str, str], expected_hashes: dict[str, str]) -> None:
        current = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in self.paths.items()}
        if current != expected_hashes:
            raise ValueError("source prompts changed since baseline snapshot")
        await self.apply_candidate(prompts)
