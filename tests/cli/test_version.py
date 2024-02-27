import importlib.metadata

import pytest


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_command_version(cli_runner, flag):
    result = cli_runner.invoke([flag])
    version = importlib.metadata.version("changelog-gen")

    assert result.exit_code == 0
    assert result.output == f"changelog {version}\n"
