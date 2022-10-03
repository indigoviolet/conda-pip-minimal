from __future__ import annotations

from .conda_env import CondaEnvSpec
from .min import ComputeMinimalSet
from .version import RelaxLevel
from functools import partial
from loguru import logger
from pathlib import Path
import sys
import trio
import typer
from typing import List, Optional


def main(
    prefix: Optional[Path] = typer.Option(
        None, "--prefix", "-p", help="Conda env prefix"
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Conda env name"),
    pip: bool = typer.Option(True, help="Include pip dependencies"),
    relax: RelaxLevel = typer.Option("full"),
    include: List[str] = typer.Option(["python", "pip"]),
    exclude: List[str] = typer.Option([]),
    channel: bool = typer.Option(False, help="Add channel to conda dependencies"),
    debug: bool = False,
):
    if prefix is not None and name is not None:
        print(f"Exactly one of --prefix or --name must be provided {prefix=} {name=}")
        raise typer.Exit()

    logger.configure(
        handlers=[{"sink": sys.stderr, "level": ("DEBUG" if debug else "WARNING")}]
    )

    env_spec: Optional[CondaEnvSpec] = None
    if prefix is not None or name is not None:
        env_spec = CondaEnvSpec(
            name=str(prefix or name), is_prefix=(prefix is not None)
        )

    cms = ComputeMinimalSet(
        env_spec=env_spec,
        include_pip=pip,
        always_include=set(include),
        always_exclude=set(exclude),
    )

    trio.run(partial(compute_and_export, cms, channel=channel, relax=relax))


async def compute_and_export(cms: ComputeMinimalSet, channel: bool, relax: RelaxLevel):
    ms = await cms.compute()
    print(await ms.export(include_channel=channel, relax=relax))


if __name__ == "__main__":
    typer.run(main)
