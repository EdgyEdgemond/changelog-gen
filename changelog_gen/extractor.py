from collections import (
    OrderedDict,
    defaultdict,
)
from pathlib import Path

from changelog_gen import errors


SUPPORTED_SECTIONS = {
    "feat": "Features and Improvements",
    "fix": "Bug fixes",
}


class ReleaseNoteExtractor:
    def __init__(self, dry_run=False):
        self.release_notes = Path("./release_notes")
        self.dry_run = dry_run

        if not self.release_notes.exists() or not self.release_notes.is_dir():
            raise errors.NoReleaseNotesError("No release notes directory found.")

    def extract(self):
        sections = defaultdict(OrderedDict)

        # Extract changelog details from release note files.
        for issue in sorted(self.release_notes.iterdir()):
            if issue.is_file and not issue.name.startswith("."):
                ticket, section = issue.name.split(".")
                breaking = False
                if section.endswith("!"):
                    section = section[:-1]
                    breaking = True
                contents = issue.read_text().strip()
                if section not in SUPPORTED_SECTIONS:
                    raise errors.InvalidSectionError(
                        "Unsupported CHANGELOG section {section}".format(
                            section=section,
                        ),
                    )

                sections[section][ticket] = {
                    "description": contents,
                    "breaking": breaking,
                }

        return sections

    def clean(self):
        if not self.dry_run:
            for x in self.release_notes.iterdir():
                if x.is_file and not x.name.startswith("."):
                    x.unlink()
