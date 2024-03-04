from __future__ import annotations

import logging
import subprocess
from typing import TypeVar

from changelog_gen import errors

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Git")


class Git:
    """VCS implementation for git repositories."""

    def __init__(self: T, *, commit: bool = True, dry_run: bool = False) -> None:
        self._commit = commit
        self.dry_run = dry_run

    def get_current_info(self: T) -> dict[str, str]:
        """Get current state info from git."""
        changed_files = (
            subprocess.check_output(
                ["git", "status", "-s"],  # noqa: S603, S607
                stderr=subprocess.STDOUT,
            )
            .decode()
            .strip()
            .split("\n")
        )

        try:
            branch = (
                subprocess.check_output(
                    [  # noqa: S603, S607
                        "git",
                        "rev-parse",
                        "--abbrev-ref",
                        "HEAD",
                    ],
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            msg = (
                f"Unable to get current git branch: {e.output.decode().strip()}"
                if e.output
                else "Unable to get current git branch."
            )
            raise errors.VcsError(msg) from e

        return {
            "dirty": changed_files != [""],  # Any changed files == dirty
            "branch": branch[0],
        }

    def find_tag(self: T, version_string: str) -> str | None:
        """Find a version tag given the version string.

        Given a version string `0.1.2` find the version tag `v0.1.2`, `0.1.2` etc.
        """
        tag = (
            subprocess.check_output(
                [  # noqa: S603, S607
                    "git",
                    "tag",
                    "-n",
                    "--format='%(refname:short)'",
                    rf"*{version_string}",
                ],
                stderr=subprocess.STDOUT,
            )
            .decode()
            .strip()
        )

        return tag.strip("'") or None

    def get_logs(self: T, tag: str | None) -> list:
        """Fetch logs since last tag."""
        args = [
            "git",
            "log",
            "--format=%h:%H:%B",  # message only
            "-z",  # separate with \x00 rather than \n to differentiate multiline commits
        ]
        if tag:
            args.append(f"{tag}..HEAD")
        return [
            m.split(":", 2)
            for m in (
                subprocess.check_output(args)  # noqa: S603
                .decode()
                .strip()
                .split("\x00")
            )
            if m
        ]

    def add_path(self: T, path: str) -> None:
        """Add path to git repository."""
        if self.dry_run:
            logger.warning("  Would add path '%s' to Git", path)
            return
        subprocess.check_output(["git", "add", "--update", path])  # noqa: S603, S607

    def commit(self: T, version: str, paths: list[str] | None = None) -> None:
        """Commit changes to git repository."""
        logger.warning("Would prepare Git commit")
        paths = paths or []

        for path in paths:
            self.add_path(path)

        if self.dry_run or not self._commit:
            logger.warning("  Would commit to Git with message 'Update CHANGELOG for %s'", version)
            return

        try:
            subprocess.check_output(
                ["git", "commit", "-m", f"Update CHANGELOG for {version}"],  # noqa: S603, S607
            )
        except subprocess.CalledProcessError as e:
            msg = f"Unable to commit: {e.output.decode().strip()}" if e.output else "Unable to commit."
            raise errors.VcsError(msg) from e

    def revert(self: T) -> None:
        """Revert a commit."""
        if self.dry_run:
            logger.warning("Would revert commit in Git")
            return
        subprocess.check_output(["git", "reset", "HEAD~1", "--hard"])  # noqa: S603, S607
