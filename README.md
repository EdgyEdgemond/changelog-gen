# Changelog Generator - v0.9.1
[![image](https://img.shields.io/pypi/v/changelog_gen.svg)](https://pypi.org/project/changelog_gen/)
[![image](https://img.shields.io/pypi/l/changelog_gen.svg)](https://pypi.org/project/changelog_gen/)
[![image](https://img.shields.io/pypi/pyversions/changelog_gen.svg)](https://pypi.org/project/changelog_gen/)
![style](https://github.com/EdgyEdgemond/changelog-gen/workflows/style/badge.svg)
![tests](https://github.com/EdgyEdgemond/changelog-gen/workflows/tests/badge.svg)
[![codecov](https://codecov.io/gh/EdgyEdgemond/changelog-gen/branch/master/graph/badge.svg)](https://codecov.io/gh/EdgyEdgemond/changelog-gen)

`changelog-gen` is a CHANGELOG generator intended to be used in conjunction
with [bump-my-version](https://github.com/callowayproject/bump-my-version) to generate
changelogs and create release tags.

## Migrating to 0.9 (Conventioanl Commit support)
Check the discussion
[here](https://github.com/EdgyEdgemond/changelog-gen/discussions/98) for
details on how to update usage to maintain legacy functionality or move over to
new features.

## Installation

```bash
pip install changelog-gen[bump-my-version]   # recommended

pip install changelog-gen[bump2version]  # bump2version support will be dropped in the future
```

or clone this repo and install with poetry.

```bash
poetry install --extras=bump-my-version
```

## Usage

`changelog` currently supports generating from commit logs using [Conventional
Commits](https://www.conventionalcommits.org/en/v1.0.0/), as well as reading
changes from a `release_notes` folder.

NOTE: `release_notes` support will be dropped in a future version, migration to
conventional commits is recommended.

See [Configuration](#Configuration) below for default commit type configuration
and how to customize them.

```md
## <version>

### Features and Improvements
- xxx
- xxx

### Bug fixes
- xxx
- xxx

### Documentation
- xxx
- xxx

### Miscellaneous
- xxx
- xxx
```

### Conventional commits

```
<type>[(optional scope)][!]: <description>

[optional body]

[optional footer(s)]
```

`description` allows typical `[a-zA-Z ]` sentences, as well as `[.,/]`
punctuation, and ``[`]`` for highlighting words.

i.e.
```
fix: This is a valid description, with punctuation and a `highlighted` word.
```

Optional footers that are parsed by `changelog-gen` are:

* `BREAKING CHANGE:`
* `Refs: [#]<issue_ref>`
* `Authors: (<author>, ...)`

The description is used to populate the changelog file. If the type includes
the optional `!` flag, or the `BREAKING CHANGE` footer, this will lead to a
major release being suggested.

### Release Notes

Files in the folder should use the format `{issue_number}.{type}`.

The contents of each file is used to populate the changelog file. If the type
ends with a `!` it denotes a breaking change has been made, this will lead to a
major release being suggested.

```bash
$ ls release_notes
  4.fix  7.fix

$ changelog generate

## v0.2.1

### Bug fixes

- Raise errors from internal classes, don't use click.echo() [#4]
- Update changelog line format to include issue number at the end. [#7]

Write CHANGELOG for suggested version 0.2.1 [y/N]: y
```

## Configuration

Of the command line arguments, most of them can be configured in `setup.cfg` or `pyproject.toml` to remove
the need to pass them in every time.

Example `pyproject.toml`:

```toml
[tool.changelog_gen]
commit = true
release = true
allow_dirty = false

[tool.changelog_gen.post_process]
  url = "https://your-domain.atlassian.net/rest/api/2/issue/ISSUE-::issue_ref::/comment"
  verb = "POST"
  body = '{"body": "Released on v::version::"}'
  auth_env = "JIRA_AUTH"
```

NOTE: setup.cfg is being deprecated, use `changelog migrate` to generate valid
toml from existing setup.cfg file.

Example `setup.cfg`:

```ini
[changelog_gen]
commit = true
release = true
allow_dirty = false
```

Example `pyproject.toml`:

```toml
[tool.changelog_gen]
commit = true
release = true
allow_dirty = false

[tool.changelog_gen.post_process]
  url = "https://your-domain.atlassian.net/rest/api/2/issue/ISSUE-::issue_ref::/comment"
  verb = "POST"
  body = '{"body": "Released on v::version::"}'
  auth_env = "JIRA_AUTH"
```

### Configuration file -- Global configuration

General configuration is grouped in a `[changelog_gen]` section.

#### `commit = (True | False)`
  _**[optional]**_<br />
  **default**: False

  Commit changes to the changelog after writing.

  Also available as `--commit` (e.g. `changelog generate --commit`)

#### `release = (True | False)`
  _**[optional]**_<br />
  **default**: False

  Use bumpversion to tag the release

  Also available as `--release` (e.g. `changelog generate --release`)

#### `allow_dirty = (True | False)`
  _**[optional]**_<br />
  **default**: False

  Don't abort if the current branch contains uncommitted changes

  Also available as `--allow-dirty` (e.g. `changelog generate --allow-dirty`)

#### `reject_empty = (True | False)`
  _**[optional]**_<br />
  **default**: False

  Abort if there are no release notes to add to the change log.

  Also available as `--reject-empty` (e.g. `changelog generate --reject-empty`)

#### `issue_link =`
  _**[optional]**_<br />
  **default**: None

  Create links in the CHANGELOG to the originating issue. A url that contains
  an `issue_ref` placeholder for replacement.

  Example:

```toml
[tool.changelog_gen]
issue_link = "http://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::"
```

#### `commit_link =`
  _**[optional]**_<br />
  **default**: None

  Create links in the CHANGELOG to the originating commit. A url that contains
  a `::commit_hash::` placeholder for replacement.

  Example:

```toml
[tool.changelog_gen]
commit_link = "http://github.com/EdgyEdgemond/changelog-gen/commit/::commit_hash::"
```

#### `version_string =`
  _**[optional]**_<br />
  **default**: `v{new_version}`

  Format for the version tag, this will be passed into changelog, commit
  messages, and any post processing.

  Example:

```toml
[tool.changelog_gen]
version_string = "{new_version}"
```

#### `date_format =`
  _**[optional]**_<br />
  **default**: None

  Add a date on the version line, use [strftime and strptime format
  codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).
  The format string can include any character, a space is included between the
  version tag and the date tag.

  When using in `setup.cfg` be sure to protect the `%` signs by using `%%` and
  be mindful about spacing as the string is taken straight from the `=` sign.

  Also available as `--date-format` (e.g. `--date-format '%Y-%m-%d'`).

  Example:

```toml
[tool.changelog_gen]
date_format = "on %Y-%m-%d"
```

#### `allowed_branches =`
  _**[optional]**_<br />
  **default**: None

  Prevent changelog being generated if the current branch is not in the
  supplied list. By default all branches are allowed.

  Example:

```toml
[tool.changelog_gen]
allowed_branches = [
  "master",
  "develop",
]
```

#### `commit_types = `
  _**[optional]**_<br />
  **default**: { <br />
      "feat": { <br />
        "header": "Features and Improvements", <br />
        "semver": "minor",
      }<br />
      "fix": {<br />
        "header": "Bug fixes", <br />
        "semver": "patch",<br />
      },<br />
      "docs": {<br />
        "header": "Documentation", <br />
        "semver": "patch",<br />
      },<br />
      "bug": {<br />
        "header": "Bug fixes", <br />
        "semver": "patch",<br />
      },<br />
      "chore": {<br />
        "header": "Miscellaneous", <br />
        "semver": "patch",<br />
      },<br />
      "ci": {<br />
        "header": "Miscellaneous", <br />
        "semver": "patch",<br />
      },<br />
      "perf": {<br />
        "header": "Miscellaneous", <br />
        "semver": "patch",<br />
      },<br />
      "refactor": {<br />
        "header": "Miscellaneous", <br />
        "semver": "patch",<br />
      },<br />
      "revert": {<br />
        "header": "Miscellaneous", <br />
        "semver": "patch",<br />
      },<br />
      "style": {<br />
        "header": "Miscellaneous", <br />
        "semver": "patch",<br />
      },<br />
      "test": {<br />
        "header": "Miscellaneous", <br />
        "semver": "patch",<br />
      },<br />
  }

  Define commit types and which headers and semver in the changelog they should map to, default semver is `patch`.

  Example:

```toml
[tool.changelog_gen.commit_types]
feat.header = "New Features"
feat.semver = "minor"
change.header = "Changes"
remove.header = "Removals"
remove.semver = "minor"
fix.header = "Bugfixes"
```

#### `sections =`
  _**[Deprecated]**_<br />
  _**[optional]**_<br />
  **default**: { <br />
      "feat": "Features and Improvements", <br />
      "fix": "Bug fixes", <br />
      "docs": "Documentation", <br />
      "misc": "Miscellaneous", <br />
  }

  Define custom headers or new sections/headers, new sections will require a
  matching section_mapping configuration.

  This configuration has been deprecated, use `commit_types` instead.

  Example:

```toml
[tool.changelog_gen.sections]
feat = "New Features"
change = "Changes"
remove = "Removals"
fix = "Bugfixes"
```

#### `section_mapping =`
  _**[Deprecated]**_<br />
  _**[optional]**_<br />
  **default**: { <br />
      "bug": "fix", <br />
      "chore": "misc", <br />
      "ci": "misc", <br />
      "docs": "docs", <br />
      "perf": "misc", <br />
      "refactor": "misc", <br />
      "revert": "misc", <br />
      "style": "misc", <br />
      "test": "misc", <br />
  }

  Configure additional supported commit types to supported changelog sections.

  This configuration has been deprecated, use `commit_types` instead.

  Example:

```toml
[tool.changelog_gen.section_mapping]
test = "fix"
bugfix = "fix"
docs = "fix"
new = "feat"
```

#### `post_process =`
  _**[optional]**_<br />
  **default**: None

  Configure a REST API to contact when a release is made

  See example on Jira configuration information.

 `.url =`<br />
  _**[required]**_<br />
  **default**: None<br />
  The url to contact.
  Can have the placeholders `::issue_ref::` and `::version::``.

  `.verb =`<br />
  _**[optional]**_<br />
  **default**: POST<br />
  HTTP method to use.

  `.body =`<br />
  _**[optional]**_<br />
  **default**: `{"body": "Released on ::version::"}`<br />
  The text to send to the API.
  Can have the placeholders `::issue_ref::` and `::version::`.

  `.headers =`<br />
  _**[optional]**_<br />
  **default**: None<br />
  Headers dictionary to inject into http requests.

  If using setup.cfg, provide a json string representation of the headers.

  `.auth_type =`<br />
  _**[optional]**_<br />
  **default**: basic<br />
  Auth type to use for post process requests, supported options are `basic` and `bearer`.

  `.auth_env =`<br />
  _**[optional]**_<br />
  **default**: None<br />
  Name of the environment variable to use to extract the basic auth information to contact the API.

  * For basic auth the content of the variable should be `{user}:{api key}`.
  * For bearer auth the content of the variable should be `{api key}`.

  Example to post to JIRA:

```toml
[tool.changelog_gen.post_process]
url = "https://your-domain.atlassian.net/rest/api/2/issue/ISSUE-::issue_ref::/comment"
verb = "POST"
body = '{"body": "Released on ::version::"}'
auth_env = "JIRA_AUTH"
headers."content-type" = "application/json"
```
  This assumes an environment variable `JIRA_AUTH` with the content `user@domain.com:{api_key}`.
  See
  [manage-api-tokens-for-your-atlassian-account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
  to generate a key.

  Also partially available as `--post-process-url` and `--post-process-auth-env` (e.g. `changelog generate --post-process-url 'http://my-api-url.domain/comment/::issue_ref::' --post-process-auth-env MY_API_AUTH`)

### Pre-release flows

If your versioning uses prerelease version parts, after a major/minor/patch update creates e.g. `v0.0.1rc0`, use
`--version-part=<part>` to trigger release flows, based on your configuration.

```bash
$ changelog generate --version-part build
... v0.0.1rc1
```

## Contributing

This project uses pre-commit hooks, please run `pre-commit install` after
cloning and installing dev dependencies.
