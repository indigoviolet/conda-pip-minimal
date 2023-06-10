from enum import Enum
from typing import Optional

from semver.version import Version


class RelaxLevel(Enum):
    NONE = "none"
    MAJOR = "major"
    MINOR = "minor"
    FULL = "full"


def version_string(
    version: Optional[str], *, op: str = "==", how: RelaxLevel = RelaxLevel.MINOR
) -> str:
    if version is None:
        return ""
    if how == RelaxLevel.NONE:
        return ""
    if how == RelaxLevel.FULL:
        return f"{op}{version}"

    parsed_version = Version.parse(version)
    if how == RelaxLevel.MINOR:
        return f"{op}{parsed_version.major}.{parsed_version.minor}.*"
    elif how == RelaxLevel.MAJOR:
        return f"{op}{parsed_version.major}.*"
