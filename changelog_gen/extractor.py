from __future__ import annotations

import re
import typing
from collections import defaultdict
from pathlib import Path

from changelog_gen import errors
from changelog_gen.vcs import Git
from changelog_gen.version import BumpVersion

SectionDict = dict[str, dict[str, dict[str, str]]]


class ReleaseNoteExtractor:
    """Parse release notes and generate section dictionaries."""

    def __init__(self: typing.Self, supported_sections: list[str], *, dry_run: bool = False) -> None:
        self.release_notes = Path("./release_notes")
        self.dry_run = dry_run
        self.supported_sections: dict[str, str] = supported_sections

        self.has_release_notes = self.release_notes.exists() and self.release_notes.is_dir()

    def extract(self: typing.Self, section_mapping: dict[str, str] | None = None) -> SectionDict:
        """Iterate over release note files extracting sections and issues."""
        section_mapping = section_mapping or {}

        sections = defaultdict(dict)

        if self.has_release_notes:
            # Extract changelog details from release note files.
            for issue in sorted(self.release_notes.iterdir()):
                if issue.is_file and not issue.name.startswith("."):
                    issue_ref, section = issue.name.split(".")
                    section = section_mapping.get(section, section)

                    breaking = False
                    if section.endswith("!"):
                        section = section[:-1]
                        breaking = True

                    contents = issue.read_text().strip()
                    if section not in self.supported_sections:
                        msg = f"Unsupported CHANGELOG section {section}, derived from `./release_notes/{issue.name}`"
                        raise errors.InvalidSectionError(msg)

                    sections[section][issue_ref] = {
                        "description": contents,
                        "breaking": breaking,
                    }

        latest_info = Git.get_latest_tag_info()
        logs = Git.get_logs(latest_info["current_tag"])

        # Build a conventional commit regex based on configured sections
        #   ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)
        types = "|".join(set(list(self.supported_sections.keys()) + list(section_mapping.keys())))
        reg = re.compile(rf"^({types}){{1}}(\([\w\-\.]+\))?(!)?: ([\w .]+)+([\s\S]*)")

        for i, log in enumerate(logs):
            m = reg.match(log)
            if m:
                section = m[1]
                scope = m[2]
                breaking = m[3] is not None
                message = m[4]
                details = m[5] or ""

                # Handle missing refs in commit message, skip link generation in writer
                issue_ref = f"__{i}__"
                breaking = breaking or "BREAKING CHANGE" in details
                for line in details.split("\n"):
                    m = re.match(r"Refs: #?([\w-]+)", line)
                    if m:
                        issue_ref = m[1]

                section = section_mapping.get(section, section)
                sections[section][issue_ref] = {
                    "description": message,
                    "breaking": breaking,
                    "scope": scope,
                }
        return sections

    def unique_issues(self: typing.Self, sections: SectionDict) -> list[str]:
        """Generate unique list of issue references."""
        issue_refs = set()
        for section, issues in sections.items():
            if section in self.supported_sections:
                issue_refs.update(issues.keys())
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


def extract_version_tag(sections: SectionDict, semver_mapping: dict[str, str]) -> str:
    """Generate new version tag based on changelog sections.

    Breaking changes: major
    Feature releases: minor
    Bugs/Fixes: patch

    """
    version_info_ = BumpVersion.get_version_info("patch")
    current = version_info_["current"]

    semvers = ["patch", "minor", "major"]
    semver = "patch"
    for section, section_issues in sections.items():
        if semvers.index(semver) < semvers.index(semver_mapping.get(section, "patch")):
            semver = semver_mapping.get(section, "patch")
        for issue in section_issues.values():
            if issue["breaking"]:
                semver = "major"

    if current.startswith("0."):
        # If currently on 0.X releases, downgrade semver by one, major -> minor etc.
        idx = semvers.index(semver)
        semver = semvers[max(idx - 1, 0)]

    version_info = BumpVersion.get_version_info(semver)

    return version_info["new"]
