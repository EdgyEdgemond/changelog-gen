"""Writer implementations for different changelog extensions."""

from __future__ import annotations

import logging
import typing
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile

if typing.TYPE_CHECKING:
    from changelog_gen import config
    from changelog_gen.extractor import Change, SectionDict


logger = logging.getLogger(__name__)


class Extension(Enum):
    """Supported changelog file extensions."""

    MD = "md"
    RST = "rst"


class BaseWriter:
    """Base implementation for a changelog file writer."""

    file_header_line_count = 0
    file_header = None
    extension = None

    def __init__(
        self: typing.Self,
        changelog: Path,
        cfg: config.Config,
        *,
        dry_run: bool = False,
    ) -> None:
        self.existing = []
        self.changelog = changelog
        if self.changelog.exists():
            lines = changelog.read_text().split("\n")
            self.existing = lines[self.file_header_line_count + 1 :]
        self.content = []
        self.dry_run = dry_run
        self.issue_link = cfg.issue_link
        self.commit_link = cfg.commit_link

    def add_version(self: typing.Self, version: str) -> None:
        """Add a version string to changelog file."""
        self._add_version(version)

    def _add_version(self: typing.Self, version: str) -> None:
        raise NotImplementedError

    def consume(self: typing.Self, type_headers: dict[str, str], sections: SectionDict) -> None:
        """Process sections and generate changelog file entries."""
        for header in type_headers.values():
            if header not in sections:
                continue
            # Remove processed headers to prevent rendering duplicate type -> header mappings
            changes = sections.pop(header)
            self.add_section(header, changes)

    def add_section(self: typing.Self, header: str, changes: dict[str, Change]) -> None:
        """Add a section to changelog file."""
        self._add_section_header(header)
        for change in sorted(changes.values()):
            description = f"{change.scope} {change.description}" if change.scope else change.description
            description = f"{self.bold_string('Breaking:')} {description}" if change.breaking else description
            description = f"{description} {change.authors}" if change.authors else description

            self._add_section_line(
                description,
                change,
            )
        self._post_section()

    def bold_string(self: typing.Self, string: str) -> str:
        """Render a string as bold."""
        return f"**{string.strip()}**"

    def _add_section_header(self: typing.Self, header: str) -> None:
        raise NotImplementedError

    def _add_section_line(self: typing.Self, description: str, change: Change) -> None:
        raise NotImplementedError

    def _post_section(self: typing.Self) -> None:
        pass

    def __str__(self: typing.Self) -> str:  # noqa: D105
        content = "\n".join(self.content)
        return f"\n\n{content}\n\n"

    def write(self: typing.Self) -> None:
        """Write file contents to destination."""
        self.content = [self.file_header, *self.content, *self.existing]
        self._write(self.content)

    def _write(self: typing.Self, content: list[str]) -> None:
        if self.dry_run:
            logger.warning("Would write to '%s'", self.changelog.name)
            with NamedTemporaryFile("wb") as output_file:
                output_file.write(("\n".join(content)).encode("utf-8"))
        else:
            logger.warning("Writing to '%s'", self.changelog.name)
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

    def _add_section_line(self: typing.Self, description: str, change: Change) -> None:
        # Skip __{i}__ placeholder refs
        if change.issue_ref.startswith("__"):
            line = f"- {description}"
        elif self.issue_link:
            line = f"- {description} [[#::issue_ref::]({self.issue_link})]"
        else:
            line = f"- {description} [#::issue_ref::]"

        if self.commit_link and change.commit_hash:
            line = f"{line} [[{change.short_hash}]({self.commit_link})]"

        line = line.replace("::issue_ref::", change.issue_ref)
        line = line.replace("::commit_hash::", change.commit_hash or "")

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
        content = "\n".join(self.content + self.links)
        return f"\n\n{content}\n\n"

    @property
    def links(self: typing.Self) -> list[str]:
        """Generate RST supported links for inclusion in changelog."""
        return [f".. _`{ref}`: {link}" for ref, link in sorted(self._links.items())]

    def _add_version(self: typing.Self, version: str) -> None:
        self.content.extend([version, "=" * len(version), ""])

    def _add_section_header(self: typing.Self, header: str) -> None:
        self.content.extend([header, "-" * len(header), ""])

    def _add_section_line(self: typing.Self, description: str, change: Change) -> None:
        # Skip __{i}__ placeholder refs
        if change.issue_ref.startswith("__"):
            line = f"* {description}"
        elif self.issue_link:
            line = f"* {description} [`#{change.issue_ref}`_]"
            self._links[f"#{change.issue_ref}"] = self.issue_link.replace("::issue_ref::", change.issue_ref)
        else:
            line = f"* {description} [#{change.issue_ref}]"

        if self.commit_link and change.commit_hash:
            line = f"{line} [`{change.short_hash}`_]"
            self._links[f"{change.short_hash}"] = self.commit_link.replace("::commit_hash::", change.commit_hash)

        self.content.extend([line, ""])

    def write(self: typing.Self) -> None:
        """Write contents to destination."""
        self.content = [self.file_header, *self.content, *self.existing, *self.links]
        self._write(self.content)


def new_writer(
    extension: Extension,
    cfg: config.Config,
    *,
    dry_run: bool = False,
) -> BaseWriter:
    """Generate a new writer based on the required extension."""
    changelog = Path(f"CHANGELOG.{extension.value}")

    if extension == Extension.MD:
        return MdWriter(changelog, cfg, dry_run=dry_run)
    if extension == Extension.RST:
        return RstWriter(changelog, cfg, dry_run=dry_run)

    msg = f'Changelog extension "{extension.value}" not supported.'
    raise ValueError(msg)
