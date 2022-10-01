from __future__ import annotations

from .version import RelaxLevel
from pathlib import Path
import typer
from typing import List, Optional

from .conda_env import CondaEnvSpec
from .min import ComputeMinimalSet


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
):
    if prefix is not None and name is not None:
        print(f"Exactly one of --prefix or --name must be provided {prefix=} {name=}")
        raise typer.Exit()

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
    ms = cms.compute()
    print(ms.export(include_channel=channel, relax=relax))


if __name__ == "__main__":
    typer.run(main)
