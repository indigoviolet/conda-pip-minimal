from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

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

    async def _pipdeptree_leaves(self, env_spec: CondaEnvSpec) -> Dict[str, PipPackage]:
        await ensure_pipdeptree()
        python = str(await env_spec.get_python())
        return await pipdeptree_leaves(python=python)

    async def _conda_leaves(self, env_spec: CondaEnvSpec) -> List[str]:
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

        min_conda_pkgs, min_pip_pkgs = self._get_min_packages(
            conda_list=clst,
            conda_leaves=clvs_fut.result,
            pip_leaves=pls_fut.result if pls_fut is not None else None,
        )
        return YAMLExport(
            env_spec=self.env_spec,
            conda_packages=min_conda_pkgs,
            pip_packages=min_pip_pkgs,
        )

    def _get_min_packages(
        self,
        *,
        conda_list: Dict[str, CondaPackage],
        conda_leaves: List[str],
        pip_leaves: Optional[Dict[str, PipPackage]],
    ) -> Tuple[List[CondaPackage], List[PipPackage]]:
        # First add conda packages - excludes
        conda_packages = {
            c: conda_list[c] for c in conda_leaves if c not in self.always_exclude
        }

        # Then add pip packages - excludes
        pip_packages: Dict[str, PipPackage] = {}
        if pip_leaves is not None:
            # Filter pipdeptree_leaves to packages that are installed by pip,
            # according to conda, since by default it will include
            # conda-installed packages
            pip_leaves = {
                k: v
                for k, v in pip_leaves.items()
                if k in conda_list and conda_list[k].channel == "pypi"
            }
            pip_packages = {
                k: v for k, v in pip_leaves.items() if k not in self.always_exclude
            }

        # Finally, add always_include packages, choosing the appropriate source
        for p in (
            self.always_include
            - set(conda_packages.keys())
            - set(pip_packages.keys())
            - self.always_exclude
        ):
            if p not in conda_list:
                raise RuntimeError(f"-i package {p} not found in `conda list`")

            pkg = conda_list[p]
            if pkg.channel == "pypi":
                assert pkg.version is not None
                pip_packages[p] = PipPackage(p, pkg.version)
            else:
                conda_packages[p] = pkg

        return list(conda_packages.values()), list(pip_packages.values())
