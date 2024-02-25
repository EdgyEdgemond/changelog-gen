from __future__ import annotations

import subprocess
from typing import TypeVar

from changelog_gen import errors

T = TypeVar("T", bound="Git")


class Git:
    """VCS implementation for git repositories."""

    @classmethod
    def get_latest_tag_info(cls: type[T]) -> dict[str, str | int]:
        """Extract latest tag info from git."""
        describe_out = None
        for tags in ["[0-9]*", "v[0-9]*"]:
            try:
                describe_out = (
                    subprocess.check_output(
                        [  # noqa: S603, S607
                            "git",
                            "describe",
                            "--tags",
                            "--dirty",
                            "--long",
                            "--match",
                            tags,
                        ],
                        stderr=subprocess.STDOUT,
                    )
                    .decode()
                    .strip()
                    .split("-")
                )
            except subprocess.CalledProcessError:  # noqa: PERF203
                pass
            else:
                break
        else:
            msg = "Unable to get version number from git tags."
            raise errors.VcsError(msg)

        try:
            rev_parse_out = (
                subprocess.check_output(
                    [  # noqa: S603, S607
                        "git",
                        "rev-parse",
                        "--tags",
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
            msg = "Unable to get current git branch."
            raise errors.VcsError(msg) from e

        info = {
            "dirty": False,
            "branch": rev_parse_out[-1],
        }

        if describe_out[-1].strip() == "dirty":
            info["dirty"] = True
            describe_out.pop()

        info["commit_sha"] = describe_out.pop().lstrip("g")
        info["distance_to_latest_tag"] = int(describe_out.pop())
        tag = "-".join(describe_out)
        info["current_version"] = tag.lstrip("v")
        info["current_tag"] = tag

        return info

    @classmethod
    def get_logs(cls: type[T], tag: str) -> list:
        """Fetch logs since last tag."""
        return [
            m.split(":", 2)
            for m in (
                subprocess.check_output(
                    [  # noqa: S603, S607
                        "git",
                        "log",
                        f"{tag}..HEAD",  # between last tag and HEAd
                        "--format=%h:%H:%B",  # message only
                        "-z",  # separate with \x00 rather than \n to differentiate multiline commits
                    ],
                )
                .decode()
                .strip()
                .split("\x00")
            )
            if m
        ]

    @classmethod
    def add_path(cls: type[T], path: str) -> None:
        """Add path to git repository."""
        subprocess.check_output(["git", "add", "--update", path])  # noqa: S603, S607

    @classmethod
    def commit(cls: type[T], version: str) -> None:
        """Commit changes to git repository."""
        subprocess.check_output(
            ["git", "commit", "-m", f"Update CHANGELOG for {version}"],  # noqa: S603, S607
        )

    @classmethod
    def revert(cls: type[T]) -> None:
        """Revert a commit."""
        subprocess.check_output(["git", "reset", "HEAD~1", "--hard"])  # noqa: S603, S607
