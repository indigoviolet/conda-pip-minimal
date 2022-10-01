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

    def get_python(self) -> Path:
        return self.get_prefix() / "bin" / "python"

    def get_prefix(self) -> Path:
        if self.is_prefix:
            return Path(self.name)
        else:
            return Path(conda_env_export(self)["prefix"])

    @classmethod
    def get_name(cls) -> str:
        return conda_env_export()["name"]


def conda_env_export(env_spec: Optional[CondaEnvSpec] = None):
    return CONDA.json(
        "env",
        "export",
        env_spec() if env_spec is not None else [],
        "--no-builds",
        "--json",
    )
