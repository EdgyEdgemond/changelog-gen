# Changelog Generator - v0.2.2

`changelog-gen` is a CHANGELOG generator intended to be used in conjunction with `bumpversion`
to generate changelogs and create release tags.

## Installation

```bash
pip install changelog-gen
```

or clone this repo and install with poetry, currently depends on poetry < 1.0.0
due to other personal projects being stuck.

```bash
poetry install
```

## Usage

`changelog-gen` currently only supports reading changes from a `release_notes` folder.

Files in the folder should use the format `{issue_number}.{type}`, supported
types are currently `fix` and `feat`. The contents of the file is used to populate
the changelog file.

```bash
$ changelog-gen

## v0.2.2

### Bug fixes

- Raise errors from internal classes, don't use click.echo() [#4]
- Update changelog line format to include issue number at the end. [#7]

Write CHANGELOG for suggested version 0.2.2 [y/N]: y
```
