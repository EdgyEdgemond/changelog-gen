import random
from unittest import mock

import pytest

from changelog_gen import errors, extractor
from changelog_gen.config import TYPE_HEADERS
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
    e = ReleaseNoteExtractor(TYPE_HEADERS)
    assert e.has_release_notes is False


def test_init_with_release_notes_non_dir(multiversion_repo):
    path = multiversion_repo.workspace
    r = path / "release_notes"
    r.write_text("not a dir")

    e = ReleaseNoteExtractor(TYPE_HEADERS)

    assert e.has_release_notes is False


@pytest.mark.usefixtures("_valid_release_notes")
def test_valid_notes_extraction():
    e = ReleaseNoteExtractor(TYPE_HEADERS)

    sections = e.extract()

    assert sections == {
        "Features and Improvements": {
            "2": Change("2", "Detail about 2", "feat"),
            "3": Change("3", "Detail about 3", "feat"),
        },
        "Bug fixes": {
            "1": Change("1", "Detail about 1", "fix"),
            "4": Change("4", "Detail about 4", "fix"),
        },
    }


@pytest.mark.usefixtures("_breaking_release_notes")
def test_breaking_notes_extraction():
    e = ReleaseNoteExtractor(TYPE_HEADERS)

    sections = e.extract()

    assert sections == {
        "Features and Improvements": {
            "2": Change("2", "Detail about 2", "feat"),
            "3": Change("3", "Detail about 3", "feat", breaking=True),
        },
        "Bug fixes": {
            "1": Change("1", "Detail about 1", "fix", breaking=True),
            "4": Change("4", "Detail about 4", "fix"),
        },
    }


def test_git_commit_extraction(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    hashes = []
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
        hashes.append(str(multiversion_repo.api.head.commit))

    e = ReleaseNoteExtractor(TYPE_HEADERS)

    sections = e.extract()

    assert sections == {
        "Features and Improvements": {
            "2": Change("2", "Detail about 2", short_hash=hashes[5][:7], commit_hash=hashes[5], commit_type="feat"),
            "3": Change(
                "3",
                "Detail about 3",
                breaking=True,
                scope="(docs)",
                short_hash=hashes[2][:7],
                commit_hash=hashes[2],
                commit_type="feat",
            ),
        },
        "Bug fixes": {
            "1": Change(
                "1",
                "Detail about 1",
                breaking=True,
                short_hash=hashes[3][:7],
                commit_hash=hashes[3],
                commit_type="fix",
            ),
            "4": Change(
                "4",
                "Detail about 4",
                scope="(config)",
                short_hash=hashes[0][:7],
                commit_hash=hashes[0],
                commit_type="fix",
            ),
        },
    }


def test_git_commit_extraction_picks_up_custom_types(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    hashes = []
    for msg in [
        """custom: Detail about 1

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
        hashes.append(str(multiversion_repo.api.head.commit))

    e = ReleaseNoteExtractor({"custom": "Bug fixes", "feat": "Features and Improvements", "bug": "Bug fixes"})

    sections = e.extract()

    assert sections == {
        "Features and Improvements": {
            "2": Change("2", "Detail about 2", short_hash=hashes[2][:7], commit_hash=hashes[2], commit_type="feat"),
        },
        "Bug fixes": {
            "1": Change(
                "1",
                "Detail about 1",
                breaking=True,
                short_hash=hashes[0][:7],
                commit_hash=hashes[0],
                commit_type="custom",
            ),
        },
    }


@pytest.mark.usefixtures("_invalid_release_notes")
def test_invalid_notes_extraction_raises():
    e = ReleaseNoteExtractor({"fix": "Fix", "feat": "Features"})

    with pytest.raises(errors.InvalidSectionError) as ex:
        e.extract()

    assert str(ex.value) == "Unsupported CHANGELOG commit type bug, derived from `./release_notes/3.bug`"


@pytest.mark.usefixtures("_invalid_release_notes")
def test_section_mapping_can_handle_new_sections():
    e = ReleaseNoteExtractor({"bug": "BugFix", "feat": "Features", "fix": "BugFix"})

    sections = e.extract()
    assert sections == {
        "Features": {
            "2": Change("2", "Detail about 2", "feat"),
        },
        "BugFix": {
            "1": Change("1", "Detail about 1", "fix"),
            "3": Change("3", "Detail about 3", "bug"),
            "4": Change("4", "Detail about 4", "fix"),
        },
    }


def test_unique_issues():
    e = ReleaseNoteExtractor({"bug": "BugFix", "feat": "Features"})

    assert e.unique_issues(
        {
            "Unsupported header": {
                "5": Change("5", "Detail about 5", "unsupported"),
            },
            "Feature header": {
                "2": Change("2", "Detail about 2", "feat"),
            },
            "Bug header": {
                "2": Change("2", "Detail about 2", "bug"),
                "3": Change("3", "Detail about 3", "bug"),
                "4": Change("4", "Detail about 4", "bug"),
            },
        },
    ) == ["2", "3", "4"]


@pytest.mark.usefixtures("_valid_release_notes")
def test_dry_run_clean_keeps_files(release_notes):
    e = ReleaseNoteExtractor(TYPE_HEADERS, dry_run=True)

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
    e = ReleaseNoteExtractor(TYPE_HEADERS)

    e.clean()

    assert [f.name for f in release_notes.iterdir()] == [".file"]


@pytest.mark.parametrize(
    ("sections", "semver_mapping", "expected_semver"),
    [
        ({"header": {"1": Change("1", "desc", "fix")}}, {"feat": "minor"}, "patch"),
        ({"header": {"1": Change("1", "desc", "feat")}}, {"feat": "minor"}, "patch"),
        ({"header": {"1": Change("1", "desc", "fix", breaking=True)}}, {"feat": "minor"}, "minor"),
        ({"header": {"1": Change("1", "desc", "feat", breaking=True)}}, {"feat": "minor"}, "minor"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": "patch"}, "patch"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": "minor"}, "patch"),
        ({"header": {"1": Change("1", "desc", "custom", breaking=True)}}, {"custom": "minor"}, "minor"),
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
        ({"header": {"1": Change("1", "desc", "fix")}}, {"feat": "minor"}, "patch"),
        ({"header": {"1": Change("1", "desc", "feat")}}, {"feat": "minor"}, "minor"),
        ({"header": {"1": Change("1", "desc", "fix", breaking=True)}}, {"feat": "minor"}, "major"),
        ({"header": {"1": Change("1", "desc", "feat", breaking=True)}}, {"feat": "minor"}, "major"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": "patch"}, "patch"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": "minor"}, "minor"),
        ({"header": {"1": Change("1", "desc", "custom", breaking=True)}}, {"custom": "minor"}, "major"),
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
        Change(
            issue_ref="23",
            description="Small change",
            authors="(edgy, tom)",
            scope="",
            breaking=False,
            commit_type="fix",
        ),
        Change(
            issue_ref="24",
            description="A description",
            authors="(edgy)",
            scope="(writer)",
            breaking=True,
            commit_type="misc",
        ),
        Change(
            issue_ref="25",
            description="Another change",
            authors="(tom)",
            scope="(extractor)",
            breaking=False,
            commit_type="ci",
        ),
        Change(
            issue_ref="26",
            description="Bugfix",
            authors="",
            scope="(extractor)",
            breaking=False,
            commit_type="chore",
        ),
        Change(
            issue_ref="27",
            description="Upgrade python",
            authors="(tom)",
            scope="",
            breaking=True,
            commit_type="custom",
        ),
        Change(
            issue_ref="28",
            description="Update config",
            authors="(edgy)",
            scope="(config)",
            breaking=False,
            commit_type="feat",
        ),
    ]
    random.shuffle(changes)

    assert sorted(changes) == [
        Change(
            issue_ref="24",
            description="A description",
            authors="(edgy)",
            scope="(writer)",
            breaking=True,
            commit_type="misc",
        ),
        Change(
            issue_ref="27",
            description="Upgrade python",
            authors="(tom)",
            scope="",
            breaking=True,
            commit_type="custom",
        ),
        Change(
            issue_ref="28",
            description="Update config",
            authors="(edgy)",
            scope="(config)",
            breaking=False,
            commit_type="feat",
        ),
        Change(
            issue_ref="25",
            description="Another change",
            authors="(tom)",
            scope="(extractor)",
            breaking=False,
            commit_type="ci",
        ),
        Change(
            issue_ref="26",
            description="Bugfix",
            authors="",
            scope="(extractor)",
            breaking=False,
            commit_type="chore",
        ),
        Change(
            issue_ref="23",
            description="Small change",
            authors="(edgy, tom)",
            scope="",
            breaking=False,
            commit_type="fix",
        ),
    ]
