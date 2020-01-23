# Changelog Generator - v0.3.0

`changelog-gen` is a CHANGELOG generator intended to be used in conjunction
with [bumpversion](https://github.com/c4urself/bump2version) to generate
changelogs and create release tags.

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
the changelog file. If the type ends with a `!` it denotes a breaking change has been
made, this will lead to a major release being suggested.

```bash
$ changelog-gen

## v0.3.0

### Bug fixes

- Raise errors from internal classes, don't use click.echo() [#4]
- Update changelog line format to include issue number at the end. [#7]

Write CHANGELOG for suggested version 0.3.0 [y/N]: y
```
