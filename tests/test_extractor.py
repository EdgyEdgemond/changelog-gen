import random
from unittest import mock

import pytest

from changelog_gen import extractor
from changelog_gen.config import CommitType, Config
from changelog_gen.extractor import Change, ReleaseNoteExtractor
from changelog_gen.vcs import Git


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
def conventional_commits(multiversion_repo):
    f = multiversion_repo.workspace / "hello.txt"
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
    return hashes


@pytest.mark.backwards_compat()
@pytest.mark.usefixtures("multiversion_repo")
def test_init_with_no_release_notes():
    cfg = Config()
    git = mock.Mock()
    e = ReleaseNoteExtractor(cfg, git)
    assert e.has_release_notes is False


@pytest.mark.backwards_compat()
def test_init_with_release_notes_non_dir(multiversion_repo):
    path = multiversion_repo.workspace
    r = path / "release_notes"
    r.write_text("not a dir")

    cfg = Config()
    git = mock.Mock()

    e = ReleaseNoteExtractor(cfg, git)

    assert e.has_release_notes is False


@pytest.mark.backwards_compat()
@pytest.mark.usefixtures("_breaking_release_notes")
def test_breaking_notes_extraction():
    cfg = Config()
    git = Git()

    e = ReleaseNoteExtractor(cfg, git)

    sections = e.extract("0.0.2")

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


def test_git_commit_extraction(conventional_commits):
    hashes = conventional_commits
    cfg = Config()
    git = Git()

    e = ReleaseNoteExtractor(cfg, git)

    sections = e.extract("0.0.2")

    assert sections == {
        "Features and Improvements": {
            "2": Change("2", "Detail about 2", short_hash=hashes[5][:7], commit_hash=hashes[5], commit_type="feat"),
            "3": Change(
                "3",
                "Detail about 3",
                breaking=True,
                scope="(`docs`)",
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
                scope="(`config`)",
                short_hash=hashes[0][:7],
                commit_hash=hashes[0],
                commit_type="fix",
            ),
        },
    }


def test_git_commit_extraction_handles_random_tags(conventional_commits, multiversion_repo):
    hashes = conventional_commits
    multiversion_repo.api.create_tag("a-random-tag")
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("Detail about 5.")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("fix: Detail about 5")
    hashes.append(str(multiversion_repo.api.head.commit))

    cfg = Config()
    git = Git()

    e = ReleaseNoteExtractor(cfg, git)

    sections = e.extract("0.0.2")

    assert sections == {
        "Bug fixes": {
            "__0__": Change(
                "__0__",
                "Detail about 5",
                short_hash=hashes[6][:7],
                commit_hash=hashes[6],
                commit_type="fix",
            ),
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
                scope="(`config`)",
                short_hash=hashes[0][:7],
                commit_hash=hashes[0],
                commit_type="fix",
            ),
        },
        "Features and Improvements": {
            "2": Change("2", "Detail about 2", short_hash=hashes[5][:7], commit_hash=hashes[5], commit_type="feat"),
            "3": Change(
                "3",
                "Detail about 3",
                breaking=True,
                scope="(`docs`)",
                short_hash=hashes[2][:7],
                commit_hash=hashes[2],
                commit_type="feat",
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

    cfg = Config(
        commit_types={
            "custom": CommitType("Bug fixes"),
            "feat": CommitType("Features and Improvements"),
            "bug": CommitType("Bug fixes"),
        },
    )
    git = Git()

    e = ReleaseNoteExtractor(cfg, git)

    sections = e.extract("0.0.2")

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


def test_git_commit_extraction_picks_up_additional_allowed_characted(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    hashes = []
    for msg in [
        """fix: Ensure one/two chars are allowed `and` highlighting, but random PR link ignored. (#20)

With some details

BREAKING CHANGE:
Refs: #1
""",
    ]:
        f.write_text(msg)
        multiversion_repo.run("git add hello.txt")
        multiversion_repo.api.index.commit(msg)
        hashes.append(str(multiversion_repo.api.head.commit))

    cfg = Config()
    git = Git()

    e = ReleaseNoteExtractor(cfg, git)

    sections = e.extract("0.0.2")

    assert sections == {
        "Bug fixes": {
            "1": Change(
                "1",
                "Ensure one/two chars are allowed `and` highlighting, but random PR link ignored.",
                breaking=True,
                short_hash=hashes[0][:7],
                commit_hash=hashes[0],
                commit_type="fix",
            ),
        },
    }


@pytest.mark.backwards_compat()
@pytest.mark.usefixtures("_valid_release_notes")
def test_invalid_notes_skipped():
    cfg = Config(commit_types={"fix": CommitType("Fix")})
    git = Git()

    e = ReleaseNoteExtractor(cfg, git)

    sections = e.extract("0.0.2")

    assert sections == {
        "Fix": {
            "1": Change("1", "Detail about 1", "fix"),
            "4": Change("4", "Detail about 4", "fix"),
        },
    }


def test_unique_issues():
    cfg = Config(commit_types={"bug": CommitType("BugFix"), "feat": CommitType("Features")})
    git = mock.Mock()

    e = ReleaseNoteExtractor(cfg, git)

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


@pytest.mark.backwards_compat()
@pytest.mark.usefixtures("_valid_release_notes")
def test_dry_run_clean_keeps_files(release_notes):
    cfg = Config()
    git = mock.Mock()

    e = ReleaseNoteExtractor(cfg, git, dry_run=True)

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


@pytest.mark.backwards_compat()
@pytest.mark.usefixtures("_valid_release_notes")
def test_clean_removes_all_non_dotfiles(release_notes):
    """Clean should not remove .gitkeep files etc."""
    cfg = Config()
    git = mock.Mock()

    e = ReleaseNoteExtractor(cfg, git)

    e.clean()

    assert [f.name for f in release_notes.iterdir()] == [".file"]


@pytest.mark.parametrize(
    ("sections", "commit_types", "expected_semver"),
    [
        ({"header": {"1": Change("1", "desc", "fix")}}, {"feat": CommitType("h", "minor")}, "patch"),
        ({"header": {"1": Change("1", "desc", "feat")}}, {"feat": CommitType("h", "minor")}, "patch"),
        ({"header": {"1": Change("1", "desc", "fix", breaking=True)}}, {"feat": CommitType("h", "minor")}, "minor"),
        ({"header": {"1": Change("1", "desc", "feat", breaking=True)}}, {"feat": CommitType("h", "minor")}, "minor"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": CommitType("h", "patch")}, "patch"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": CommitType("h", "minor")}, "patch"),
        (
            {"header": {"1": Change("1", "desc", "custom", breaking=True)}},
            {"custom": CommitType("h", "minor")},
            "minor",
        ),
    ],
)
def test_extract_version_tag_version_zero(sections, commit_types, expected_semver):
    bv = mock.Mock()
    bv.get_version_info = mock.Mock(return_value={"new": "0.0.0", "current": "0.0.0"})
    cfg = Config(commit_types=commit_types)

    extractor.extract_version_tag(sections, cfg, bv)

    assert bv.get_version_info.call_args == mock.call(expected_semver)


@pytest.mark.parametrize(
    ("sections", "commit_types", "expected_semver"),
    [
        ({"header": {"1": Change("1", "desc", "fix")}}, {"feat": CommitType("h", "minor")}, "patch"),
        ({"header": {"1": Change("1", "desc", "feat")}}, {"feat": CommitType("h", "minor")}, "minor"),
        ({"header": {"1": Change("1", "desc", "fix", breaking=True)}}, {"feat": CommitType("h", "minor")}, "major"),
        ({"header": {"1": Change("1", "desc", "feat", breaking=True)}}, {"feat": CommitType("h", "minor")}, "major"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": CommitType("h", "patch")}, "patch"),
        ({"header": {"1": Change("1", "desc", "custom")}}, {"custom": CommitType("h", "minor")}, "minor"),
        (
            {"header": {"1": Change("1", "desc", "custom", breaking=True)}},
            {"custom": CommitType("h", "minor")},
            "major",
        ),
    ],
)
def test_extract_version_tag(sections, commit_types, expected_semver):
    bv = mock.Mock()
    bv.get_version_info = mock.Mock(return_value={"new": "1.0.0", "current": "1.0.0"})
    cfg = Config(commit_types=commit_types)

    extractor.extract_version_tag(sections, cfg, bv)

    assert bv.get_version_info.call_args == mock.call(expected_semver)


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
