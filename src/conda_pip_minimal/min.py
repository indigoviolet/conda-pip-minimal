from __future__ import annotations

from dataclasses import dataclass, field
import io
from typing import Dict, List, Optional, Set, Union
import yaml
import subprocess
from loguru import logger

from .conda_env import CondaEnvSpec
from .deps import CONDA, CONDA_TREE, PIPDEPTREE, ensure_conda_tree, ensure_pipdeptree
from .result_capture import open_capturing_nursery
from .version import RelaxLevel, version_string


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


async def conda_leaves(env_spec: Optional[CondaEnvSpec] = None) -> List[str]:
    return await CONDA_TREE.literal(
        env_spec() if env_spec is not None else [], "leaves"
    )


async def conda_list(
    env_spec: Optional[CondaEnvSpec] = None,
) -> Dict[str, CondaPackage]:
    try:
        output = await CONDA.json(
            "list", env_spec() if env_spec is not None else [], "--json"
        )
    except subprocess.CalledProcessError:
        logger.error("Conda failed to list environment")
        raise
    return {
        p["name"]: CondaPackage(p["name"], p["version"], p["channel"]) for p in output
    }


async def pipdeptree_leaves(python: Optional[str]) -> Dict[str, PipPackage]:
    output = await PIPDEPTREE.json(
        ["--python", python] if python is not None else [],
        "--local-only",
        "--json-tree",
    )
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

    async def _pipdeptree_leaves(self):
        await ensure_pipdeptree()
        python = (
            str(await self.env_spec.get_python()) if self.env_spec is not None else None
        )
        return await pipdeptree_leaves(python=python)

    async def _conda_leaves(self):
        await ensure_conda_tree()
        return await conda_leaves(self.env_spec)

    async def compute(self) -> MinimalSet:
        async with open_capturing_nursery() as N:
            clvs_fut = N.start_soon(self._conda_leaves)
            clst_fut = N.start_soon(conda_list, self.env_spec)
            pls_fut = (
                N.start_soon(self._pipdeptree_leaves) if self.include_pip else None
            )

        clvs = clvs_fut.result
        clst = clst_fut.result

        # await ensure_conda_tree()
        # clvs = await conda_leaves(self.env_spec)
        # clst = await conda_list(self.env_spec)

        conda_min_pkg_names = (set(clvs) | self.always_include) - self.always_exclude
        conda_pkgs = [
            clst.get(c, CondaPackage(c, version=None, channel=None))
            for c in conda_min_pkg_names
        ]
        ms = MinimalSet(env_spec=self.env_spec, conda_packages=conda_pkgs)

        if pls_fut is not None:
            # pls = await self._pipdeptree_leaves()
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
    env_spec: Optional[CondaEnvSpec]
    conda_packages: List[CondaPackage]
    pip_packages: List[PipPackage] = field(default_factory=list)

    async def export(
        self, *, include_channel: bool = False, relax: RelaxLevel = RelaxLevel.FULL
    ) -> str:
        yml_data = await self.get_yml_data(include_channel=include_channel, relax=relax)
        stream = io.StringIO()
        yaml.dump(yml_data, stream)
        return stream.getvalue()

    async def get_yml_data(
        self, *, include_channel: bool, relax: RelaxLevel = RelaxLevel.FULL
    ) -> Dict:
        deps: List[Union[str, Dict[str, List[str]]]] = [
            p.export(include_channel=include_channel, relax=relax)
            for p in self.conda_packages
        ]
        if len(self.pip_packages):
            pip_deps = {"pip": [p.export(relax=relax) for p in self.pip_packages]}
            deps.append(pip_deps)
        return {"name": (await self._name()), "dependencies": deps}

    async def _name(self) -> str:
        return (
            self.env_spec.name
            if self.env_spec is not None
            else (await CondaEnvSpec.get_name())
        )
