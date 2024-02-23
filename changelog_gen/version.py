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
                    ["bumpversion", semver, "--dry-run", "--list", "--allow-dirty"],  # noqa: S603, S607
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            msg = "Unable to get version data from bumpversion."
            raise errors.VersionDetectionError(msg) from e

        bumpversion_data = {v.split("=")[0]: v.split("=")[1] for v in describe_out}

        return {
            "current": bumpversion_data["current_version"],
            "new": bumpversion_data["new_version"],
        }

    @classmethod
    def release(cls: type[T], version: str) -> None:
        """Generate new release."""
        subprocess.check_output(["bumpversion", "--new-version", version, "patch"])  # noqa: S603, S607
