import click

from changelog_gen import (
    errors,
    extractor,
    writer,
)
from changelog_gen.cli import util
from changelog_gen.config import Config
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
@click.option("--version-tag", default=None, help="Provide the desired version tag, skip auto generation.")
@click.option("--release", is_flag=True, help="Use bumpversion to tag the release")
@click.option("--dry-run", is_flag=True, help="Don't write release notes to check for errors")
@click.command("changelog-gen", help="Generate a change log from release_notes/* files")
def gen(dry_run=False, release=False, version_tag=None):
    """
    Read release notes and generate a new CHANGELOG entry for the current version.
    """

    try:
        _gen(dry_run, release, version_tag)
    except errors.ChangelogException as ex:
        click.echo(ex)
        raise click.Abort()


def _gen(dry_run=False, release=False, version_tag=None):
    config = Config().read()

    release = config.get("release", release)

    extension = util.detect_extension()

    if extension is None:
        click.echo("No CHANGELOG file detected, run changelog-init")
        raise click.Abort()

    # TODO: supported default extensions (steal from conventional commits)
    # TODO: support multiple extras by default (the usuals)
    # TODO: Read in additional extensions to headings or overrides for custom headings
    e = extractor.ReleaseNoteExtractor(dry_run=dry_run)
    sections = e.extract()

    semver = None
    if version_tag is None:
        semver = "minor" if "feat" in sections else "patch"
        for section_issues in sections.values():
            for issue in section_issues.values():
                if issue["breaking"]:
                    semver = "major"
        version_info = BumpVersion.get_version_info(semver)

        version_tag = version_info["new"]

    # TODO: take a note from bumpversion, read in versioning format string
    version_string = "v{version_tag}".format(version_tag=version_tag)

    w = writer.new_writer(extension, dry_run=dry_run)

    w.add_version(version_string)

    for section in sorted(extractor.SUPPORTED_SECTIONS):
        if section not in sections:
            continue

        header = extractor.SUPPORTED_SECTIONS[section]
        lines = [
            "{} [#{}]".format(content["description"], issue_number)
            for issue_number, content in sections[section].items()
        ]
        w.add_section(header, lines)

    click.echo(w)

    _finalise(w, e, version_tag, extension, dry_run=dry_run, release=release)


def _finalise(writer, extractor, version_tag, extension, release=False, dry_run=False):
    if dry_run or click.confirm(
        "Write CHANGELOG for suggested version {}".format(version_tag),
    ):
        writer.write()
        extractor.clean()

        if dry_run:
            return

        # TODO: Commit changes if configured
        Git.add_path("CHANGELOG.{extension}".format(extension=extension))
        # TODO: Dont add release notes if using commit messages...
        Git.add_path("release_notes")
        Git.commit(version_tag)

        if release:
            # TODO: use bumpversion to tag if configured
            BumpVersion.release(version_tag)
