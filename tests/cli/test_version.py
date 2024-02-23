import pytest

import changelog_gen


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_command_version(cli_runner, flag):
    result = cli_runner.invoke([flag])

    assert result.exit_code == 0
    assert result.output == f"changelog {changelog_gen.VERSION}\n"
