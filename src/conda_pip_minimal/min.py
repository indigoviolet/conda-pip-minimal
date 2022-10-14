from __future__ import annotations

from dataclasses import dataclass, field
import io

from ruamel.yaml import YAML
from typing import Dict, List, Optional, Set, Union

from .conda_env import CondaEnvSpec
from .deps import CONDA, CONDA_TREE, PIPDEPTREE, ensure_conda_tree, ensure_pipdeptree
from .result_capture import open_capturing_nursery
from .version import RelaxLevel, version_string
from .logging import logger


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


async def conda_leaves(env_spec: CondaEnvSpec) -> List[str]:
    return await CONDA_TREE.literal(env_spec(), "leaves")


async def conda_list(env_spec: CondaEnvSpec) -> Dict[str, CondaPackage]:
    output = await CONDA.json("list", env_spec(), "--json")
    return {
        p["name"]: CondaPackage(p["name"], p["version"], p["channel"]) for p in output
    }


async def pipdeptree_leaves(python: str) -> Dict[str, PipPackage]:
    output = await PIPDEPTREE.json(["--python", python], "--local-only", "--json-tree")
    return {
        p["package_name"]: PipPackage(p["package_name"], p["installed_version"])
        for p in output
    }


@dataclass
class ComputeMinimalSet:
    env_spec: Optional[CondaEnvSpec] = None
    include_pip: bool = True
    always_include: Set[str] = field(default_factory=set)
    always_exclude: Set[str] = field(default_factory=set)

    async def _pipdeptree_leaves(self, env_spec: CondaEnvSpec):
        await ensure_pipdeptree()
        python = str(await env_spec.get_python())
        return await pipdeptree_leaves(python=python)

    async def _conda_leaves(self, env_spec: CondaEnvSpec):
        await ensure_conda_tree()
        return await conda_leaves(env_spec)

    async def compute(self) -> MinimalSet:
        if self.env_spec is None:
            self.env_spec = await CondaEnvSpec.current()

        if self.env_spec is None:
            raise RuntimeError("Could not identify conda environment")

        async with open_capturing_nursery() as N:
            try:
                clst = await conda_list(self.env_spec)
            except BaseException as e:
                logger.debug(f"{self.env_spec=}")
                raise RuntimeError(f"Invalid conda environment") from e

            clvs_fut = N.start_soon(self._conda_leaves, self.env_spec)
            pls_fut = (
                N.start_soon(self._pipdeptree_leaves, self.env_spec)
                if self.include_pip
                else None
            )

        clvs = clvs_fut.result

        conda_min_pkg_names = (set(clvs) | self.always_include) - self.always_exclude
        conda_pkgs = [
            clst.get(c, CondaPackage(c, version=None, channel=None))
            for c in conda_min_pkg_names
        ]
        ms = MinimalSet(env_spec=self.env_spec, conda_packages=conda_pkgs)

        if pls_fut is not None:
            pls = pls_fut.result
            # Filter pipdeptree_leaves to packages that are installed by pip,
            # according to conda, since by default it will include
            # conda-installed packages
            ms.pip_packages = [
                v
                for k, v in pls.items()
                if k not in self.always_exclude
                and k in clst
                and clst[k].channel == "pypi"
            ]

        return ms


@dataclass
class MinimalSet:
    env_spec: CondaEnvSpec
    conda_packages: List[CondaPackage]
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
            for p in self.conda_packages
        ]
        if len(self.pip_packages):
            pip_deps = {"pip": [p.export(relax=relax) for p in self.pip_packages]}
            deps.append(pip_deps)
        return {
            "name": export_name
            if export_name is not None
            else self.env_spec.export_name(),
            "dependencies": deps,
        }
