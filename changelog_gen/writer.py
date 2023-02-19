import typing
from pathlib import Path
from tempfile import NamedTemporaryFile

if typing.TYPE_CHECKING:
    from changelog_gen.extractor import SectionDict

SUPPORTED_EXTENSIONS = ["md", "rst"]


class BaseWriter:
    file_header_line_count = 0
    file_header = None
    extension = None

    def __init__(self, changelog: Path, dry_run: bool = False, issue_link: str | None = None) -> None:
        self.existing = []
        self.changelog = changelog
        if self.changelog.exists():
            lines = changelog.read_text().split("\n")
            self.existing = lines[self.file_header_line_count + 1 :]
        self.content = []
        self.dry_run = dry_run
        self.issue_link = issue_link

    def add_version(self, version: str) -> None:
        self._add_version(version)

    def _add_version(self, version: str) -> None:
        raise NotImplementedError

    def consume(self, supported_sections: dict[str, str], sections: "SectionDict") -> None:
        for section in sorted(supported_sections):
            if section not in sections:
                continue

            header = supported_sections[section]
            self.add_section(header, {k: v["description"] for k, v in sections[section].items()})

    def add_section(self, header: str, lines: list[str]) -> None:
        self._add_section_header(header)
        for issue_ref, description in sorted(lines.items()):
            self._add_section_line(description, issue_ref)
        self._post_section()

    def _add_section_header(self, header: str) -> None:
        raise NotImplementedError

    def _add_section_line(self, description: str, issue_ref: str) -> None:
        raise NotImplementedError

    def _post_section(self) -> None:
        pass

    def __str__(self) -> str:
        return "\n".join(self.content)

    def write(self) -> None:
        self.content = [self.file_header, *self.content, *self.existing]
        self._write(self.content)

    def _write(self, content: list[str]) -> None:
        if self.dry_run:
            with NamedTemporaryFile("wb") as output_file:
                output_file.write(("\n".join(content)).encode("utf-8"))
        else:
            self.changelog.write_text("\n".join(content))


class MdWriter(BaseWriter):
    file_header_line_count = 1
    file_header = "# Changelog\n"
    extension = "md"

    def _add_version(self, version: str) -> None:
        self.content.extend([f"## {version}", ""])

    def _add_section_header(self, header: str) -> None:
        self.content.extend([f"### {header}", ""])

    def _add_section_line(self, description: str, issue_ref: str) -> None:
        if self.issue_link:
            line = "- {} [[#{}]({})]".format(
                description,
                issue_ref,
                self.issue_link,
            )
        else:
            line = f"- {description} [#{issue_ref}]"
        line = line.format(issue_ref=issue_ref)

        self.content.append(line)

    def _post_section(self) -> None:
        self.content.append("")


class RstWriter(BaseWriter):
    file_header_line_count = 3
    file_header = "=========\nChangelog\n=========\n"
    extension = "rst"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._links = {}

    def __str__(self) -> str:
        return "\n".join(self.content + self.links)

    @property
    def links(self) -> list[str]:
        return [f".. _`{ref}`: {link}" for ref, link in sorted(self._links.items())]

    def _add_version(self, version: str) -> None:
        self.content.extend([version, "=" * len(version), ""])

    def _add_section_header(self, header: str) -> None:
        self.content.extend([header, "-" * len(header), ""])

    def _add_section_line(self, description: str, issue_ref: str) -> None:
        if self.issue_link:
            line = f"* {description} [`#{issue_ref}`_]"
            self._links[f"#{issue_ref}"] = self.issue_link.format(issue_ref=issue_ref)
        else:
            line = f"* {description} [#{issue_ref}]"
        line = line.format(issue_ref=issue_ref)

        self.content.extend([line, ""])

    def write(self) -> None:
        self.content = [self.file_header, *self.content, *self.existing, *self.links]
        self._write(self.content)


def new_writer(extension: str, dry_run: bool = False, issue_link: str | None = None) -> BaseWriter:
    changelog = Path(f"CHANGELOG.{extension}")

    if extension == "md":
        return MdWriter(changelog, dry_run=dry_run, issue_link=issue_link)
    if extension == "rst":
        return RstWriter(changelog, dry_run=dry_run, issue_link=issue_link)

    msg = 'Changelog extension "{extension}" not supported.'.format(
        extension=extension,
    )
    raise ValueError(msg)
