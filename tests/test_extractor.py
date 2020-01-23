import os

import pytest

from changelog_gen.extractor import ReleaseNoteExtractor
from changelog_gen import errors


@pytest.fixture
def cwd(tmp_path):
    orig = os.getcwd()

    try:
        os.chdir(tmp_path)
        yield tmp_path
    except Exception:
        raise
    finally:
        os.chdir(orig)


@pytest.fixture
def release_notes(cwd):
    r = cwd / "release_notes"
    r.mkdir()
    f = r / ".file"
    f.write_text("")
    return r


@pytest.fixture
def valid_release_notes(release_notes):
    for i, note in enumerate(["1.fix", "2.feat", "3.feat", "4.fix"], 1):
        n = release_notes / note
        n.write_text("Detail about {}".format(i))


@pytest.fixture
def invalid_release_notes(release_notes):
    for i, note in enumerate(["1.fix", "2.feat", "3.bug", "4.fix"]):
        n = release_notes / note
        n.write_text("Detail about {}".format(i))


@pytest.fixture
def remap_release_notes(release_notes):
    for i, note in enumerate(["1.bugfix", "2.feature", "3.test"]):
        n = release_notes / note
        n.write_text("Detail about {}".format(i))


def test_init_with_no_release_notes_raises(cwd):
    with pytest.raises(errors.NoReleaseNotesError):
        ReleaseNoteExtractor() 


def test_init_with_release_notes_non_dir_raises(cwd):
    r = cwd / "release_notes"
    r.write_text("not a dir")

    with pytest.raises(errors.NoReleaseNotesError):
        ReleaseNoteExtractor() 


def test_valid_notes_extraction(valid_release_notes):
    e = ReleaseNoteExtractor() 

    sections = e.extract()

    assert sections == {
        "feat": {
            "2": "Detail about 2",
            "3": "Detail about 3",
        },
        "fix": {
            "1": "Detail about 1",
            "4": "Detail about 4",
        },
    }


def test_invalid_notes_extraction_raises(invalid_release_notes):
    e = ReleaseNoteExtractor() 

    with pytest.raises(errors.InvalidSectionError):
        e.extract()


def test_dry_run_clean_keeps_files(valid_release_notes, release_notes):
    e = ReleaseNoteExtractor(dry_run=True) 

    e.clean()

    assert sorted([f.name for f in release_notes.iterdir()]) == sorted([
        "1.fix", "2.feat", "3.feat", "4.fix", ".file",
    ])


def test_clean_removes_all_non_dotfiles(valid_release_notes, release_notes):
    """
    Clean should not remove .gitkeep files etc
    """
    e = ReleaseNoteExtractor() 

    e.clean()

    assert [f.name for f in release_notes.iterdir()] == [".file"]
