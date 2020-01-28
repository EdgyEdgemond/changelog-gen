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


SUPPORTED_SECTIONS = {
    "feat": "Features and Improvements",
    "fix": "Bug fixes",
}


def process_info(info, dry_run, allow_dirty, config):
    if dry_run:
        return

    if info["dirty"] and not allow_dirty:
        click.echo("Working directory is not clean. Use `allow_dirty` configuration to ignore.")
        raise click.Abort()

    allowed_branches = config.get("allowed_branches")
    if allowed_branches and info["branch"] not in allowed_branches:
        click.echo("Current branch not in allowed generation branches.")
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
@click.option("--allow-dirty", is_flag=True, help="Don't abort if branch contains uncommited changes")
@click.option("--commit", is_flag=True, help="Commit changes made to changelog after writing")
@click.command("changelog-gen", help="Generate a change log from release_notes/* files")
def gen(dry_run=False, allow_dirty=False, release=False, commit=False, version_tag=None):
    """
    Read release notes and generate a new CHANGELOG entry for the current version.
    """

    try:
        _gen(dry_run, allow_dirty, release, commit, version_tag)
    except errors.ChangelogException as ex:
        click.echo(ex)
        raise click.Abort()


def _gen(dry_run=False, allow_dirty=False, release=False, commit=False, version_tag=None):
    config = Config().read()

    release = config.get("release") or release
    allow_dirty = config.get("allow_dirty") or allow_dirty
    commit = config.get("commit") or commit

    extension = util.detect_extension()

    if extension is None:
        click.echo("No CHANGELOG file detected, run changelog-init")
        raise click.Abort()

    process_info(Git.get_latest_tag_info(), dry_run, allow_dirty, config)

    # TODO: supported default extensions (steal from conventional commits)
    # TODO: support multiple extras by default (the usuals)
    section_mapping = config.get("section_mapping", {})
    supported_sections = config.get("sections", SUPPORTED_SECTIONS)

    e = extractor.ReleaseNoteExtractor(dry_run=dry_run, supported_sections=supported_sections)
    sections = e.extract(section_mapping)

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

    w = writer.new_writer(extension, dry_run=dry_run, issue_link=config.get("issue_link"))

    w.add_version(version_string)

    for section in sorted(e.supported_sections):
        if section not in sections:
            continue

        header = e.supported_sections[section]
        w.add_section(header, {k: v["description"] for k, v in sections[section].items()})

    click.echo(w)

    _finalise(w, e, version_tag, extension, dry_run=dry_run, release=release, commit=commit)


def _finalise(writer, extractor, version_tag, extension, release=False, dry_run=False, commit=False):
    if dry_run or click.confirm(
        "Write CHANGELOG for suggested version {}".format(version_tag),
    ):
        writer.write()
        extractor.clean()

        if dry_run or not commit:
            return

        Git.add_path("CHANGELOG.{extension}".format(extension=extension))
        # TODO: Dont add release notes if using commit messages...
        Git.add_path("release_notes")
        Git.commit(version_tag)

        if release:
            BumpVersion.release(version_tag)
