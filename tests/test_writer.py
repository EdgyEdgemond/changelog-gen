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
def changelog(tmp_path):
    p = tmp_path / "CHANGELOG"
    p.write_text("")
    return p


@pytest.fixture
def changelog_md(tmp_path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text("# Changelog\n")
    return p


@pytest.fixture
def changelog_rst(tmp_path):
    p = tmp_path / "CHANGELOG.rst"
    p.write_text("=========\nChangelog\n=========\n")
    return p


class TestBaseWriter:
    def test_init(self, changelog):
        w = writer.BaseWriter(changelog)

        assert w.content == []
        assert w.dry_run is False

    def test_init_dry_run(self, changelog):
        w = writer.BaseWriter(changelog, dry_run=True)

        assert w.content == []
        assert w.dry_run is True

    def test_init_no_existing_entries(self, changelog):
        w = writer.BaseWriter(changelog)

        assert w.existing == []

    def test_init_stores_existing_changelog(self, changelog):
        changelog.write_text("""
## 0.0.1

### header

- line1
- line2
- line3
""")
        w = writer.BaseWriter(changelog)

        assert w.existing == [
            "## 0.0.1",
            "",
            "### header",
            "",
            "- line1",
            "- line2",
            "- line3",
            "",
        ]

    def test_content_as_str(self, changelog):
        w = writer.BaseWriter(changelog)
        w.content = ["line1", "line2", "line3"]

        assert str(w) == "line1\nline2\nline3"

    def test_base_methods_not_implemented(self, changelog):
        w = writer.BaseWriter(changelog)

        with pytest.raises(NotImplementedError):
            w._add_section_header("header")

        with pytest.raises(NotImplementedError):
            w._add_section_line("description", "issue_ref")

        with pytest.raises(NotImplementedError):
            w._add_version("0.0.0")

    def test_add_version(self, monkeypatch, changelog):
        monkeypatch.setattr(writer.BaseWriter, "_add_version", mock.Mock())
        w = writer.BaseWriter(changelog)

        w.add_version("0.0.0")

        assert w._add_version.call_args == mock.call("0.0.0")

    def test_add_section(self, monkeypatch, changelog):
        monkeypatch.setattr(writer.BaseWriter, "_add_section_header", mock.Mock())
        monkeypatch.setattr(writer.BaseWriter, "_add_section_line", mock.Mock())

        w = writer.BaseWriter(changelog)

        w.add_section("header", {"1": "line1", "2": "line2", "3": "line3"})

        assert w._add_section_header.call_args == mock.call("header")
        assert w._add_section_line.call_args_list == [
            mock.call("line1", "1"),
            mock.call("line2", "2"),
            mock.call("line3", "3"),
        ]


class TestMdWriter:
    def test_init(self, changelog_md):
        w = writer.MdWriter(changelog_md)

        assert w.content == []
        assert w.dry_run is False

    def test_init_dry_run(self, changelog_md):
        w = writer.MdWriter(changelog_md, dry_run=True)

        assert w.content == []
        assert w.dry_run is True

    def test_init_no_existing_entries(self, changelog_md):
        w = writer.MdWriter(changelog_md)

        assert w.existing == []

    def test_init_stores_existing_changelog(self, changelog_md):
        changelog_md.write_text("""# Changelog

## 0.0.1

### header

- line1
- line2
- line3
""")

        w = writer.MdWriter(changelog_md)

        assert w.existing == [
            "## 0.0.1",
            "",
            "### header",
            "",
            "- line1",
            "- line2",
            "- line3",
            "",
        ]

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

        w._add_section_line("line", "1")

        assert w.content == ["- line [#1]"]

    def test_add_section_line_with_issue_link(self, changelog_md):
        w = writer.MdWriter(changelog_md, issue_link="http://url/issues/{issue_ref}")

        w._add_section_line("line", "1")

        assert w.content == ["- line [[#1](http://url/issues/1)]"]

    def test_write_dry_run_doesnt_write_to_file(self, changelog_md):
        w = writer.MdWriter(changelog_md, dry_run=True)
        w.add_version("0.0.1")
        w.add_section("header", {"1": "line1", "2": "line2", "3": "line3"})

        w.write()
        assert changelog_md.read_text() == """# Changelog\n"""

    def test_write(self, changelog_md):
        w = writer.MdWriter(changelog_md)
        w.add_version("0.0.1")
        w.add_section("header", {"1": "line1", "2": "line2", "3": "line3"})

        w.write()
        assert changelog_md.read_text() == """# Changelog

## 0.0.1

### header

- line1 [#1]
- line2 [#2]
- line3 [#3]
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
        w.add_section("header", {"4": "line4", "5": "line5", "6": "line6"})

        w.write()

        assert changelog_md.read_text() == """# Changelog

## 0.0.2

### header

- line4 [#4]
- line5 [#5]
- line6 [#6]

## 0.0.1

### header

- line1
- line2
- line3
"""


class TestRstWriter:
    def test_init(self, changelog_rst):
        w = writer.RstWriter(changelog_rst)

        assert w.content == []
        assert w.dry_run is False

    def test_init_dry_run(self, changelog_rst):
        w = writer.RstWriter(changelog_rst, dry_run=True)

        assert w.content == []
        assert w.dry_run is True

    def test_init_no_existing_entries(self, changelog_rst):
        w = writer.RstWriter(changelog_rst)

        assert w.existing == []

    def test_init_stores_existing_changelog(self, changelog_rst):
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

        assert w.existing == [
            "0.0.1",
            "=====",
            "",
            "header",
            "------",
            "",
            "* line1",
            "",
            "* line2",
            "",
            "* line3",
            "",
        ]

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

        w._add_section_line("line", "1")

        assert w.content == ["* line [#1]", ""]

    def test_add_section_line_with_issue_link(self, changelog_rst):
        w = writer.RstWriter(changelog_rst, issue_link="http://url/issues/{issue_ref}")

        w._add_section_line("line", "1")

        assert w.content == ["* line [`#1`_]", ""]
        assert w.links == {"#1": "http://url/issues/1"}

    def test_write_dry_run_doesnt_write_to_file(self, changelog_rst):
        w = writer.RstWriter(changelog_rst, dry_run=True)
        w.add_version("0.0.1")
        w.add_section("header", {"1": "line1", "2": "line2", "3": "line3"})

        w.write()
        assert changelog_rst.read_text() == """=========
Changelog
=========
"""

    def test_write(self, changelog_rst):
        w = writer.RstWriter(changelog_rst)
        w.add_version("0.0.1")
        w.add_section("header", {"1": "line1", "2": "line2", "3": "line3"})

        w.write()
        assert changelog_rst.read_text() == """=========
Changelog
=========

0.0.1
=====

header
------

* line1 [#1]

* line2 [#2]

* line3 [#3]
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

        w = writer.RstWriter(changelog_rst, issue_link="http://url/issues/{issue_ref}")
        w.add_version("0.0.2")
        w.add_section("header", {"4": "line4", "5": "line5", "6": "line6"})

        w.write()

        assert changelog_rst.read_text() == """=========
Changelog
=========

0.0.2
=====

header
------

* line4 [`#4`_]

* line5 [`#5`_]

* line6 [`#6`_]

0.0.1
=====

header
------

* line1

* line2

* line3

.. _`#4`: http://url/issues/4
.. _`#5`: http://url/issues/5
.. _`#6`: http://url/issues/6"""
