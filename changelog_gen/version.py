import re
import subprocess
from typing import TypeVar

from changelog_gen import errors

T = TypeVar("T", bound="BumpVersion")


class BumpVersion:  # noqa: D101
    @classmethod
    def get_version_info(cls: type[T], semver: str) -> dict[str, str]:
        """Get version info for a semver release."""
        try:
            describe_out = (
                subprocess.check_output(
                    ["bump-my-version", "show-bump", "--ascii"],  # noqa: S603, S607
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            msg = "Unable to get version data from bumpversion."
            raise errors.VersionDetectionError(msg) from e

        reg = re.compile(rf".*({semver}) [-]+ (.*)")

        current = describe_out[0].split(" -- ")[0]
        for line in describe_out:
            m = reg.match(line)
            if m:
                new = m[2]

        return {
            "current": current,
            "new": new,
        }

    @classmethod
    def release(cls: type[T], version: str) -> None:
        """Generate new release."""
        subprocess.check_output(["bump-my-version", "bump", "--new-version", version, "patch"])  # noqa: S603, S607
