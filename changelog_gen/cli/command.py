import click

from changelog_gen import (
    errors,
    extractor,
    writer,
)
from changelog_gen.cli import util
from changelog_gen.vcs import Git
from changelog_gen.version import BumpVersion


# TODO: use config to support reading from files, or from commits
# TODO: support ConventionalCommits instead of reading from files?
# setup.cfg or pyproject.toml
# https://github.com/c4urself/bump2version/blob/master/bumpversion/cli.py _determine_config_file


def process_info(info, dry_run):
    if info["dirty"]:
        click.echo("Working directory is not clean.")
        raise click.Abort()

    if (
        not dry_run and
        info["distance_to_latest_tag"] != 0 and
        not click.confirm(
            "Changes made since release, continue generating CHANGELOG",
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
    "--dry-run", is_flag=True, help="Don't write release notes to check for errors",
)
@click.command("changelog-gen", help="Generate a change log from release_notes/* files")
def gen(dry_run=False):
    """
    Read release notes and generate a new CHANGELOG entry for the current version.
    """

    try:
        _gen(dry_run)
    except errors.ChangelogException as ex:
        click.echo(ex)
        raise click.Abort()


def _gen(dry_run=False):
    extension = util.detect_extension()

    if extension is None:
        click.echo("No CHANGELOG file detected, run changelog-init")
        raise click.Abort()

    # TODO: supported default extensions (steal from conventional commits)
    # TODO: support multiple extras by default (the usuals)
    # TODO: Read in additional extensions to headings or overrides for custom headings
    e = extractor.ReleaseNoteExtractor(dry_run=dry_run)
    sections = e.extract()

    # TODO: break could be a fix or a feat... Detect break some other way
    semver = (
        "major" if "break" in sections else "minor" if "feat" in sections else "patch"
    )
    version_info = BumpVersion.get_version_info(semver)

    # TODO: take a note from bumpversion, read in versioning format string
    version = "v{new_version}".format(new_version=version_info["new"])

    w = writer.new_writer(extension, dry_run=dry_run)

    w.add_version(version)

    for section in extractor.SUPPORTED_SECTIONS:
        if section not in sections:
            continue

        header = extractor.SUPPORTED_SECTIONS[section]
        lines = [
            "{} [#{}]".format(content, issue_number)
            for issue_number, content in sections[section].items()
        ]
        w.add_section(header, lines)

    click.echo(w)

    if dry_run or click.confirm(
        "Write CHANGELOG for suggested version {}".format(version_info["new"]),
    ):
        w.write()
        e.clean()

        if dry_run:
            return

        # TODO: Commit changes if configured
        Git.add_path("CHANGELOG.{extension}".format(extension=extension))
        # TODO: Dont add release notes if using commit messages...
        Git.add_path("release_notes")
        Git.commit(version_info["new"])

        # TODO: use bumpversion to tag if configured
        BumpVersion.release(semver)
