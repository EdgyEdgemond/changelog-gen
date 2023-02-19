# Changelog Generator - v0.8.1
[![image](https://img.shields.io/pypi/v/changelog_gen.svg)](https://pypi.org/project/changelog_gen/)
[![image](https://img.shields.io/pypi/l/changelog_gen.svg)](https://pypi.org/project/changelog_gen/)
[![image](https://img.shields.io/pypi/pyversions/changelog_gen.svg)](https://pypi.org/project/changelog_gen/)
![style](https://github.com/EdgyEdgemond/changelog-gen/workflows/style/badge.svg)
![tests](https://github.com/EdgyEdgemond/changelog-gen/workflows/tests/badge.svg)
[![codecov](https://codecov.io/gh/EdgyEdgemond/changelog-gen/branch/master/graph/badge.svg)](https://codecov.io/gh/EdgyEdgemond/changelog-gen)

`changelog-gen` is a CHANGELOG generator intended to be used in conjunction
with [bumpversion](https://github.com/c4urself/bump2version) to generate
changelogs and create release tags.

## Installation

```bash
pip install changelog-gen
```

or clone this repo and install with poetry.

```bash
poetry install
```

## Usage

`changelog-gen` currently only supports reading changes from a `release_notes` folder.

Files in the folder should use the format `{issue_number}.{type}`.

By default supported types are currently `fix` and `feat`. Additional types can be configured
to map to these initial types.

The contents of each file is used to populate the changelog file. If the type
ends with a `!` it denotes a breaking change has been made, this will lead to a
major release being suggested.

```bash
$ ls release_notes
  4.fix  7.fix

$ changelog-gen

## v0.2.1

### Bug fixes

- Raise errors from internal classes, don't use click.echo() [#4]
- Update changelog line format to include issue number at the end. [#7]

Write CHANGELOG for suggested version 0.2.1 [y/N]: y
```

## Configuration

Of the command line arguments, most of them can be configured in `setup.cfg` to remove
the need to pass them in every time.

Example `setup.cfg`:

```ini
[changelog_gen]
commit = true
release = true
allow_dirty = false
```

### Configuration file -- Global configuration

General configuration is grouped in a `[changelog_gen]` section.

#### `commit = (True | False)`
  _**[optional]**_<br />
  **default**: False

  Commit changes to the changelog after writing.

  Also available as `--commit` (e.g. `changelog-gen --commit`)

#### `release = (True | False)`
  _**[optional]**_<br />
  **default**: False

  Use bumpversion to tag the release

  Also available as `--release` (e.g. `changelog-gen --release`)

#### `allow_dirty = (True | False)`
  _**[optional]**_<br />
  **default**: False

  Don't abort if the current branch contains uncommitted changes

  Also available as `--allow-dirty` (e.g. `changelog-gen --allow-dirty`)

#### `issue_link =`
  _**[optional]**_<br />
  **default**: None

  Create links in the CHANGELOG to the originating issue. A url that contains an
  `{issue_ref}` for formatting.

  Example:

```ini
[changelog_gen]
issue_link = http://github.com/EdgyEdgemond/changelog-gen/issues/{issue_ref}
```

#### `date_format =`
  _**[optional]**_<br />
  **default**: None

  Add a date on the version line, use [strftime and strptime format codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).
  The format string can include any character, a space is included between the version tag and the date tag.

  When using in `setup.cfg` be sure to protect the `%` signs (see example below) and be mindful about spacing as the string is taken straight from the `=` sign.

  Also available as `--date-format` (e.g. `--date-format '%Y-%m-%d'`).

  Example:

```ini
[changelog_gen]
date_format =on %%Y-%m-%d
```


#### `allowed_branches =`
  _**[optional]**_<br />
  **default**: None

  Prevent changelog being generated if the current branch is not in the supplied list. By
  default all branches are allowed.

  Example:

```ini
[changelog_gen]
allowed_branches =
  master
  develop
```

#### `sections =`
  _**[optional]**_<br />
  **default**: None

  Define custom headers or new sections/headers, new sections will require a matching
  section_mapping configuration.

  Example:

```ini
[changelog_gen]
sections =
  feat=New Features
  change=Changes
  remove=Removals
  fix=Bugfixes
```

#### `section_mapping =`
  _**[optional]**_<br />
  **default**: None

  Configure additional supported release_note extensions to supported changelog
  sections.

  Example:

```ini
[changelog_gen]
section_mapping =
  test=fix
  bugfix=fix
  docs=fix
  new=feat
```

#### `post_process =`
  _**[optional]**_<br />
  **default**: None

  Configure a REST API to contact when a release is made

  See example on Jira configuration information.

 `.url=`<br />
  _**[required]**_<br />
  **default**: None<br />
  The url to contact.
  Can have the variables `{issue_ref}` and `{new_version}`.

  `.verb=`<br />
  _**[optional]**_<br />
  **default**: POST<br />
  HTTP method to use.

  `.body=`<br />
  _**[optional]**_<br />
  **default**: `{{"body": "Released on v{new_version}"}}`<br />
  The text to send to the API.
  Can have the variables `{issue_ref}` and `{new_version}`.

  `.auth_env =`<br />
  _**[optional]**_<br />
  **default**: None<br />
  Name of the environment variable to use to extract the basic auth information to contact the API.
  The content of the variable should be `{user}:{api key}`.

  Example to post to JIRA:

```ini
[changelog_gen]
post_process =
  url=https://your-domain.atlassian.net/rest/api/2/issue/ISSUE-{issue_ref}/comment
  verb=POST
  body={{"body": "Released on v{new_version}"}}
  auth_env=JIRA_AUTH
```
  This assumes an environment variable `JIRA_AUTH` with the content `user@domain.com:{api_key}`.
  See [manage-api-tokens-for-your-atlassian-account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) to generate a key.

  Note: spaces around `=` will not be stripped, be sure to use `<field>=<value>`.

  Also partially available as `--post-process-url` and `--post-process-auth-env` (e.g. `changelog-gen --post-process-url 'http://my-api-url.domain/comment{issue_ref}' --post-process-auth-env MY_API_AUTH`)

## Contributing

This project uses pre-commit hooks, please run `pre-commit install` after cloning and installing dev dependencies.
