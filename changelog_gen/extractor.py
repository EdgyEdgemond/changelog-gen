from collections import (
    OrderedDict,
    defaultdict,
)
from pathlib import Path
from typing import (
    Dict,
    List,
)

from changelog_gen import errors
from changelog_gen.version import BumpVersion


# Dict[section, Dict[issue, {description: ..., breaking: ...}]]
SectionDict = Dict[str, Dict[str, Dict[str, str]]]


class ReleaseNoteExtractor:
    def __init__(self, supported_sections, dry_run=False):
        self.release_notes = Path("./release_notes")
        self.dry_run = dry_run
        # Dict[extension, header]
        self.supported_sections: Dict[str, str] = supported_sections

        if not self.release_notes.exists() or not self.release_notes.is_dir():
            raise errors.NoReleaseNotesError("No release notes directory found.")

    def extract(self, section_mapping=None) -> SectionDict:
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
                    raise errors.InvalidSectionError(
                        "Unsupported CHANGELOG section {section}".format(
                            section=section,
                        ),
                    )

                sections[section][issue_ref] = {
                    "description": contents,
                    "breaking": breaking,
                }

        return sections

    def unique_issues(self, sections: SectionDict) -> List[str]:
        issue_refs = set()
        for section, issues in sections.items():
            if section in self.supported_sections:
                issue_refs.update(issues.keys())
        return list(issue_refs)

    def clean(self):
        if not self.dry_run:
            for x in self.release_notes.iterdir():
                if x.is_file and not x.name.startswith("."):
                    x.unlink()


def extract_version_tag(sections: SectionDict) -> str:
    semver = "minor" if "feat" in sections else "patch"
    for section_issues in sections.values():
        for issue in section_issues.values():
            if issue["breaking"]:
                semver = "major"
    version_info = BumpVersion.get_version_info(semver)

    return version_info["new"]
