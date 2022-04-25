def test_main_help(cli_runner):
    result = cli_runner.invoke(["--help"])

    assert result.exit_code == 0
    expected = """Usage: changelog-gen [OPTIONS]

  Generate a change log from release_notes/* files

Options:
  --date-format TEXT              The date format for strftime - empty string
                                  allowed

  --commit / --no-commit          Commit changes made to changelog after writing
  --allow-dirty / --no-allow-dirty
                                  Don't abort if branch contains uncommited
                                  changes

  --dry-run                       Don't write release notes to check for errors
  --release / --no-release        Use bumpversion to tag the release
  --version-tag TEXT              Provide the desired version tag, skip auto
                                  generation.

  --post-process-url TEXT         Rest API endpoint to post release version for
                                  each issue

  --post-process-auth-env TEXT    Name of the ENV variable that contains the
                                  rest API basic auth content

  -v, --version                   Show the version and exit.
  --help                          Show this message and exit.
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
