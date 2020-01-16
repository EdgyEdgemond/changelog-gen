import subprocess
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

import click

from changelog_gen.cli import util
from changelog_gen import writer


# Create a public repo on pypi?

# TODO: changelog-init --ff=md|rst create base file.
# TODO: changelog-gen rename command
# TODO: FileGenerator classes for .md and .rst
# TODO: use config to support reading from files, or from commits
# TODO: support ConventionalCommits instead of reading from files?
# setup.cfg or pyproject.toml
# https://github.com/c4urself/bump2version/blob/master/bumpversion/cli.py _determine_config_file
# TODO: DetailsExtraction if release_notes, file format, if commit messages, main commit message

# TODO: Don't use fstrings that limits python version


@util.common_options
@click.option('--file-format', type=str, default='md', help='File format to generate')
@click.command('changelog-init', help='Generate an empty CHANGELOG file')
def init(file_format):
    """
    Create a new CHANGELOG file.

    Detect and raise if a CHANGELOG already exists, if not create a new file.
    """
    extension = util.detect_extension()
    if extension is not None:
        click.echo(f'CHANGELOG.{extension} detected.')
        raise click.Abort()

    w = writer.new_writer(file_format)
    w.write()



@util.common_options
@click.option('--dry-run', is_flag=True, help="Don't write release notes to check for errors")
@click.command('changelog-gen', help='Generate a change log from release_notes/* files')
def gen(dry_run=False):
    """
    Read release notes and generate a new CHANGELOG entry for the current version.
    """

    extension = util.detect_extension()

    if extension is None:
        click.echo('No CHANGELOG file detected, run changelog-init')
        raise click.Abort()

    release_notes = Path('./release_notes')

    if not release_notes.exists() or not release_notes.is_dir:
        click.echo('No release notes directory found.')
        raise click.Abort()

    supported_sections = {
        'feature': 'Features and Improvements',
        'bugfix': 'Bug fixes',
    }

    # TODO: check git is ready for making changes (not dirty)

    # TODO: supported default extensions (steal from conventional commits)
    # TODO: support multiple extras by default (the usuals)
    # TODO: Read in additional extensions to headings or overrides for custom headings
    sections = defaultdict(dict)

    # Extract changelog details from release note files.
    for issue in release_notes.iterdir():
        if issue.is_file and not issue.name.startswith('.'):
            ticket, section = issue.name.split('.')
            contents = issue.read_text().strip()
            if section not in supported_sections:
                click.echo(f'Unsupported CHANGELOG section {section}')
                raise click.Abort()

            sections[section][ticket] = contents

    w = writer.new_writer(extension, dry_run=dry_run)

    cmd = ['git' 'describe', '--tags', '--match', '[0-9]*']
    try:
        version = subprocess.check_output(cmd).decode().strip()
    except subprocess.CalledProcessError:
        click.echo('Unable to get version number from git tags')
        raise click.Abort

    print(version)
    # TODO: extract version from git.
    # TODO: take a note from bumpversion, read in versioning format string
    version = 'v0.0.2'

    w.add_version(version)

    for section in supported_sections:
        if section not in sections:
            continue

        header = supported_sections[section]
        lines = [
            '{}: {}\n'.format(ticket, content)
            for ticket, content in sections[section].items()
        ]
        w.add_section(header, lines)

    w.write()
    if not dry_run:
        for x in release_notes.iterdir():
            if x.is_file and not x.name.startswith('.'):
                x.unlink()

        # TODO: Commit changes and retag (detect from config)
