import re
import subprocess
from typing import TypeVar
from warnings import warn

try:
    from bumpversion import bump  # noqa: F401
except ImportError:
    bump_library = "bump2version"
    warn(
        "bump2version deprecated, recommend installing extras[bump-my-version].",
        DeprecationWarning,
        stacklevel=2,
    )
else:
    bump_library = "bump-my-version"

from changelog_gen import errors

T = TypeVar("T", bound="BumpVersion")


def parse_bump_my_version_info(semver: str, lines: list[str]) -> tuple[str, str]:
    """Parse output from bump-my-version info command."""
    reg = re.compile(rf".*({semver}) [-]+ (.*)")

    current = lines[0].split(" -- ")[0]
    for line in lines:
        m = reg.match(line)
        if m:
            new = m[2]

    return current, new


def parse_bump2version_info(_semver: str, lines: list[str]) -> tuple[str, str]:
    """Parse output from bump2version info command."""
    bumpversion_data = {v.split("=")[0]: v.split("=")[1] for v in lines if "_version" in v}

    return bumpversion_data["current_version"], bumpversion_data["new_version"]


commands = {
    "bump-my-version": {
        "get_version_info": ["bump-my-version", "show-bump", "--ascii"],
        "release": ["bump-my-version", "bump", "patch", "--new-version", "VERSION"],
        "parser": parse_bump_my_version_info,
    },
    "bump2version": {
        "get_version_info": ["bumpversion", "SEMVER", "--dry-run", "--list", "--allow-dirty"],
        "release": ["bumpversion", "patch", "--new-version", "VERSION"],
        "parser": parse_bump2version_info,
    },
}


class BumpVersion:  # noqa: D101
    @classmethod
    def _version_info_cmd(cls: type[T], semver: str) -> list[str]:
        command = commands[bump_library]["get_version_info"]
        return [c.replace("SEMVER", semver) for c in command]

    @classmethod
    def _release_cmd(cls: type[T], version: str) -> list[str]:
        command = commands[bump_library]["release"]
        return [c.replace("VERSION", version) for c in command]

    @classmethod
    def get_version_info(cls: type[T], semver: str) -> dict[str, str]:
        """Get version info for a semver release."""
        try:
            describe_out = (
                subprocess.check_output(
                    cls._version_info_cmd(semver),  # noqa: S603
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            msg = "Unable to get version data from bumpversion."
            raise errors.VersionDetectionError(msg) from e

        current, new = commands[bump_library]["parser"](semver, describe_out)
        return {
            "current": current,
            "new": new,
        }

    @classmethod
    def release(cls: type[T], version: str) -> None:
        """Generate new release."""
        subprocess.check_output(
            cls._release_cmd(version),  # noqa: S603
        )
