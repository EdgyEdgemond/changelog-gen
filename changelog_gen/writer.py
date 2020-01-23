from pathlib import Path
from tempfile import NamedTemporaryFile


SUPPORTED_EXTENSIONS = ["md", "rst"]


class BaseWriter:
    file_header_line_count = 0
    file_header = None
    extension = None

    def __init__(self, changelog, dry_run=False):
        self.existing = []
        self.changelog = changelog
        if self.changelog.exists():
            lines = changelog.read_text().split("\n")
            self.existing = lines[self.file_header_line_count + 1:]
        self.content = []
        self.dry_run = dry_run

    def add_version(self, version):
        self._add_version(version)

    def _add_version(self, version):
        raise NotImplementedError

    def add_section(self, header, lines):
        self._add_section_header(header)
        for line in lines:
            self._add_section_line(line)
        self._post_section()

    def _add_section_header(self, header):
        raise NotImplementedError

    def _add_section_line(self, line):
        raise NotImplementedError

    def _post_section(self):
        pass

    def __str__(self):
        return "\n".join(self.content)

    def write(self):
        self.content = [self.file_header] + self.content + self.existing

        if self.dry_run:
            with NamedTemporaryFile("wb") as output_file:
                output_file.write(("\n".join(self.content)).encode("utf-8"))
        else:
            self.changelog.write_text("\n".join(self.content))


class MdWriter(BaseWriter):
    file_header_line_count = 1
    file_header = "# Changelog\n"
    extension = "md"

    def _add_version(self, version):
        self.content.extend(["## {version}".format(version=version), ""])

    def _add_section_header(self, header):
        self.content.extend(["### {header}".format(header=header), ""])

    def _add_section_line(self, line):
        self.content.extend(["- {line}".format(line=line)])

    def _post_section(self):
        self.content.extend([""])


class RstWriter(BaseWriter):
    file_header_line_count = 3
    file_header = "=========\nChangelog\n=========\n"
    extension = "rst"

    def _add_version(self, version):
        self.content.extend([version, "=" * len(version), ""])

    def _add_section_header(self, header):
        self.content.extend([header, "-" * len(header), ""])

    def _add_section_line(self, line):
        self.content.extend(["* {line}".format(line=line), ""])


def new_writer(extension, dry_run=False):
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            'Changelog extension "{extension}" not supported.'.format(
                extension=extension,
            ),
        )

    changelog = Path("CHANGELOG.{extension}".format(extension=extension))

    if extension == "md":
        return MdWriter(changelog, dry_run=dry_run)
    if extension == "rst":
        return RstWriter(changelog, dry_run=dry_run)
