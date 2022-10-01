from __future__ import annotations

from .deps import CONDA
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CondaEnvSpec:
    name: str
    is_prefix: bool = False

    def __call__(self) -> List[str]:
        return ["--prefix" if self.is_prefix else "--name", self.name]

    async def get_python(self) -> Path:
        return (await self.get_prefix()) / "bin" / "python"

    async def get_prefix(self) -> Path:
        if self.is_prefix:
            return Path(self.name)
        else:
            return Path((await conda_env_export(self))["prefix"])

    @classmethod
    async def get_name(cls) -> str:
        return (await conda_env_export())["name"]


async def conda_env_export(env_spec: Optional[CondaEnvSpec] = None):
    return await CONDA.json(
        "env",
        "export",
        env_spec() if env_spec is not None else [],
        "--no-builds",
        "--json",
    )
