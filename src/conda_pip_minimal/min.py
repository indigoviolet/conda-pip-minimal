from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .conda_env import CondaEnvSpec
from .deps import CONDA, CONDA_TREE, PIPDEPTREE, ensure_conda_tree, ensure_pipdeptree
from .export import CondaPackage, PipPackage, YAMLExport
from .logging import logger
from .result_capture import open_capturing_nursery


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

    async def compute(self) -> YAMLExport:
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
        ms = YAMLExport(env_spec=self.env_spec, conda_packages=conda_pkgs)

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
