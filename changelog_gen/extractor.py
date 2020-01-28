from collections import (
    OrderedDict,
    defaultdict,
)
from pathlib import Path

from changelog_gen import errors


class ReleaseNoteExtractor:
    def __init__(self, supported_sections, dry_run=False):
        self.release_notes = Path("./release_notes")
        self.dry_run = dry_run
        self.supported_sections = supported_sections

        if not self.release_notes.exists() or not self.release_notes.is_dir():
            raise errors.NoReleaseNotesError("No release notes directory found.")

    def extract(self, section_mapping=None):
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

    def clean(self):
        if not self.dry_run:
            for x in self.release_notes.iterdir():
                if x.is_file and not x.name.startswith("."):
                    x.unlink()
