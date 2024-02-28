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


def test_get_latest_info_branch(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")

    info = Git().get_latest_tag_info()

    assert info["branch"] == "master"


@pytest.mark.usefixtures("multiversion_repo")
def test_get_latest_info_clean():
    info = Git().get_latest_tag_info()

    assert info["dirty"] is False


def test_get_latest_info_dirty(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")

    info = Git().get_latest_tag_info()

    assert info["dirty"] is True
    assert info["distance_to_latest_tag"] == 0


def test_get_latest_info_untagged(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("untagged")

    info = Git().get_latest_tag_info()

    assert info["distance_to_latest_tag"] == 1


@pytest.mark.usefixtures("multiversion_repo")
def test_get_latest_info_current_version():
    info = Git().get_latest_tag_info()

    assert info["current_version"] == "0.0.2"


@pytest.mark.usefixtures("multiversion_v_repo")
def test_get_latest_info_current_version_vtag():
    info = Git().get_latest_tag_info()

    assert info["current_version"] == "0.0.2"


@pytest.mark.usefixtures("multiversion_repo")
def test_get_latest_info_current_tag():
    info = Git().get_latest_tag_info()

    assert info["current_tag"] == "0.0.2"


@pytest.mark.usefixtures("multiversion_v_repo")
def test_get_latest_info_current_tag_vtag():
    info = Git().get_latest_tag_info()

    assert info["current_tag"] == "v0.0.2"


def test_get_latest_info_commit_sha(multiversion_repo):
    head_hash = multiversion_repo.api.head.commit

    info = Git().get_latest_tag_info()

    assert info["commit_sha"] == str(head_hash)[:7]


@pytest.mark.usefixtures("git_repo")
def test_get_latest_info_raises_if_no_tags_found():
    with pytest.raises(errors.VcsError) as ex:
        Git().get_latest_tag_info()

    assert str(ex.value) == "Unable to get version number from git tags."


@pytest.mark.usefixtures("git_repo")
def test_get_latest_info_raises_if_rev_parse_fails(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "check_output",
        mock.Mock(side_effect=[b"", subprocess.CalledProcessError(returncode=1, cmd="")]),
    )
    with pytest.raises(errors.VcsError) as ex:
        Git().get_latest_tag_info()

    assert str(ex.value) == "Unable to get current git branch."


def test_add_path_stages_changes_for_commit(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    assert "Changes not staged for commit" in multiversion_repo.run("git status", capture=True)

    Git().add_path("hello.txt")

    assert "Changes not staged for commit" not in multiversion_repo.run("git status", capture=True)


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


def test_commit_no_changes_staged(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")

    Git().commit("new_version")

    assert "Changes not staged for commit" in multiversion_repo.run("git status", capture=True)


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
