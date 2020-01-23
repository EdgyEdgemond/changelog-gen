import pytest

import changelog_gen


@pytest.mark.parametrize("flag", ("--version", "-v"))
def test_command_version(cli_runner, flag):
    result = cli_runner.invoke([flag])

    assert result.exit_code == 0
    assert result.output == "changelog-gen, version {}\n".format(changelog_gen.VERSION)


@pytest.mark.parametrize("flag", ("--version", "-v"))
def test_init_command_version(init_cli_runner, flag):
    result = init_cli_runner.invoke([flag])

    assert result.exit_code == 0
    assert result.output == "changelog-gen, version {}\n".format(changelog_gen.VERSION)
