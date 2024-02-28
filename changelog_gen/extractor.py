from __future__ import annotations

import dataclasses
import re
import typing
from collections import defaultdict
from pathlib import Path
from warnings import warn

from changelog_gen import config, errors

if typing.TYPE_CHECKING:
    from changelog_gen.vcs import Git
    from changelog_gen.version import BumpVersion


@dataclasses.dataclass
class Change:  # noqa: D101
    issue_ref: str
    description: str
    commit_type: str

    authors: str = ""
    scope: str = ""
    breaking: bool = False
    short_hash: str | None = None
    commit_hash: str | None = None

    def __lt__(self: typing.Self, other: Change) -> bool:  # noqa: D105
        s = (not self.breaking, self.scope.lower() if self.scope else "zzz", self.issue_ref.lower())
        o = (not other.breaking, other.scope.lower() if other.scope else "zzz", other.issue_ref.lower())
        return s < o


SectionDict = dict[str, dict[str, Change]]


class ReleaseNoteExtractor:
    """Parse release notes and generate section dictionaries."""

    def __init__(self: typing.Self, cfg: config.Config, git: Git, *, dry_run: bool = False) -> None:
        self.release_notes = Path("./release_notes")
        self.dry_run = dry_run
        self.type_headers = cfg.type_headers
        self.verbose = cfg.verbose
        self.git = git

        self.has_release_notes = self.release_notes.exists() and self.release_notes.is_dir()

    def _extract_release_notes(
        self: typing.Self,
        sections: dict[str, dict],
    ) -> None:
        warn(
            "`release_notes` support will be dropped in a future version, please migrate to conventional commits.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Extract changelog details from release note files.
        for issue in sorted(self.release_notes.iterdir()):
            if issue.is_file and not issue.name.startswith("."):
                issue_ref, commit_type = issue.name.split(".")

                breaking = False
                if commit_type.endswith("!"):
                    commit_type = commit_type[:-1]
                    breaking = True

                header = self.type_headers.get(commit_type, commit_type)

                contents = issue.read_text().strip()
                if commit_type not in self.type_headers:
                    msg = (
                        f"Unsupported CHANGELOG commit type {commit_type}, derived from `./release_notes/{issue.name}`"
                    )
                    raise errors.InvalidSectionError(msg)

                sections[header][issue_ref] = Change(
                    description=contents,
                    issue_ref=issue_ref,
                    breaking=breaking,
                    commit_type=commit_type,
                )

    def _extract_commit_logs(
        self: typing.Self,
        sections: dict[str, dict],
    ) -> None:
        latest_info = self.git.get_latest_tag_info()
        logs = self.git.get_logs(latest_info["current_tag"])

        # Build a conventional commit regex based on configured sections
        #   ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)
        types = "|".join(self.type_headers.keys())
        reg = re.compile(rf"^({types}){{1}}(\([\w\-\.]+\))?(!)?: ([\w .]+)+([\s\S]*)")

        for i, (short_hash, commit_hash, log) in enumerate(logs):
            m = reg.match(log)
            if m:
                commit_type = m[1]
                scope = m[2] or ""
                breaking = m[3] is not None
                message = m[4]
                details = m[5] or ""

                # Handle missing refs in commit message, skip link generation in writer
                issue_ref = f"__{i}__"
                breaking = breaking or "BREAKING CHANGE" in details

                change = Change(
                    description=message,
                    issue_ref=issue_ref,
                    breaking=breaking,
                    scope=scope,
                    short_hash=short_hash,
                    commit_hash=commit_hash,
                    commit_type=commit_type,
                )

                for line in details.split("\n"):
                    for target, pattern in [
                        ("issue_ref", r"Refs: #?([\w-]+)"),
                        ("authors", r"Authors: (.*)"),
                    ]:
                        m = re.match(pattern, line)
                        if m:
                            setattr(change, target, m[1])

                header = self.type_headers.get(commit_type, commit_type)
                sections[header][change.issue_ref] = change

    def extract(self: typing.Self) -> SectionDict:
        """Iterate over release note files extracting sections and issues."""
        sections = defaultdict(dict)

        if self.has_release_notes:
            self._extract_release_notes(sections)

        self._extract_commit_logs(sections)

        return sections

    def unique_issues(self: typing.Self, sections: SectionDict) -> list[str]:
        """Generate unique list of issue references."""
        issue_refs = set()
        issue_refs = {
            issue.issue_ref
            for issues in sections.values()
            for issue in issues.values()
            if issue.commit_type in self.type_headers
        }
        return sorted(issue_refs)

    def clean(self: typing.Self) -> None:
        """Remove parsed release not files.

        On dry_run, leave files where they are as they haven't been written to
        a changelog.
        """
        if not self.dry_run and self.release_notes.exists():
            for x in self.release_notes.iterdir():
                if x.is_file and not x.name.startswith("."):
                    x.unlink()


def extract_version_tag(sections: SectionDict, cfg: config.Config, bv: BumpVersion) -> str:
    """Generate new version tag based on changelog sections.

    Breaking changes: major
    Feature releases: minor
    Bugs/Fixes: patch

    """
    semver_mapping = cfg.semver_mapping
    version_info_ = bv.get_version_info("patch")
    current = version_info_["current"]

    semvers = ["patch", "minor", "major"]
    semver = "patch"
    for section_issues in sections.values():
        for issue in section_issues.values():
            if semvers.index(semver) < semvers.index(semver_mapping.get(issue.commit_type, "patch")):
                semver = semver_mapping.get(issue.commit_type, "patch")
            if issue.breaking:
                semver = "major"

    if current.startswith("0."):
        # If currently on 0.X releases, downgrade semver by one, major -> minor etc.
        idx = semvers.index(semver)
        semver = semvers[max(idx - 1, 0)]

    version_info = bv.get_version_info(semver)

    return version_info["new"]
