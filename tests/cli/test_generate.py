from unittest import mock

import click
import pytest


@pytest.fixture
def git_repo(git_repo):
    path = git_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world!")

    git_repo.run("git add hello.txt")
    git_repo.api.index.commit("initial commit")

    git_repo.api.create_tag("0.0.1")

    f.write_text("hello world! v2")
    git_repo.run("git add hello.txt")
    git_repo.api.index.commit("update")

    git_repo.api.create_tag("0.0.2")

    return git_repo


@pytest.fixture
def changelog(git_repo):
    p = git_repo.workspace / "CHANGELOG.md"
    p.write_text("# Changelog\n")
    git_repo.run("git add CHANGELOG.md")
    git_repo.api.index.commit("commit changelog")
    return p


@pytest.fixture
def release_notes(git_repo):
    r = git_repo.workspace / "release_notes"
    r.mkdir()
    f = r / ".file"
    f.write_text("")

    for i, note in enumerate(["1.fix", "2.feat", "3.feat", "4.fix"], 1):
        n = r / note
        n.write_text("Detail about {}".format(i))

    git_repo.run("git add release_notes")
    git_repo.api.index.commit("commit release_notes")


@pytest.fixture
def breaking_release_notes(git_repo):
    r = git_repo.workspace / "release_notes"
    r.mkdir()
    f = r / ".file"
    f.write_text("")

    for i, note in enumerate(["1.fix", "2.feat!", "3.feat", "4.fix"], 1):
        n = r / note
        n.write_text("Detail about {}".format(i))

    git_repo.run("git add release_notes")
    git_repo.api.index.commit("commit release_notes")


@pytest.fixture
def setup(git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text("""
[bumpversion]
current_version = 0.0.0
commit = true
tag = true
""")

    git_repo.run("git add setup.cfg")
    git_repo.api.index.commit("commit setup.cfg")

    return p


def test_generate_aborts_if_changelog_missing(cli_runner, cwd):
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "No CHANGELOG file detected, run changelog-init\nAborted!\n"


def test_generate_aborts_if_no_release_notes_directory(cli_runner, changelog):
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "No release notes directory found.\nAborted!\n"


def test_generate_wraps_errors(cli_runner, changelog, release_notes):
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "Unable to get version data from bumpversion\nAborted!\n"


def test_generate_confirms_suggested_changes(cli_runner, changelog, release_notes, setup):
    result = cli_runner.invoke()

    assert result.exit_code == 0
    assert result.output == """
## v0.1.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]

Write CHANGELOG for suggested version 0.1.0 [y/N]: \n""".lstrip()


def test_generate_writes_to_file(
    cli_runner,
    git_repo,
    changelog,
    release_notes,
    setup,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke()

    assert result.exit_code == 0

    assert changelog.read_text() == """
# Changelog

## v0.1.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]
""".lstrip()
    assert git_repo.api.head.commit.message == "Update CHANGELOG for 0.1.0\n"


def test_generate_suggests_major_version_for_breaking_change(
    cli_runner,
    git_repo,
    changelog,
    breaking_release_notes,
    setup,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke()

    assert result.exit_code == 0

    assert changelog.read_text() == """
# Changelog

## v1.0.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]
""".lstrip()
    assert git_repo.api.head.commit.message == "Update CHANGELOG for 1.0.0\n"


def test_generate_creates_release(
    cli_runner,
    git_repo,
    changelog,
    release_notes,
    setup,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke(["--release"])

    assert result.exit_code == 0
    assert git_repo.api.head.commit.message == "Bump version: 0.0.0 → 0.1.0\n"


def test_generate_creates_release_using_config(
    cli_runner,
    git_repo,
    changelog,
    release_notes,
    monkeypatch,
):
    p = git_repo.workspace / "setup.cfg"
    p.write_text("""
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
release = true
""")

    git_repo.run("git add setup.cfg")
    git_repo.api.index.commit("commit setup.cfg")

    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke()

    assert result.exit_code == 0
    assert git_repo.api.head.commit.message == "Bump version: 0.0.0 → 0.1.0\n"


def test_generate_uses_supplied_version_tag(
    cli_runner,
    git_repo,
    changelog,
    release_notes,
    setup,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke(["--version-tag", "0.3.2"])

    assert result.exit_code == 0
    assert changelog.read_text() == """
# Changelog

## v0.3.2

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]
""".lstrip()
    assert git_repo.api.head.commit.message == "Update CHANGELOG for 0.3.2\n"


def test_generate_dry_run(
    cli_runner,
    git_repo,
    changelog,
    release_notes,
    setup,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke(["--dry-run"])

    assert result.exit_code == 0

    assert changelog.read_text() == """
# Changelog
""".lstrip()
