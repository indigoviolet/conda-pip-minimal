from __future__ import annotations

from .deps import CONDA
from dataclasses import dataclass
from more_itertools import first
from pathlib import Path
from typing import List


@dataclass
class CondaEnvSpec:
    name: str
    is_prefix: bool = False

    @classmethod
    async def current(cls) -> CondaEnvSpec:
        info = await conda_info()
        if info.get("active_prefix") is None:
            raise RuntimeError("No active conda environment found (or specified)")

        if info["active_prefix_name"] == info["active_prefix"]:
            return CondaEnvSpec(info["active_prefix"], is_prefix=True)
        else:
            return CondaEnvSpec(info["active_prefix_name"], is_prefix=False)

    def __call__(self) -> List[str]:
        return ["--prefix" if self.is_prefix else "--name", self.name]

    async def get_python(self) -> Path:
        return (await self.get_prefix()) / "bin" / "python"

    async def get_prefix(self) -> Path:
        if self.is_prefix:
            return Path(self.name)
        else:
            return Path((await conda_env_export(self))["prefix"])

    def export_name(self):
        if not self.is_prefix:
            return self.name
        else:
            return first(
                [p for p in reversed(Path(self.name).parts) if not p.startswith(".")]
            )


async def conda_env_export(env_spec: CondaEnvSpec):
    return await CONDA.json("env", "export", env_spec(), "--no-builds", "--json")


async def conda_info():
    return await CONDA.json("info", "--json")
