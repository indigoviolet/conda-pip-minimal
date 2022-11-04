from __future__ import annotations

from .conda_env import CondaEnvSpec
from .version import RelaxLevel, version_string
from dataclasses import dataclass, field
import io
from ruamel.yaml import YAML  # type: ignore
from typing import Dict, List, Optional, TypeVar, Union


@dataclass
class CondaPackage:
    name: str
    version: Optional[str]
    channel: Optional[str]

    def export(
        self, *, include_channel: bool = False, relax: RelaxLevel = RelaxLevel.FULL
    ) -> str:
        return "".join(
            [
                f"{self.channel}::"
                if (include_channel and self.channel is not None)
                else "",
                self.name,
                version_string(self.version, op="=", how=relax),
            ]
        )


@dataclass
class PipPackage:
    name: str
    version: str

    def export(self, *, relax: RelaxLevel = RelaxLevel.FULL) -> str:
        return f"{self.name}{version_string(self.version, op='==', how=relax)}"


@dataclass
class YAMLExport:
    env_spec: CondaEnvSpec
    conda_packages: List[CondaPackage] = field(default_factory=list)
    pip_packages: List[PipPackage] = field(default_factory=list)

    def __post_init__(self):
        self.yaml = YAML()
        self.yaml.default_flow_style = False
        self.yaml.indent(sequence=4, mapping=2, offset=2)

    async def export(
        self,
        *,
        include_channel: bool = False,
        relax: RelaxLevel = RelaxLevel.FULL,
        export_name: Optional[str] = None,
    ) -> str:
        yml_data = await self.get_yml_data(
            include_channel=include_channel, relax=relax, export_name=export_name
        )
        stream = io.StringIO()
        self.yaml.dump(yml_data, stream)
        return stream.getvalue()

    async def get_yml_data(
        self,
        *,
        include_channel: bool,
        relax: RelaxLevel = RelaxLevel.FULL,
        export_name: Optional[str] = None,
    ) -> Dict:
        deps: List[Union[str, Dict[str, List[str]]]] = [
            p.export(include_channel=include_channel, relax=relax)
            for p in sort_packages(self.conda_packages)
        ]
        if len(self.pip_packages):
            pip_deps = {
                "pip": [p.export(relax=relax) for p in sort_packages(self.pip_packages)]
            }
            deps.append(pip_deps)
        return {
            "name": export_name
            if export_name is not None
            else self.env_spec.export_name(),
            "dependencies": deps,
        }


P = TypeVar("P", bound=Union[PipPackage, CondaPackage])

SortPriority = {"python": 0, "pip": 1}


def sort_packages(packages: List[P]) -> List[P]:
    return sorted(packages, key=lambda p: (SortPriority.get(p.name, 1e6), p.name))
