"""Writer implementations for different changelog extensions."""

from __future__ import annotations

import typing
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile

if typing.TYPE_CHECKING:
    from changelog_gen.extractor import SectionDict


class Extension(Enum):
    """Supported changelog file extensions."""

    MD = "md"
    RST = "rst"


class BaseWriter:
    """Base implementation for a changelog file writer."""

    file_header_line_count = 0
    file_header = None
    extension = None

    def __init__(self: typing.Self, changelog: Path, issue_link: str | None = None, *, dry_run: bool = False) -> None:
        self.existing = []
        self.changelog = changelog
        if self.changelog.exists():
            lines = changelog.read_text().split("\n")
            self.existing = lines[self.file_header_line_count + 1 :]
        self.content = []
        self.dry_run = dry_run
        self.issue_link = issue_link

    def add_version(self: typing.Self, version: str) -> None:
        """Add a version string to changelog file."""
        self._add_version(version)

    def _add_version(self: typing.Self, version: str) -> None:
        raise NotImplementedError

    def consume(self: typing.Self, supported_sections: dict[str, str], sections: SectionDict) -> None:
        """Process sections and generate changelog file entries."""
        for section in sorted(supported_sections):
            if section not in sections:
                continue

            header = supported_sections[section]
            self.add_section(header, sections[section])

    def add_section(self: typing.Self, header: str, lines: dict[str, dict]) -> None:
        """Add a section to changelog file."""
        self._add_section_header(header)
        for issue_ref, details in sorted(lines.items()):
            description = details["description"]
            scope = details.get("scope")
            breaking = details.get("breaking", False)

            description = f"{scope} {description}" if scope else description
            description = f"**Breaking:** {description}" if breaking else description

            self._add_section_line(
                description,
                issue_ref,
            )
        self._post_section()

    def _add_section_header(self: typing.Self, header: str) -> None:
        raise NotImplementedError

    def _add_section_line(self: typing.Self, description: str, issue_ref: str) -> None:
        raise NotImplementedError

    def _post_section(self: typing.Self) -> None:
        pass

    def __str__(self: typing.Self) -> str:  # noqa: D105
        return "\n".join(self.content)

    def write(self: typing.Self) -> None:
        """Write file contents to destination."""
        self.content = [self.file_header, *self.content, *self.existing]
        self._write(self.content)

    def _write(self: typing.Self, content: list[str]) -> None:
        if self.dry_run:
            with NamedTemporaryFile("wb") as output_file:
                output_file.write(("\n".join(content)).encode("utf-8"))
        else:
            self.changelog.write_text("\n".join(content))


class MdWriter(BaseWriter):
    """Markdown writer implementation."""

    file_header_line_count = 1
    file_header = "# Changelog\n"
    extension = Extension.MD

    def _add_version(self: typing.Self, version: str) -> None:
        self.content.extend([f"## {version}", ""])

    def _add_section_header(self: typing.Self, header: str) -> None:
        self.content.extend([f"### {header}", ""])

    def _add_section_line(self: typing.Self, description: str, issue_ref: str) -> None:
        # Skip __{i}__ placeholder refs
        if issue_ref.startswith("__"):
            line = f"- {description}"
        elif self.issue_link:
            line = f"- {description} [[#$ISSUE_REF]({self.issue_link})]"
        else:
            line = f"- {description} [#$ISSUE_REF]"

        line = line.replace("$ISSUE_REF", issue_ref)

        self.content.append(line)

    def _post_section(self: typing.Self) -> None:
        self.content.append("")


class RstWriter(BaseWriter):
    """RST writer implementation."""

    file_header_line_count = 3
    file_header = "=========\nChangelog\n=========\n"
    extension = Extension.RST

    def __init__(self: typing.Self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._links = {}

    def __str__(self: typing.Self) -> str:  # noqa: D105
        return "\n".join(self.content + self.links)

    @property
    def links(self: typing.Self) -> list[str]:
        """Generate RST supported links for inclusion in changelog."""
        return [f".. _`{ref}`: {link}" for ref, link in sorted(self._links.items())]

    def _add_version(self: typing.Self, version: str) -> None:
        self.content.extend([version, "=" * len(version), ""])

    def _add_section_header(self: typing.Self, header: str) -> None:
        self.content.extend([header, "-" * len(header), ""])

    def _add_section_line(self: typing.Self, description: str, issue_ref: str) -> None:
        # Skip __{i}__ placeholder refs
        if issue_ref.startswith("__"):
            line = f"* {description}"
        elif self.issue_link:
            line = f"* {description} [`#$ISSUE_REF`_]"
            self._links[f"#{issue_ref}"] = self.issue_link.replace("$ISSUE_REF", issue_ref)
        else:
            line = f"* {description} [#$ISSUE_REF]"

        line = line.replace("$ISSUE_REF", issue_ref)

        self.content.extend([line, ""])

    def write(self: typing.Self) -> None:
        """Write contents to destination."""
        self.content = [self.file_header, *self.content, *self.existing, *self.links]
        self._write(self.content)


def new_writer(extension: Extension, issue_link: str | None = None, *, dry_run: bool = False) -> BaseWriter:
    """Generate a new writer based on the required extension."""
    changelog = Path(f"CHANGELOG.{extension.value}")

    if extension == Extension.MD:
        return MdWriter(changelog, dry_run=dry_run, issue_link=issue_link)
    if extension == Extension.RST:
        return RstWriter(changelog, dry_run=dry_run, issue_link=issue_link)

    msg = f'Changelog extension "{extension.value}" not supported.'
    raise ValueError(msg)
