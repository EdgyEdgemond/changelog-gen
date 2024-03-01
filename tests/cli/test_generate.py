from unittest import mock

import pytest
import typer
from freezegun import freeze_time

from changelog_gen.cli import command
from changelog_gen.config import PostProcessConfig


@pytest.fixture()
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


@pytest.fixture()
def changelog(git_repo):
    p = git_repo.workspace / "CHANGELOG.md"
    p.write_text("# Changelog\n")
    git_repo.run("git add CHANGELOG.md")
    git_repo.api.index.commit("commit changelog")
    return p


@pytest.fixture()
def _empty_release_notes(git_repo):
    r = git_repo.workspace / "release_notes"
    r.mkdir()

    git_repo.run("git add release_notes")
    git_repo.api.index.commit("commit release_notes")


@pytest.fixture()
def _release_notes(git_repo):
    r = git_repo.workspace / "release_notes"
    r.mkdir()
    f = r / ".file"
    f.write_text("")

    for i, note in enumerate(["1.fix", "2.feat", "3.feat", "4.fix"], 1):
        n = r / note
        n.write_text(f"Detail about {i}")

    git_repo.run("git add release_notes")
    git_repo.api.index.commit("commit release_notes")


@pytest.fixture()
def _breaking_release_notes(git_repo):
    r = git_repo.workspace / "release_notes"
    r.mkdir()
    f = r / ".file"
    f.write_text("")

    for i, note in enumerate(["1.fix", "2.feat!", "3.feat", "4.fix"], 1):
        n = r / note
        n.write_text(f"Detail about {i}")

    git_repo.run("git add release_notes")
    git_repo.api.index.commit("commit release_notes")


@pytest.fixture()
def setup(git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 1.0.0
commit = true
tag = true
""",
    )

    git_repo.run("git add setup.cfg")
    git_repo.api.index.commit("commit setup.cfg")

    return p


@pytest.fixture()
def post_process_setup(git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
commit = true
post_process =
    url=https://my-api/{issue_ref}/release
    auth_env=MY_API_AUTH
""",
    )

    git_repo.run("git add setup.cfg")
    git_repo.api.index.commit("commit setup.cfg")

    return p


@pytest.mark.usefixtures("cwd")
def test_generate_aborts_if_changelog_missing(gen_cli_runner):
    result = gen_cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "No CHANGELOG file detected, run `changelog init`\n"


@pytest.mark.usefixtures("changelog")
def test_generate_aborts_if_no_release_notes_directory(gen_cli_runner):
    result = gen_cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "No release notes directory found.\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_aborts_if_dirty(gen_cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
allow_dirty = false
""",
    )
    result = gen_cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "Working directory is not clean. Use `allow_dirty` configuration to ignore.\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_allows_dirty(gen_cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
allow_dirty = false
""",
    )
    result = gen_cli_runner.invoke(["--allow-dirty"])

    assert result.exit_code == 0


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_continues_if_allow_dirty_configured(gen_cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
allow_dirty = true
""",
    )
    result = gen_cli_runner.invoke()

    assert result.exit_code == 0


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_aborts_if_unsupported_current_branch(gen_cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
allow_dirty = true
allowed_branches = release_candidate
""",
    )
    result = gen_cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "Current branch not in allowed generation branches.\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_allows_supported_branch(gen_cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
allow_dirty = true
allowed_branches = master
""",
    )
    result = gen_cli_runner.invoke()

    assert result.exit_code == 0


@pytest.mark.usefixtures("changelog", "_release_notes")
def test_generate_wraps_errors(gen_cli_runner):
    result = gen_cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "Unable to get version data from bumpversion.\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_confirms_suggested_changes(gen_cli_runner):
    result = gen_cli_runner.invoke()

    assert result.exit_code == 0
    assert (
        result.output
        == """
## v1.1.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]

Write CHANGELOG for suggested version 1.1.0 [y/N]: \n""".lstrip()
    )


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_with_section_mapping(gen_cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
allow_dirty = true
section_mapping =
  feat=fix
""",
    )
    result = gen_cli_runner.invoke()

    assert result.exit_code == 0
    assert (
        result.output
        == """
## v0.0.1

### Bug fixes

- Detail about 1 [#1]
- Detail about 2 [#2]
- Detail about 3 [#3]
- Detail about 4 [#4]

Write CHANGELOG for suggested version 0.0.1 [y/N]: \n""".lstrip()
    )


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_with_custom_sections(gen_cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 1.1.0
commit = true
tag = true

[changelog_gen]
allow_dirty = true
sections =
  feat=My Features
  fix=My Fixes
""",
    )
    result = gen_cli_runner.invoke()

    assert result.exit_code == 0
    assert (
        result.output
        == """
## v1.2.0

### My Features

- Detail about 2 [#2]
- Detail about 3 [#3]

### My Fixes

- Detail about 1 [#1]
- Detail about 4 [#4]

Write CHANGELOG for suggested version 1.2.0 [y/N]: \n""".lstrip()
    )


@pytest.mark.usefixtures("git_repo", "_release_notes", "setup")
def test_generate_writes_to_file(
    gen_cli_runner,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
    result = gen_cli_runner.invoke()

    assert result.exit_code == 0

    assert (
        changelog.read_text()
        == """
# Changelog

## v1.1.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]
""".lstrip()
    )


@pytest.mark.usefixtures("_breaking_release_notes", "setup")
def test_generate_suggests_major_version_for_breaking_change(
    gen_cli_runner,
    git_repo,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
    result = gen_cli_runner.invoke(["--commit"])

    assert result.exit_code == 0

    assert (
        changelog.read_text()
        == """
# Changelog

## v2.0.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]
""".lstrip()
    )
    assert git_repo.api.head.commit.message == "Update CHANGELOG for 2.0.0\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_creates_release(
    gen_cli_runner,
    git_repo,
    monkeypatch,
):
    monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
    result = gen_cli_runner.invoke(["--commit", "--release"])

    assert result.exit_code == 0
    assert git_repo.api.head.commit.message == "Bump version: 1.0.0 → 1.1.0\n"


@pytest.mark.usefixtures("changelog", "_release_notes")
def test_generate_creates_release_using_config(
    gen_cli_runner,
    git_repo,
    monkeypatch,
):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
commit = true
release = true
""",
    )

    git_repo.run("git add setup.cfg")
    git_repo.api.index.commit("commit setup.cfg")

    monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
    result = gen_cli_runner.invoke()

    assert result.exit_code == 0
    assert git_repo.api.head.commit.message == "Bump version: 0.0.0 → 0.0.1\n"


@pytest.mark.usefixtures("setup", "_release_notes")
def test_generate_uses_supplied_version_tag(
    gen_cli_runner,
    git_repo,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
    result = gen_cli_runner.invoke(["--version-tag", "0.3.2", "--commit"])

    assert result.exit_code == 0
    assert (
        changelog.read_text()
        == """
# Changelog

## v0.3.2

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]
""".lstrip()
    )
    assert git_repo.api.head.commit.message == "Update CHANGELOG for 0.3.2\n"


@pytest.mark.usefixtures("git_repo", "_release_notes", "setup")
def test_generate_dry_run(
    gen_cli_runner,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
    result = gen_cli_runner.invoke(["--dry-run"])

    assert result.exit_code == 0

    assert (
        changelog.read_text()
        == """
# Changelog
""".lstrip()
    )


@pytest.mark.usefixtures("git_repo", "_empty_release_notes", "setup")
def test_generate_reject_empty(
    gen_cli_runner,
    changelog,
):
    result = gen_cli_runner.invoke(["--reject-empty"])

    assert result.exit_code == 0
    assert result.output == "No changes present and reject_empty configured.\n"

    assert (
        changelog.read_text()
        == """
# Changelog
""".lstrip()
    )


class TestDelegatesToPerIssuePostProcess:
    # The behaviour of per_issue_post_process are tested in test_post_processor

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_load_config(
        self,
        gen_cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        result = gen_cli_runner.invoke()

        assert result.exit_code == 0
        assert post_process_mock.call_args_list == [
            mock.call(
                PostProcessConfig(
                    url="https://my-api/{issue_ref}/release",
                    auth_env="MY_API_AUTH",
                ),
                ["1", "2", "3", "4"],
                "0.0.1",
                dry_run=False,
            ),
        ]

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_generate_post_process_url(
        self,
        gen_cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        api_url = "https://my-api/{issue_ref}/comment"
        result = gen_cli_runner.invoke(["--post-process-url", api_url])

        assert result.exit_code == 0
        assert post_process_mock.call_args_list == [
            mock.call(
                PostProcessConfig(
                    url=api_url,
                    auth_env="MY_API_AUTH",
                ),
                ["1", "2", "3", "4"],
                "0.0.1",
                dry_run=False,
            ),
        ]

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_generate_post_process_auth_env(
        self,
        gen_cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        result = gen_cli_runner.invoke(["--post-process-auth-env", "OTHER_API_AUTH"])

        assert result.exit_code == 0
        assert post_process_mock.call_args_list == [
            mock.call(
                PostProcessConfig(
                    url="https://my-api/{issue_ref}/release",
                    auth_env="OTHER_API_AUTH",
                ),
                ["1", "2", "3", "4"],
                "0.0.1",
                dry_run=False,
            ),
        ]

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_generate_dry_run(
        self,
        gen_cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        result = gen_cli_runner.invoke(["--dry-run"])

        assert result.exit_code == 0
        assert post_process_mock.call_count == 0

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_generate_decline_changes(
        self,
        gen_cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=False))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        result = gen_cli_runner.invoke([])

        assert result.exit_code == 0
        assert post_process_mock.call_count == 0


@freeze_time("2022-04-14T16:45:03")
class TestGenerateWithDate:
    @pytest.mark.usefixtures("_release_notes", "changelog")
    def test_using_config(self, gen_cli_runner, git_repo, monkeypatch):
        p = git_repo.workspace / "setup.cfg"
        p.write_text(
            """
            [bumpversion]
            current_version = 0.0.0
            commit = true
            tag = true

            [changelog_gen]
            commit = true
            release = true
            date_format =on %%Y-%%m-%%d
        """.strip(),
        )

        git_repo.run("git add setup.cfg")
        git_repo.api.index.commit("commit setup.cfg")

        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        gen_cli_runner.invoke()

        assert writer_mock.add_version.call_args == mock.call("v0.0.1 on 2022-04-14")

    @pytest.mark.usefixtures("_release_notes", "changelog", "setup")
    def test_using_cli(self, gen_cli_runner, monkeypatch):
        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        gen_cli_runner.invoke(["--date-format", "(%Y-%m-%d at %H:%M)"])

        assert writer_mock.add_version.call_args == mock.call("v1.1.0 (2022-04-14 at 16:45)")

    @pytest.mark.usefixtures("_release_notes", "changelog")
    def test_override_config(self, gen_cli_runner, git_repo, monkeypatch):
        p = git_repo.workspace / "setup.cfg"
        p.write_text(
            """
            [bumpversion]
            current_version = 0.0.0
            commit = true
            tag = true

            [changelog_gen]
            commit = true
            release = true
            date_format =on %%Y-%%m-%%d
        """.strip(),
        )

        git_repo.run("git add setup.cfg")
        git_repo.api.index.commit("commit setup.cfg")

        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        gen_cli_runner.invoke(["--date-format", "(%Y-%m-%d at %H:%M)"])

        assert writer_mock.add_version.call_args == mock.call("v0.0.1 (2022-04-14 at 16:45)")

    @pytest.mark.usefixtures("_release_notes", "changelog")
    def test_override_config_and_disable(self, gen_cli_runner, git_repo, monkeypatch):
        p = git_repo.workspace / "setup.cfg"
        p.write_text(
            """
            [bumpversion]
            current_version = 0.0.0
            commit = true
            tag = true

            [changelog_gen]
            commit = true
            release = true
            date_format =on %%Y-%%m-%%d
        """.strip(),
        )

        git_repo.run("git add setup.cfg")
        git_repo.api.index.commit("commit setup.cfg")

        monkeypatch.setattr(typer, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        gen_cli_runner.invoke(["--date-format", ""])

        assert writer_mock.add_version.call_args == mock.call("v0.0.1")
