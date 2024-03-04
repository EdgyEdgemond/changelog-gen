import subprocess
from unittest import mock

import pytest

from changelog_gen import errors
from changelog_gen.vcs import Git


@pytest.fixture()
def multiversion_repo(git_repo):
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


@pytest.fixture()
def multiversion_v_repo(git_repo):
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


def test_get_current_info_branch(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")

    info = Git().get_current_info()

    assert info["branch"] == "master"


@pytest.mark.usefixtures("multiversion_repo")
def test_get_current_info_clean():
    info = Git().get_current_info()

    assert info["dirty"] is False


def test_get_current_info_dirty(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")

    info = Git().get_current_info()

    assert info["dirty"] is True


@pytest.mark.usefixtures("git_repo")
def test_get_current_info_raises_if_rev_parse_fails(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "check_output",
        mock.Mock(side_effect=[b"", subprocess.CalledProcessError(returncode=1, cmd="")]),
    )
    with pytest.raises(errors.VcsError) as ex:
        Git().get_current_info()

    assert str(ex.value) == "Unable to get current git branch."


@pytest.mark.usefixtures("multiversion_repo")
def test_get_find_tag():
    tag = Git().find_tag("0.0.2")

    assert tag == "0.0.2"


@pytest.mark.usefixtures("multiversion_repo")
def test_get_find_tag_no_tag():
    tag = Git().find_tag("0.0.3")

    assert tag is None


@pytest.mark.usefixtures("multiversion_v_repo")
def test_get_find_tag_vtag():
    tag = Git().find_tag("0.0.2")

    assert tag == "v0.0.2"


def test_add_path_stages_changes_for_commit(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    assert "Changes not staged for commit" in multiversion_repo.run("git status", capture=True)

    Git().add_path("hello.txt")

    assert "Changes not staged for commit" not in multiversion_repo.run("git status", capture=True)


def test_add_path_dry_run(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")

    Git(dry_run=True).add_path("hello.txt")

    assert "Changes not staged for commit" in multiversion_repo.run("git status", capture=True)


def test_commit_adds_message_with_version_string(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")

    Git().commit("new_version")

    assert multiversion_repo.api.head.commit.message == "Update CHANGELOG for new_version\n"


def test_commit_with_paths(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")

    Git().commit("new_version", ["hello.txt"])

    assert multiversion_repo.api.head.commit.message == "Update CHANGELOG for new_version\n"


def test_commit_dry_run(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")

    Git(dry_run=True).commit("new_version", ["hello.txt"])

    assert "Changes not staged for commit" in multiversion_repo.run("git status", capture=True)


def test_commit_no_changes_staged(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")

    with pytest.raises(errors.VcsError) as e:
        Git().commit("new_version")

    assert "Changes not staged for commit" in str(e.value)


def test_get_logs(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("commit log")
    hash1 = str(multiversion_repo.api.head.commit)

    f.write_text("hello world! v4")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("commit log 2: electric boogaloo")
    hash2 = str(multiversion_repo.api.head.commit)

    f.write_text("hello world! v5")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit(
        """Commit message 3

Formatted
""",
    )
    hash3 = str(multiversion_repo.api.head.commit)

    logs = Git().get_logs("0.0.2")
    assert logs == [
        [hash3[:7], hash3, "Commit message 3\n\nFormatted\n"],
        [hash2[:7], hash2, "commit log 2: electric boogaloo"],
        [hash1[:7], hash1, "commit log"],
    ]


@pytest.mark.usefixtures("multiversion_repo")
def test_get_logs_no_tag():

    logs = Git().get_logs(None)
    assert [log[2] for log in logs] == [
        "update",
        "initial commit",
    ]


def test_commit(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("commit log")

    f.write_text("hello world! v4")
    multiversion_repo.run("git add hello.txt")

    Git().commit("0.0.3")

    assert multiversion_repo.api.head.commit.message == "Update CHANGELOG for 0.0.3\n"


@pytest.mark.usefixtures("multiversion_repo")
def test_commit_no_changes():
    with pytest.raises(errors.VcsError) as ex:
        Git().commit("0.0.3")

    assert str(ex.value) == "Unable to commit: On branch master\nnothing to commit, working tree clean"


def test_revert(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("commit log")

    f.write_text("hello world! v4")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("commit log 2")

    assert multiversion_repo.api.head.commit.message == "commit log 2"

    Git().revert()

    assert multiversion_repo.api.head.commit.message == "commit log"


def test_revert_dry_run(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("commit log")

    f.write_text("hello world! v4")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("commit log 2")

    assert multiversion_repo.api.head.commit.message == "commit log 2"

    Git(dry_run=True).revert()

    assert multiversion_repo.api.head.commit.message == "commit log 2"
