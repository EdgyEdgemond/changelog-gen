import click.testing
import pytest

import changelog_gen.cli.command


class GenCliRunner(click.testing.CliRunner):
    target = changelog_gen.cli.command.gen

    def invoke(self, *args, **kwargs):
        result = super().invoke(self.target, *args, **kwargs)
        if result.exception:
            if isinstance(result.exception, SystemExit):
                # The error is already properly handled. Print it and return.
                print(result.output)
            else:
                raise result.exception.with_traceback(result.exc_info[2])
        return result


class InitCliRunner(GenCliRunner):
    target = changelog_gen.cli.command.init


@pytest.fixture
def cli_runner():
    return GenCliRunner()


@pytest.fixture
def init_cli_runner():
    return InitCliRunner()
