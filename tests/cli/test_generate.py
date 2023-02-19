from unittest import mock

import click
import pytest
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
current_version = 0.0.0
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
post_process =
    url=https://my-api/{issue_ref}/release
    auth_env=MY_API_AUTH
""",
    )

    git_repo.run("git add setup.cfg")
    git_repo.api.index.commit("commit setup.cfg")

    return p


@pytest.mark.usefixtures("cwd")
def test_generate_aborts_if_changelog_missing(cli_runner):
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "No CHANGELOG file detected, run changelog-init\nAborted!\n"


@pytest.mark.usefixtures("changelog")
def test_generate_aborts_if_no_release_notes_directory(cli_runner):
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "No release notes directory found.\nAborted!\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_aborts_if_dirty(cli_runner, git_repo):
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
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "Working directory is not clean. Use `allow_dirty` configuration to ignore.\nAborted!\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_allows_dirty(cli_runner, git_repo):
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
    result = cli_runner.invoke(["--allow-dirty"])

    assert result.exit_code == 0


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_continues_if_allow_dirty_configured(cli_runner, git_repo):
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
    result = cli_runner.invoke()

    assert result.exit_code == 0


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_aborts_if_unsupported_current_branch(cli_runner, git_repo):
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
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "Current branch not in allowed generation branches.\nAborted!\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_allows_supported_branch(cli_runner, git_repo):
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
    result = cli_runner.invoke()

    assert result.exit_code == 0


@pytest.mark.usefixtures("changelog", "_release_notes")
def test_generate_wraps_errors(cli_runner):
    result = cli_runner.invoke()

    assert result.exit_code == 1
    assert result.output == "Unable to get version data from bumpversion.\nAborted!\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_confirms_suggested_changes(cli_runner):
    result = cli_runner.invoke()

    assert result.exit_code == 0
    assert (
        result.output
        == """
## v0.1.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]

Write CHANGELOG for suggested version 0.1.0 [y/N]: \n""".lstrip()
    )


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_with_section_mapping(cli_runner, git_repo):
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
    result = cli_runner.invoke()

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
def test_generate_with_custom_sections(cli_runner, git_repo):
    p = git_repo.workspace / "setup.cfg"
    p.write_text(
        """
[bumpversion]
current_version = 0.0.0
commit = true
tag = true

[changelog_gen]
allow_dirty = true
sections =
  feat=My Features
  fix=My Fixes
""",
    )
    result = cli_runner.invoke()

    assert result.exit_code == 0
    assert (
        result.output
        == """
## v0.1.0

### My Features

- Detail about 2 [#2]
- Detail about 3 [#3]

### My Fixes

- Detail about 1 [#1]
- Detail about 4 [#4]

Write CHANGELOG for suggested version 0.1.0 [y/N]: \n""".lstrip()
    )


@pytest.mark.usefixtures("git_repo", "_release_notes", "setup")
def test_generate_writes_to_file(
    cli_runner,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke()

    assert result.exit_code == 0

    assert (
        changelog.read_text()
        == """
# Changelog

## v0.1.0

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
    cli_runner,
    git_repo,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke(["--commit"])

    assert result.exit_code == 0

    assert (
        changelog.read_text()
        == """
# Changelog

## v1.0.0

### Features and Improvements

- Detail about 2 [#2]
- Detail about 3 [#3]

### Bug fixes

- Detail about 1 [#1]
- Detail about 4 [#4]
""".lstrip()
    )
    assert git_repo.api.head.commit.message == "Update CHANGELOG for 1.0.0\n"


@pytest.mark.usefixtures("changelog", "_release_notes", "setup")
def test_generate_creates_release(
    cli_runner,
    git_repo,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke(["--commit", "--release"])

    assert result.exit_code == 0
    assert git_repo.api.head.commit.message == "Bump version: 0.0.0 → 0.1.0\n"


@pytest.mark.usefixtures("changelog", "_release_notes")
def test_generate_creates_release_using_config(
    cli_runner,
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

    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke()

    assert result.exit_code == 0
    assert git_repo.api.head.commit.message == "Bump version: 0.0.0 → 0.1.0\n"


@pytest.mark.usefixtures("setup", "_release_notes")
def test_generate_uses_supplied_version_tag(
    cli_runner,
    git_repo,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke(["--version-tag", "0.3.2", "--commit"])

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
    cli_runner,
    changelog,
    monkeypatch,
):
    monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
    result = cli_runner.invoke(["--dry-run"])

    assert result.exit_code == 0

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
        cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        result = cli_runner.invoke()

        assert result.exit_code == 0
        assert post_process_mock.call_args_list == [
            mock.call(
                PostProcessConfig(
                    url="https://my-api/{issue_ref}/release",
                    auth_env="MY_API_AUTH",
                ),
                ["1", "2", "3", "4"],
                "0.1.0",
                dry_run=False,
            ),
        ]

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_generate_post_process_url(
        self,
        cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        api_url = "https://my-api/{issue_ref}/comment"
        result = cli_runner.invoke(["--post-process-url", api_url])

        assert result.exit_code == 0
        assert post_process_mock.call_args_list == [
            mock.call(
                PostProcessConfig(
                    url=api_url,
                    auth_env="MY_API_AUTH",
                ),
                ["1", "2", "3", "4"],
                "0.1.0",
                dry_run=False,
            ),
        ]

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_generate_post_process_auth_env(
        self,
        cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        result = cli_runner.invoke(["--post-process-auth-env", "OTHER_API_AUTH"])

        assert result.exit_code == 0
        assert post_process_mock.call_args_list == [
            mock.call(
                PostProcessConfig(
                    url="https://my-api/{issue_ref}/release",
                    auth_env="OTHER_API_AUTH",
                ),
                ["1", "2", "3", "4"],
                "0.1.0",
                dry_run=False,
            ),
        ]

    @pytest.mark.usefixtures("git_repo", "_release_notes", "changelog", "post_process_setup")
    def test_generate_dry_run(
        self,
        cli_runner,
        monkeypatch,
    ):
        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        post_process_mock = mock.MagicMock()
        monkeypatch.setattr(command, "per_issue_post_process", post_process_mock)

        result = cli_runner.invoke(["--dry-run"])

        assert result.exit_code == 0
        assert post_process_mock.call_args_list == [
            mock.call(
                PostProcessConfig(
                    url="https://my-api/{issue_ref}/release",
                    auth_env="MY_API_AUTH",
                ),
                ["1", "2", "3", "4"],
                "0.1.0",
                dry_run=True,
            ),
        ]


@freeze_time("2022-04-14T16:45:03")
class TestGenerateWithDate:
    @pytest.mark.usefixtures("_release_notes", "changelog")
    def test_using_config(self, cli_runner, git_repo, monkeypatch):
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

        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        cli_runner.invoke()

        assert writer_mock.add_version.call_args == mock.call("v0.1.0 on 2022-04-14")

    @pytest.mark.usefixtures("_release_notes", "changelog", "setup")
    def test_using_cli(self, cli_runner, monkeypatch):
        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        cli_runner.invoke(["--date-format", "(%Y-%m-%d at %H:%M)"])

        assert writer_mock.add_version.call_args == mock.call("v0.1.0 (2022-04-14 at 16:45)")

    @pytest.mark.usefixtures("_release_notes", "changelog")
    def test_override_config(self, cli_runner, git_repo, monkeypatch):
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

        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        cli_runner.invoke(["--date-format", "(%Y-%m-%d at %H:%M)"])

        assert writer_mock.add_version.call_args == mock.call("v0.1.0 (2022-04-14 at 16:45)")

    @pytest.mark.usefixtures("_release_notes", "changelog")
    def test_override_config_and_disable(self, cli_runner, git_repo, monkeypatch):
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

        monkeypatch.setattr(click, "confirm", mock.MagicMock(return_value=True))
        writer_mock = mock.MagicMock()
        monkeypatch.setattr(command.writer, "new_writer", mock.MagicMock(return_value=writer_mock))

        cli_runner.invoke(["--date-format", ""])

        assert writer_mock.add_version.call_args == mock.call("v0.1.0")
