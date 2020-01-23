def test_main_help(cli_runner):
    result = cli_runner.invoke(["--help"])

    assert result.exit_code == 0
    expected = """Usage: changelog-gen [OPTIONS]

  Generate a change log from release_notes/* files

Options:
  --dry-run      Don't write release notes to check for errors
  -v, --version  Show the version and exit.
  --help         Show this message and exit.
"""
    assert result.output == expected


def test_init_help(init_cli_runner):
    result = init_cli_runner.invoke(["--help"])

    assert result.exit_code == 0
    expected = """Usage: changelog-init [OPTIONS]

  Generate an empty CHANGELOG file

Options:
  --file-format TEXT  File format to generate
  -v, --version       Show the version and exit.
  --help              Show this message and exit.
"""
    assert result.output == expected
