import subprocess
from typing import Dict

from changelog_gen import errors


class BumpVersion:
    @classmethod
    def get_version_info(cls, semver: str) -> Dict[str, str]:
        try:
            describe_out = (
                subprocess.check_output(
                    ["bumpversion", semver, "--dry-run", "--list", "--allow-dirty"],
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
    def release(cls, version: str) -> None:
        subprocess.check_output(["bumpversion", "--new-version", version, "patch"])
