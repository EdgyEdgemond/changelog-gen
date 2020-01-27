import pytest

from changelog_gen import errors
from changelog_gen.vcs import Git


@pytest.fixture
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


def test_get_latest_info_branch(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")

    info = Git.get_latest_tag_info()

    assert info["branch"] == "master"


def test_get_latest_info_clean(multiversion_repo):
    info = Git.get_latest_tag_info()

    assert info["dirty"] is False


def test_get_latest_info_dirty(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")

    info = Git.get_latest_tag_info()

    assert info["dirty"] is True
    assert info["distance_to_latest_tag"] == 0


def test_get_latest_info_untagged(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"

    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")
    multiversion_repo.api.index.commit("untagged")

    info = Git.get_latest_tag_info()

    assert info["distance_to_latest_tag"] == 1


def test_get_latest_info_current_version(multiversion_repo):
    info = Git.get_latest_tag_info()

    assert info["current_version"] == "0.0.2"


def test_get_latest_info_commit_sha(multiversion_repo):
    head_hash = multiversion_repo.api.head.commit

    info = Git.get_latest_tag_info()

    assert info["commit_sha"] == str(head_hash)[:7]


def test_get_latest_info_raises_if_no_tags_found(git_repo):
    with pytest.raises(errors.VcsError):
        Git.get_latest_tag_info()


def test_add_path_stages_changes_for_commit(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    assert "Changes not staged for commit" in multiversion_repo.run("git status", True)

    Git.add_path("hello.txt")

    assert "Changes not staged for commit" not in multiversion_repo.run("git status", True)


def test_commit_adds_message_with_version_string(multiversion_repo):
    path = multiversion_repo.workspace
    f = path / "hello.txt"
    f.write_text("hello world! v3")
    multiversion_repo.run("git add hello.txt")

    Git.commit("new_version")

    assert multiversion_repo.api.head.commit.message == "Update CHANGELOG for new_version\n"
