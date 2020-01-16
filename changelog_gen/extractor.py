from collections import defaultdict
from pathlib import Path


SUPPORTED_SECTIONS = {
    "feature": "Features and Improvements",
    "bugfix": "Bug fixes",
}


class ReleaseNoteExtractor:
    def extract(self):
        release_notes = Path("./release_notes")

        if not release_notes.exists() or not release_notes.is_dir:
            click.echo("No release notes directory found.")
            raise click.Abort()

        sections = defaultdict(dict)

        # Extract changelog details from release note files.
        for issue in release_notes.iterdir():
            if issue.is_file and not issue.name.startswith("."):
                ticket, section = issue.name.split(".")
                contents = issue.read_text().strip()
                if section not in SUPPORTED_SECTIONS:
                    click.echo(
                        "Unsupported CHANGELOG section {section}".format(
                            section=section
                        )
                    )
                    raise click.Abort()

                sections[section][ticket] = contents

        return sections
