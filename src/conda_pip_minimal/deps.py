from __future__ import annotations

from .cmd import Cmd
import re
import semver
import subprocess
from typing import List


class EnsureCmdError(RuntimeError):
    pass


# Modified from https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
# - removed ^$
# - added ?P<full>
SEMVER_REGEX = r"(?P<full>(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?)"


def extract_semver(input: str) -> str:
    if (match := re.search(SEMVER_REGEX, input)) is not None:
        return match.group("full")
    else:
        raise EnsureCmdError(f"Cannot parse semver from {input=}")


async def ensure_cmd_version(cmd: Cmd, args: List[str], min_version: str) -> str:
    try:
        version = extract_semver(await cmd(args))
    except subprocess.CalledProcessError:
        raise EnsureCmdError(f"Could not ensure {cmd=} {args=}")

    if semver.compare(min_version, version) > 0:
        raise EnsureCmdError(
            f"Could not ensure {cmd=}, {min_version=}, found {version=}"
        )

    return version


CONDA = Cmd("conda")
CONDA_TREE = Cmd(CONDA.binary, ["tree"])
PIPDEPTREE = Cmd("pipdeptree")


CONDA_TREE_MIN_VERSION: str = "1.0.4"
PIPDEPTREE_MIN_VERSION: str = "2.3.1"


async def ensure_conda_tree(min_version: str = CONDA_TREE_MIN_VERSION):
    return await ensure_cmd_version(CONDA_TREE, ["--version"], min_version=min_version)


async def ensure_pipdeptree(min_version: str = PIPDEPTREE_MIN_VERSION):
    return await ensure_cmd_version(PIPDEPTREE, ["--version"], min_version=min_version)
