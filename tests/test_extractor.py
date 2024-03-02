import random
from unittest import mock

import pytest

from changelog_gen import errors, extractor
from changelog_gen.config import SUPPORTED_SECTIONS
from changelog_gen.extractor import Change, ReleaseNoteExtractor


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
            "2": Change("2", "Detail about 2"),
            "3": Change("3", "Detail about 3"),
        },
        "fix": {
            "1": Change("1", "Detail about 1"),
            "4": Change("4", "Detail about 4"),
        },
    }


@pytest.mark.usefixtures("_breaking_release_notes")
def test_breaking_notes_extraction():
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    sections = e.extract()

    assert sections == {
        "feat": {
            "2": Change("2", "Detail about 2"),
            "3": Change("3", "Detail about 3", breaking=True),
        },
        "fix": {
            "1": Change("1", "Detail about 1", breaking=True),
            "4": Change("4", "Detail about 4"),
        },
    }


def test_git_commit_extraction(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    for msg in [
        """fix(config): Detail about 4

Refs: #4
""",
        "fix typo",
        """feat(docs)!: Detail about 3

Refs: #3
""",
        """fix: Detail about 1

With some details

BREAKING CHANGE:
Refs: #1
""",
        "update readme",
        """feat: Detail about 2

Refs: #2
""",
    ]:
        f.write_text(msg)
        multiversion_repo.run("git add hello.txt")
        multiversion_repo.api.index.commit(msg)

    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    sections = e.extract()

    assert sections == {
        "feat": {
            "2": Change("2", "Detail about 2"),
            "3": Change("3", "Detail about 3", breaking=True, scope="(docs)"),
        },
        "fix": {
            "1": Change("1", "Detail about 1", breaking=True),
            "4": Change("4", "Detail about 4", scope="(config)"),
        },
    }


def test_git_commit_extraction_picks_up_custom_types(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    for msg in [
        """bug: Detail about 1

With some details

BREAKING CHANGE:
Refs: #1
""",
        "update readme",
        """feat: Detail about 2

Refs: #2
""",
    ]:
        f.write_text(msg)
        multiversion_repo.run("git add hello.txt")
        multiversion_repo.api.index.commit(msg)

    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    sections = e.extract({"bug": "fix"})

    assert sections == {
        "feat": {
            "2": Change("2", "Detail about 2"),
        },
        "fix": {
            "1": Change("1", "Detail about 1", breaking=True),
        },
    }


@pytest.mark.usefixtures("_invalid_release_notes")
def test_invalid_notes_extraction_raises():
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    with pytest.raises(errors.InvalidSectionError) as ex:
        e.extract()

    assert str(ex.value) == "Unsupported CHANGELOG section bug, derived from `./release_notes/3.bug`"


@pytest.mark.usefixtures("_invalid_release_notes")
def test_section_remapping_can_remap_custom_sections():
    e = ReleaseNoteExtractor(SUPPORTED_SECTIONS)

    sections = e.extract({"bug": "fix"})
    assert sections == {
        "feat": {
            "2": Change("2", "Detail about 2"),
        },
        "fix": {
            "1": Change("1", "Detail about 1"),
            "3": Change("3", "Detail about 3"),
            "4": Change("4", "Detail about 4"),
        },
    }


@pytest.mark.usefixtures("_invalid_release_notes")
def test_section_mapping_can_handle_new_sections():
    e = ReleaseNoteExtractor({"bug": "BugFix", "feat": "Features"})

    sections = e.extract({"fix": "bug"})
    assert sections == {
        "feat": {
            "2": Change("2", "Detail about 2"),
        },
        "bug": {
            "1": Change("1", "Detail about 1"),
            "3": Change("3", "Detail about 3"),
            "4": Change("4", "Detail about 4"),
        },
    }


def test_unique_issues():
    e = ReleaseNoteExtractor({"bug": "BugFix", "feat": "Features"})

    assert e.unique_issues({
        "unsupported": {
            "5": Change("5", "Detail about 5"),
        },
        "feat": {
            "2": Change("2", "Detail about 2"),
        },
        "bug": {
            "2": Change("2", "Detail about 2"),
            "3": Change("3", "Detail about 3"),
            "4": Change("4", "Detail about 4"),
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


@pytest.mark.parametrize(
    ("sections", "semver_mapping", "expected_semver"),
    [
        ({"fix": {"1": Change("1", "desc")}}, {"feat": "minor"}, "patch"),
        ({"feat": {"1": Change("1", "desc")}}, {"feat": "minor"}, "patch"),
        ({"fix": {"1": Change("1", "desc", breaking=True)}}, {"feat": "minor"}, "minor"),
        ({"feat": {"1": Change("1", "desc", breaking=True)}}, {"feat": "minor"}, "minor"),
        ({"custom": {"1": Change("1", "desc")}}, {"custom": "patch"}, "patch"),
        ({"custom": {"1": Change("1", "desc")}}, {"custom": "minor"}, "patch"),
        ({"custom": {"1": Change("1", "desc", breaking=True)}}, {"custom": "minor"}, "minor"),
    ],
)
def test_extract_version_tag_version_zero(sections, semver_mapping, expected_semver, monkeypatch):
    monkeypatch.setattr(
        extractor.BumpVersion,
        "get_version_info",
        mock.Mock(return_value={"new": "0.0.0", "current": "0.0.0"}),
    )

    extractor.extract_version_tag(sections, semver_mapping)

    assert extractor.BumpVersion.get_version_info.call_args == mock.call(expected_semver)


@pytest.mark.parametrize(
    ("sections", "semver_mapping", "expected_semver"),
    [
        ({"fix": {"1": Change("1", "desc")}}, {"feat": "minor"}, "patch"),
        ({"feat": {"1": Change("1", "desc")}}, {"feat": "minor"}, "minor"),
        ({"fix": {"1": Change("1", "desc", breaking=True)}}, {"feat": "minor"}, "major"),
        ({"feat": {"1": Change("1", "desc", breaking=True)}}, {"feat": "minor"}, "major"),
        ({"custom": {"1": Change("1", "desc")}}, {"custom": "patch"}, "patch"),
        ({"custom": {"1": Change("1", "desc")}}, {"custom": "minor"}, "minor"),
        ({"custom": {"1": Change("1", "desc", breaking=True)}}, {"custom": "minor"}, "major"),
    ],
)
def test_extract_version_tag(sections, semver_mapping, expected_semver, monkeypatch):
    monkeypatch.setattr(
        extractor.BumpVersion,
        "get_version_info",
        mock.Mock(return_value={"new": "1.0.0", "current": "1.0.0"}),
    )

    extractor.extract_version_tag(sections, semver_mapping)

    assert extractor.BumpVersion.get_version_info.call_args == mock.call(expected_semver)


def test_change_ordering():
    changes = [
        Change(issue_ref="23", description="Small change", authors="(edgy, tom)", scope="", breaking=False),
        Change(issue_ref="24", description="A description", authors="(edgy)", scope="(writer)", breaking=True),
        Change(issue_ref="25", description="Another change", authors="(tom)", scope="(extractor)", breaking=False),
        Change(issue_ref="26", description="Bugfix", authors="", scope="(extractor)", breaking=False),
        Change(issue_ref="27", description="Upgrade python", authors="(tom)", scope="", breaking=True),
        Change(issue_ref="28", description="Update config", authors="(edgy)", scope="(config)", breaking=False),
    ]
    random.shuffle(changes)

    assert sorted(changes) == [
        Change(issue_ref="24", description="A description", authors="(edgy)", scope="(writer)", breaking=True),
        Change(issue_ref="27", description="Upgrade python", authors="(tom)", scope="", breaking=True),
        Change(issue_ref="28", description="Update config", authors="(edgy)", scope="(config)", breaking=False),
        Change(issue_ref="25", description="Another change", authors="(tom)", scope="(extractor)", breaking=False),
        Change(issue_ref="26", description="Bugfix", authors="", scope="(extractor)", breaking=False),
        Change(issue_ref="23", description="Small change", authors="(edgy, tom)", scope="", breaking=False),
    ]
