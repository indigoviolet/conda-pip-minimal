from __future__ import annotations

from .conda_env import CondaEnvSpec
from .min import ComputeMinimalSet
from .version import RelaxLevel
from functools import partial
from importlib.metadata import version
from loguru import logger
from pathlib import Path
import sys
import trio
import typer
from typing import List, Optional

app = typer.Typer(add_completion=False)


def version_callback(value: bool):
    if value:
        print(version("conda-pip-minimal"))
        raise typer.Exit()


@app.command()
def main(
    prefix: Optional[Path] = typer.Option(
        None, "--prefix", "-p", help="Target conda env prefix"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Target conda env name"
    ),
    pip: bool = typer.Option(True, help="Include pip dependencies"),
    relax: RelaxLevel = typer.Option(
        "full", "--relax", "-r", help="Version stringency"
    ),
    include: List[str] = typer.Option(
        ["python", "pip"], "--include", "-i", help="Packages to always include"
    ),
    exclude: List[str] = typer.Option(
        [], "--exclude", "-x", help="Packages to always exclude"
    ),
    export_name: Optional[str] = typer.Option(
        None, "--export-name", "-e", help="Name to use in export"
    ),
    channel: bool = typer.Option(
        False, "--channel", "-c", help="Add channel to conda dependencies"
    ),
    debug: bool = typer.Option(False, "--debug"),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback
    ),
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

    trio.run(
        partial(
            compute_and_export,
            cms,
            channel=channel,
            relax=relax,
            export_name=export_name,
        )
    )


async def compute_and_export(
    cms: ComputeMinimalSet,
    channel: bool,
    relax: RelaxLevel,
    export_name: Optional[str] = None,
):
    ms = await cms.compute()
    print(
        await ms.export(export_name=export_name, include_channel=channel, relax=relax)
    )
