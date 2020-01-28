import pytest

from changelog_gen import errors
from changelog_gen.cli.command import SUPPORTED_SECTIONS
from changelog_gen.extractor import ReleaseNoteExtractor


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
def breaking_release_notes(release_notes):
    for i, note in enumerate(["1.fix!", "2.feat", "3.feat!", "4.fix"], 1):
        n = release_notes / note
        n.write_text("Detail about {}".format(i))


@pytest.fixture
def invalid_release_notes(release_notes):
    for i, note in enumerate(["1.fix", "2.feat", "3.bug", "4.fix"], 1):
        n = release_notes / note
        n.write_text("Detail about {}".format(i))


@pytest.fixture
def remap_release_notes(release_notes):
    for i, note in enumerate(["1.bugfix", "2.feature", "3.test"]):
        n = release_notes / note
        n.write_text("Detail about {}".format(i))


def test_init_with_no_release_notes_raises(cwd):
    with pytest.raises(errors.NoReleaseNotesError):
        ReleaseNoteExtractor(SUPPORTED_SECTIONS)


def test_init_with_release_notes_non_dir_raises(cwd):
    r = cwd / "release_notes"
    r.write_text("not a dir")

    with pytest.raises(errors.NoReleaseNotesError):
        ReleaseNoteExtractor(SUPPORTED_SECTIONS)


def test_valid_notes_extraction(valid_release_notes):
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    sections = e.extract()

    assert sections == {
        "feat": {
            "2": {"description": "Detail about 2", "breaking": False},
            "3": {"description": "Detail about 3", "breaking": False},
        },
        "fix": {
            "1": {"description": "Detail about 1", "breaking": False},
            "4": {"description": "Detail about 4", "breaking": False},
        },
    }


def test_breaking_notes_extraction(breaking_release_notes):
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    sections = e.extract()

    assert sections == {
        "feat": {
            "2": {"description": "Detail about 2", "breaking": False},
            "3": {"description": "Detail about 3", "breaking": True},
        },
        "fix": {
            "1": {"description": "Detail about 1", "breaking": True},
            "4": {"description": "Detail about 4", "breaking": False},
        },
    }


def test_invalid_notes_extraction_raises(invalid_release_notes):
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    with pytest.raises(errors.InvalidSectionError):
        e.extract()


def test_section_remapping_can_remap_custom_sections(invalid_release_notes):
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    sections = e.extract({"bug": "fix"})
    assert sections == {
        "feat": {
            "2": {"description": "Detail about 2", "breaking": False},
        },
        "fix": {
            "1": {"description": "Detail about 1", "breaking": False},
            "3": {"description": "Detail about 3", "breaking": False},
            "4": {"description": "Detail about 4", "breaking": False},
        },
    }


def test_section_mapping_can_handle_new_sections(invalid_release_notes):
    e = ReleaseNoteExtractor({"bug": "BugFix", "feat": "Features"})

    sections = e.extract({"fix": "bug"})
    assert sections == {
        "feat": {
            "2": {"description": "Detail about 2", "breaking": False},
        },
        "bug": {
            "1": {"description": "Detail about 1", "breaking": False},
            "3": {"description": "Detail about 3", "breaking": False},
            "4": {"description": "Detail about 4", "breaking": False},
        },
    }


def test_dry_run_clean_keeps_files(valid_release_notes, release_notes):
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS, dry_run=True)

    e.clean()

    assert sorted([f.name for f in release_notes.iterdir()]) == sorted([
        "1.fix", "2.feat", "3.feat", "4.fix", ".file",
    ])


def test_clean_removes_all_non_dotfiles(valid_release_notes, release_notes):
    """
    Clean should not remove .gitkeep files etc
    """
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    e.clean()

    assert [f.name for f in release_notes.iterdir()] == [".file"]
