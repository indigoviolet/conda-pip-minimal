import re
import subprocess
from typing import List

from semver.version import Version

from .cmd import Cmd


class EnsureCmdError(RuntimeError):
    pass


# Modified from https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
# - removed ^$
# - added ?P<full>
SEMVER_REGEX = r"(?P<full>(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?)"


def extract_semver(input: str) -> Version:
    if (match := re.search(SEMVER_REGEX, input)) is not None:
        return Version.parse(match.group("full"))
    else:
        raise EnsureCmdError(f"Cannot parse semver from {input=}")


async def ensure_cmd_version(
    cmd: Cmd, args: List[str], min_version: Version
) -> Version:
    try:
        version = extract_semver(await cmd(args))
    except subprocess.CalledProcessError:
        raise EnsureCmdError(f"Could not ensure {cmd=} {args=}")

    if not min_version.is_compatible(version):
        raise EnsureCmdError(
            f"Could not ensure {cmd=}, {min_version=}, found {version=}"
        )

    return version


CONDA = Cmd("conda")
CONDA_TREE = Cmd(CONDA.binary, ["tree"])
PIPDEPTREE = Cmd("pipdeptree")


CONDA_TREE_MIN_VERSION = Version.parse("1.1.0")
PIPDEPTREE_MIN_VERSION = Version.parse("2.3.3")


async def ensure_conda_tree(min_version=CONDA_TREE_MIN_VERSION):
    return await ensure_cmd_version(CONDA_TREE, ["--version"], min_version=min_version)


async def ensure_pipdeptree(min_version=PIPDEPTREE_MIN_VERSION):
    return await ensure_cmd_version(PIPDEPTREE, ["--version"], min_version=min_version)
