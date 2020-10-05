from pathlib import Path
from tempfile import NamedTemporaryFile


SUPPORTED_EXTENSIONS = ["md", "rst"]


class BaseWriter:
    file_header_line_count = 0
    file_header = None
    extension = None

    def __init__(self, changelog, dry_run=False, issue_link=None):
        self.existing = []
        self.changelog = changelog
        if self.changelog.exists():
            lines = changelog.read_text().split("\n")
            self.existing = lines[self.file_header_line_count + 1:]
        self.content = []
        self.dry_run = dry_run
        self.issue_link = issue_link

    def add_version(self, version):
        self._add_version(version)

    def _add_version(self, version):
        raise NotImplementedError

    def add_section(self, header, lines):
        self._add_section_header(header)
        for issue_ref, description in sorted(lines.items()):
            self._add_section_line(description, issue_ref)
        self._post_section()

    def _add_section_header(self, header):
        raise NotImplementedError

    def _add_section_line(self, description, issue_ref):
        raise NotImplementedError

    def _post_section(self):
        pass

    def __str__(self):
        return "\n".join(self.content)

    def write(self):
        self.content = [self.file_header] + self.content + self.existing
        self._write(self.content)

    def _write(self, content):
        if self.dry_run:
            with NamedTemporaryFile("wb") as output_file:
                output_file.write(("\n".join(content)).encode("utf-8"))
        else:
            self.changelog.write_text("\n".join(content))


class MdWriter(BaseWriter):
    file_header_line_count = 1
    file_header = "# Changelog\n"
    extension = "md"

    def _add_version(self, version):
        self.content.extend(["## {version}".format(version=version), ""])

    def _add_section_header(self, header):
        self.content.extend(["### {header}".format(header=header), ""])

    def _add_section_line(self, description, issue_ref):
        if self.issue_link:
            line = "- {} [[#{}]({})]".format(
                description,
                issue_ref,
                self.issue_link,
            )
        else:
            line = "- {} [#{}]".format(description, issue_ref)
        line = line.format(issue_ref=issue_ref)

        self.content.append(line)

    def _post_section(self):
        self.content.append("")


class RstWriter(BaseWriter):
    file_header_line_count = 3
    file_header = "=========\nChangelog\n=========\n"
    extension = "rst"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._links = {}

    def __str__(self):
        return "\n".join(self.content + self.links)

    @property
    def links(self):
        return [
            ".. _`{}`: {}".format(ref, link)
            for ref, link in sorted(self._links.items())
        ]

    def _add_version(self, version):
        self.content.extend([version, "=" * len(version), ""])

    def _add_section_header(self, header):
        self.content.extend([header, "-" * len(header), ""])

    def _add_section_line(self, description, issue_ref):
        if self.issue_link:
            line = "* {} [`#{}`_]".format(description, issue_ref)
            self._links["#{}".format(issue_ref)] = self.issue_link.format(issue_ref=issue_ref)
        else:
            line = "* {} [#{}]".format(description, issue_ref)
        line = line.format(issue_ref=issue_ref)

        self.content.extend([line, ""])

    def write(self):
        self.content = [self.file_header] + self.content + self.existing + self.links
        self._write(self.content)


def new_writer(extension, dry_run=False, issue_link=None):
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            'Changelog extension "{extension}" not supported.'.format(
                extension=extension,
            ),
        )

    changelog = Path("CHANGELOG.{extension}".format(extension=extension))

    if extension == "md":
        return MdWriter(changelog, dry_run=dry_run, issue_link=issue_link)
    if extension == "rst":
        return RstWriter(changelog, dry_run=dry_run, issue_link=issue_link)
