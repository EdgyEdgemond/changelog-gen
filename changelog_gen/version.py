import logging
import re
import subprocess
from typing import TypeVar
from warnings import warn

try:
    from bumpversion import bump  # noqa: F401
except ImportError:  # pragma: no cover
    bump_library = "bump2version"
    warn(
        "bump2version deprecated, recommend installing extras[bump-my-version].",
        DeprecationWarning,
        stacklevel=2,
    )
else:
    bump_library = "bump-my-version"

from changelog_gen import errors

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BumpVersion")


def parse_bump_my_version_info(semver: str, lines: list[str]) -> tuple[str, str]:
    """Parse output from bump-my-version info command."""
    reg = re.compile(rf".*({semver}) [-]+ (.*)")

    current = lines[0].split(" -- ")[0].strip()
    for line in lines:
        m = reg.match(line)
        if m:
            new = m[2].strip()

    return current, new


def parse_bump2version_info(_semver: str, lines: list[str]) -> tuple[str, str]:
    """Parse output from bump2version info command."""
    bumpversion_data = {v.split("=")[0].strip(): v.split("=")[1].strip() for v in lines if "_version" in v}

    return bumpversion_data["current_version"], bumpversion_data["new_version"]


def generate_verbosity(verbose: int = 0) -> list[str]:
    """Generate verbose flags correctly for each supported bumpversion library."""
    return ["--verbose"] * verbose if bump_library == "bump2version" else [f"-{'v' * verbose}"]


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
    def __init__(self: T, verbose: int = 0, *, allow_dirty: bool = False, dry_run: bool = False) -> None:
        self.verbose = verbose
        self.allow_dirty = allow_dirty
        self.dry_run = dry_run

    def _version_info_cmd(self: T, semver: str) -> list[str]:
        command = commands[bump_library]["get_version_info"]
        return [c.replace("SEMVER", semver) for c in command]

    def _release_cmd(self: T, version: str) -> list[str]:
        command = commands[bump_library]["release"]
        args = [c.replace("VERSION", version) for c in command]
        if self.verbose:
            args.extend(generate_verbosity(self.verbose))
        if self.dry_run:
            args.append("--dry-run")
        if self.allow_dirty:
            args.append("--allow-dirty")
        return args

    def get_version_info(self: T, semver: str) -> dict[str, str]:
        """Get version info for a semver release."""
        try:
            describe_out = (
                subprocess.check_output(
                    self._version_info_cmd(semver),  # noqa: S603
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            logger.warning(e.output, self.verbose)
            msg = "Unable to get version data from bumpversion."
            raise errors.VersionDetectionError(msg) from e

        current, new = commands[bump_library]["parser"](semver, describe_out)
        return {
            "current": current,
            "new": new,
        }

    def release(self: T, version: str) -> None:
        """Generate new release."""
        try:
            describe_out = (
                subprocess.check_output(
                    self._release_cmd(version),  # noqa: S603
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            for line in e.output.decode().split("\n"):
                logger.warning(line.strip())
            raise

        for line in describe_out:
            logger.warning(line)
