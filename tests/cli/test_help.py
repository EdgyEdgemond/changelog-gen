def test_generate_help(cli_runner):
    result = cli_runner.invoke(["generate", "--help"])

    assert result.exit_code == 0
    expected = """Usage: changelog generate [OPTIONS]

  Generate changelog entries.

  Read release notes and generate a new CHANGELOG entry for the current version.

Options:
  --version-tag TEXT              Provide the desired version tag, skip auto
                                  generation.
  --post-process-url TEXT         Rest API endpoint to post release version
                                  notifications to.
  --post-process-auth-env TEXT    Name of the ENV variable that contains the
                                  rest API basic auth content.
  --date-format TEXT              The date format for strftime - empty string
                                  allowed.
  --dry-run / --no-dry-run        Don't write release notes, check for errors.
                                  [default: no-dry-run]
  --allow-dirty / --no-allow-dirty
                                  Don't abort if branch contains uncommitted
                                  changes.
  --release / --no-release        Use bumpversion to tag the release.
  --commit / --no-commit          Commit changes made to changelog after
                                  writing.
  -v, --version                   Print version and exit.
  --help                          Show this message and exit.
"""
    assert result.output == expected


def test_init_help(cli_runner):
    result = cli_runner.invoke(["init", "--help"])

    assert result.exit_code == 0
    expected = """Usage: changelog init [OPTIONS]

  Generate an empty CHANGELOG file.

  Detect and raise if a CHANGELOG already exists, if not create a new file.

Options:
  --file-format [md|rst]  File format to generate.  [default: md]
  -v, --version           Print version and exit.
  --help                  Show this message and exit.
"""
    assert result.output == expected
