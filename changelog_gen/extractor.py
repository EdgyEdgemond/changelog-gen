from __future__ import annotations

import typing
from collections import (
    OrderedDict,
    defaultdict,
)
from pathlib import Path

from changelog_gen import errors
from changelog_gen.version import BumpVersion

SectionDict = dict[str, dict[str, dict[str, str]]]


class ReleaseNoteExtractor:
    """Parse release notes and generate section dictionaries."""

    def __init__(self: typing.Self, supported_sections: list[str], *, dry_run: bool = False) -> None:
        self.release_notes = Path("./release_notes")
        self.dry_run = dry_run
        self.supported_sections: dict[str, str] = supported_sections

        if not self.release_notes.exists() or not self.release_notes.is_dir():
            msg = "No release notes directory found."
            raise errors.NoReleaseNotesError(msg)

    def extract(self: typing.Self, section_mapping: dict[str, str] | None = None) -> SectionDict:
        """Iterate over release note files extracting sections and issues."""
        section_mapping = section_mapping or {}

        sections = defaultdict(OrderedDict)

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
                    msg = f"Unsupported CHANGELOG section {section}"
                    raise errors.InvalidSectionError(msg)

                sections[section][issue_ref] = {
                    "description": contents,
                    "breaking": breaking,
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
        if not self.dry_run:
            for x in self.release_notes.iterdir():
                if x.is_file and not x.name.startswith("."):
                    x.unlink()


def extract_version_tag(sections: SectionDict) -> str:
    """Generate new version tag based on changelog sections.

    Breaking changes: major
    Feature releases: minor
    Bugs/Fixes: patch

    """
    # TODO(edgy): In the case of 0.x releases, everything should be one semver lower.
    # https://github.com/EdgyEdgemond/changelog-gen/issues/50
    semver = "minor" if "feat" in sections else "patch"
    for section_issues in sections.values():
        for issue in section_issues.values():
            if issue["breaking"]:
                semver = "major"
    version_info = BumpVersion.get_version_info(semver)

    return version_info["new"]
