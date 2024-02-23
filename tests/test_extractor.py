import pytest

from changelog_gen import errors
from changelog_gen.config import SUPPORTED_SECTIONS
from changelog_gen.extractor import ReleaseNoteExtractor


@pytest.fixture()
def multiversion_repo(git_repo):
    path = git_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world!")

    git_repo.run("git add hello.txt")
    git_repo.api.index.commit("initial commit")

    git_repo.api.create_tag("v0.0.1")

    f.write_text("hello world! v2")
    git_repo.run("git add hello.txt")
    git_repo.api.index.commit("update")

    git_repo.api.create_tag("v0.0.2")

    return git_repo


@pytest.fixture()
def release_notes(multiversion_repo):
    path = multiversion_repo.workspace
    r = path / "release_notes"
    r.mkdir()
    f = r / ".file"
    f.write_text("")
    return r


@pytest.fixture()
def _valid_release_notes(release_notes):
    for i, note in enumerate(["1.fix", "2.feat", "3.feat", "4.fix"], 1):
        n = release_notes / note
        n.write_text(f"Detail about {i}")


@pytest.fixture()
def _breaking_release_notes(release_notes):
    for i, note in enumerate(["1.fix!", "2.feat", "3.feat!", "4.fix"], 1):
        n = release_notes / note
        n.write_text(f"Detail about {i}")


@pytest.fixture()
def _invalid_release_notes(release_notes):
    for i, note in enumerate(["1.fix", "2.feat", "3.bug", "4.fix"], 1):
        n = release_notes / note
        n.write_text(f"Detail about {i}")


@pytest.fixture()
def _remap_release_notes(release_notes):
    for i, note in enumerate(["1.bugfix", "2.feature", "3.test"]):
        n = release_notes / note
        n.write_text(f"Detail about {i}")


@pytest.mark.usefixtures("multiversion_repo")
def test_init_with_no_release_notes():
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)
    assert e.has_release_notes is False


def test_init_with_release_notes_non_dir(multiversion_repo):
    path = multiversion_repo.workspace
    r = path / "release_notes"
    r.write_text("not a dir")

    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    assert e.has_release_notes is False


@pytest.mark.usefixtures("_valid_release_notes")
def test_valid_notes_extraction():
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


@pytest.mark.usefixtures("_breaking_release_notes")
def test_breaking_notes_extraction():
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


@pytest.mark.usefixtures("_invalid_release_notes")
def test_invalid_notes_extraction_raises():
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    with pytest.raises(errors.InvalidSectionError):
        e.extract()


@pytest.mark.usefixtures("_invalid_release_notes")
def test_section_remapping_can_remap_custom_sections():
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


@pytest.mark.usefixtures("_invalid_release_notes")
def test_section_mapping_can_handle_new_sections():
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


def test_unique_issues():
    e = ReleaseNoteExtractor({"bug": "BugFix", "feat": "Features"})

    assert e.unique_issues({
        "unsupported": {
            "5": {"description": "Detail about 4", "breaking": False},
        },
        "feat": {
            "2": {"description": "Detail about 2", "breaking": False},
        },
        "bug": {
            "2": {"description": "Detail about 2", "breaking": False},
            "3": {"description": "Detail about 3", "breaking": False},
            "4": {"description": "Detail about 4", "breaking": False},
        },
    }) == ["2", "3", "4"]


@pytest.mark.usefixtures("_valid_release_notes")
def test_dry_run_clean_keeps_files(release_notes):
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS, dry_run=True)

    e.clean()

    assert sorted([f.name for f in release_notes.iterdir()]) == sorted(
        [
            "1.fix",
            "2.feat",
            "3.feat",
            "4.fix",
            ".file",
        ],
    )


@pytest.mark.usefixtures("_valid_release_notes")
def test_clean_removes_all_non_dotfiles(release_notes):
    """Clean should not remove .gitkeep files etc."""
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    e.clean()

    assert [f.name for f in release_notes.iterdir()] == [".file"]
