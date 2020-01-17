from pathlib import Path
from unittest import mock

import pytest

from changelog_gen import writer


@pytest.mark.parametrize("extension,expected_cls", [
    ("md", writer.MdWriter),
    ("rst", writer.RstWriter),
])
def test_new_writer(extension, expected_cls):
    assert isinstance(writer.new_writer(extension), expected_cls)


def test_new_writer_raises_for_unsupported_extension():
    with pytest.raises(ValueError):
        writer.new_writer("txt")


@pytest.fixture
def changelog_md(tmp_path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text("# Changelog\n")
    return p


@pytest.fixture
def changelog_rst(tmp_path):
    p = tmp_path / "CHANGELOG.rst"
    p.write_text("Changelog\n=========\n")
    return p

class TestBaseWriter:
    def test_content_as_str(self, changelog_md):
        w = writer.BaseWriter(changelog_md)
        w.content = ["line1", "line2", "line3"]

        assert str(w) == "line1\nline2\nline3"

    def test_base_methods_not_implemented(self, changelog_rst):
        w = writer.BaseWriter(changelog_rst)

        with pytest.raises(NotImplementedError):
            w._add_section_header('header')

        with pytest.raises(NotImplementedError):
            w._add_section_line('line')

        with pytest.raises(NotImplementedError):
            w._add_version('0.0.0')

    def test_add_version(self, monkeypatch, changelog_md):
        monkeypatch.setattr(writer.BaseWriter, "_add_version", mock.Mock())
        w = writer.BaseWriter(changelog_md)

        w.add_version("0.0.0")

        assert w._add_version.call_args == mock.call("0.0.0")

    def test_add_section(self, monkeypatch, changelog_rst):
        monkeypatch.setattr(writer.BaseWriter, "_add_section_header", mock.Mock())
        monkeypatch.setattr(writer.BaseWriter, "_add_section_line", mock.Mock())

        w = writer.BaseWriter(changelog_rst)

        w.add_section("header", ["line1", "line2", "line3"])

        assert w._add_section_header.call_args == mock.call("header")
        assert w._add_section_line.call_args_list == [
            mock.call("line1"),
            mock.call("line2"),
            mock.call("line3"),
        ]


class TestMdWriter:
    def test_add_version(self, changelog_md):
        w = writer.MdWriter(changelog_md)

        w._add_version("0.0.0")

        assert w.content == ["## 0.0.0", ""]

    def test_add_section_header(self, changelog_md):
        w = writer.MdWriter(changelog_md)

        w._add_section_header("header")

        assert w.content == ["### header", ""]

    def test_add_section_line(self, changelog_md):
        w = writer.MdWriter(changelog_md)

        w._add_section_line("line [#1]")

        assert w.content == ["- line [#1]"]

    def test_write(self, changelog_md):
        w = writer.MdWriter(changelog_md)
        w.add_version("0.0.1")
        w.add_section("header", ["line1", "line2", "line3"])

        w.write()
        assert changelog_md.read_text() == """# Changelog

## 0.0.1

### header

- line1
- line2
- line3
"""

    def test_write_with_existing_content(self, changelog_md):
        changelog_md.write_text("""# Changelog

## 0.0.1

### header

- line1
- line2
- line3
""")

        w = writer.MdWriter(changelog_md)
        w.add_version("0.0.2")
        w.add_section("header", ["line4", "line5", "line6"])

        w.write()

        assert changelog_md.read_text() == """# Changelog

## 0.0.2

### header

- line4
- line5
- line6

## 0.0.1

### header

- line1
- line2
- line3
"""

class TestRstWriter:
    def test_add_version(self, changelog_rst):
        w = writer.RstWriter(changelog_rst)

        w._add_version("0.0.0")

        assert w.content == ["0.0.0", "=====", ""]

    def test_add_section_header(self, changelog_rst):
        w = writer.RstWriter(changelog_rst)

        w._add_section_header("header")

        assert w.content == ["header", "------", ""]

    def test_add_section_line(self, changelog_rst):
        w = writer.RstWriter(changelog_rst)

        w._add_section_line("line [#1]")

        assert w.content == ["* line [#1]", ""]

    def test_write(self, changelog_rst):
        w = writer.RstWriter(changelog_rst)
        w.add_version("0.0.1")
        w.add_section("header", ["line1", "line2", "line3"])

        w.write()
        assert changelog_rst.read_text() == """=========
Changelog
=========

0.0.1
=====

header
------

* line1

* line2

* line3
"""

    def test_write_with_existing_content(self, changelog_rst):
        changelog_rst.write_text("""=========
Changelog
=========

0.0.1
=====

header
------

* line1

* line2

* line3
""")

        w = writer.RstWriter(changelog_rst)
        w.add_version("0.0.2")
        w.add_section("header", ["line4", "line5", "line6"])

        w.write()

        assert changelog_rst.read_text() == """=========
Changelog
=========

0.0.2
=====

header
------

* line4

* line5

* line6

0.0.1
=====

header
------

* line1

* line2

* line3
"""
