import subprocess
from pathlib import Path

import click

from changelog_gen import (
    extractor,
    writer,
)
from changelog_gen.cli import util
from changelog_gen.vcs import Git


# Create a public repo on pypi?

# TODO: use config to support reading from files, or from commits
# TODO: support ConventionalCommits instead of reading from files?
# setup.cfg or pyproject.toml
# https://github.com/c4urself/bump2version/blob/master/bumpversion/cli.py _determine_config_file


def process_info(info, dry_run):
    if info["dirty"]:
        click.echo("Working directory is not clean.")
        raise click.Abort()

    if (
        not dry_run
        and info["distance_to_latest_tag"] != 0
        and not click.confirm(
            "Changes made since release, continue generating CHANGELOG"
        )
    ):
        raise click.Abort()


@util.common_options
@click.option("--file-format", type=str, default="md", help="File format to generate")
@click.command("changelog-init", help="Generate an empty CHANGELOG file")
def init(file_format):
    """
    Create a new CHANGELOG file.

    Detect and raise if a CHANGELOG already exists, if not create a new file.
    """
    extension = util.detect_extension()
    if extension is not None:
        click.echo("CHANGELOG.{extension} detected.".format(extension=extension))
        raise click.Abort()

    w = writer.new_writer(file_format)
    w.write()


@util.common_options
@click.option(
    "--dry-run", is_flag=True, help="Don't write release notes to check for errors"
)
@click.command("changelog-gen", help="Generate a change log from release_notes/* files")
def gen(dry_run=False):
    """
    Read release notes and generate a new CHANGELOG entry for the current version.
    """

    extension = util.detect_extension()

    if extension is None:
        click.echo("No CHANGELOG file detected, run changelog-init")
        raise click.Abort()

    info = Git().get_latest_tag_info()
    process_info(info, dry_run)

    # TODO: take a note from bumpversion, read in versioning format string
    version = "v{current_version}".format(current_version=info["current_version"])

    # TODO: supported default extensions (steal from conventional commits)
    # TODO: support multiple extras by default (the usuals)
    # TODO: Read in additional extensions to headings or overrides for custom headings
    e = extractor.ReleaseNoteExtractor()
    sections = e.extract()

    w = writer.new_writer(extension, dry_run=dry_run)

    w.add_version(version)

    for section in extractor.SUPPORTED_SECTIONS:
        if section not in sections:
            continue

        header = extractor.SUPPORTED_SECTIONS[section]
        lines = [
            "{}: {}\n".format(ticket, content)
            for ticket, content in sections[section].items()
        ]
        w.add_section(header, lines)

    w.write()
    if not dry_run:
        e.clean()

        # TODO: Commit changes and retag (detect from config)
