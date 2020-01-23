import pytest

from changelog_gen.cli import util


@pytest.mark.parametrize("filename,ext", [
    ("CHANGELOG.md", "md"),
    ("CHANGELOG.rst", "rst"),
    ("CHANGELOG.txt", None),
])
def test_detect_extension(filename, ext, cwd):
    f = cwd / filename
    f.write_text("changelog")

    assert util.detect_extension() == ext
