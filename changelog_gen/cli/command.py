from datetime import datetime
from typing import (
    Any,
    Dict,
)

import click

from changelog_gen import (
    errors,
    extractor,
    writer,
)
from changelog_gen.cli import util
from changelog_gen.config import (
    Config,
    PostProcessConfig,
)
from changelog_gen.extractor import extract_version_tag
from changelog_gen.post_processor import per_issue_post_process
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
@click.option("--post-process-auth-env", default=None,
              help="Name of the ENV variable that contains the rest API basic auth content")
@click.option("--post-process-url", default=None, help="Rest API endpoint to post release version for each issue")
@click.option("--version-tag", default=None, help="Provide the desired version tag, skip auto generation.")
@click.option("--release/--no-release", help="Use bumpversion to tag the release")
@click.option("--dry-run", is_flag=True, help="Don't write release notes to check for errors")
@click.option("--allow-dirty/--no-allow-dirty", help="Don't abort if branch contains uncommited changes")
@click.option("--commit/--no-commit", help="Commit changes made to changelog after writing")
@click.option("--date-format", default=None, help="The date format for strftime - empty string allowed")
@click.command("changelog-gen", help="Generate a change log from release_notes/* files")
def gen(
    dry_run=False,
    allow_dirty=False,
    release=False,
    commit=False,
    version_tag=None,
    post_process_url=None,
    post_process_auth_env=None,
    date_format=None,
):
    """
    Read release notes and generate a new CHANGELOG entry for the current version.
    """
    config = Config().read()

    config["release"] = config.get("release") or release
    config["allow_dirty"] = config.get("allow_dirty") or allow_dirty
    config["commit"] = config.get("commit") or commit
    if date_format is not None:
        config["date_format"] = date_format

    post_process: PostProcessConfig = config.get("post_process")
    if not post_process:
        # Only overload config on change in case it wasn't present
        post_process = PostProcessConfig()
    if post_process_url:
        post_process.url = post_process_url
        config["post_process"] = post_process
    if post_process_auth_env:
        post_process.auth_env = post_process_auth_env
        config["post_process"] = post_process

    try:
        _gen(config, dry_run, version_tag)
    except errors.ChangelogException as ex:
        click.echo(ex)
        raise click.Abort()


def _gen(config: Dict[str, Any], dry_run=False, version_tag=None):
    extension = util.detect_extension()

    if extension is None:
        click.echo("No CHANGELOG file detected, run changelog-init")
        raise click.Abort()

    process_info(Git.get_latest_tag_info(), dry_run, config["allow_dirty"], config)

    # TODO: supported default extensions (steal from conventional commits)
    # TODO: support multiple extras by default (the usuals)
    section_mapping = config.get("section_mapping", {})
    supported_sections = config.get("sections", SUPPORTED_SECTIONS)

    e = extractor.ReleaseNoteExtractor(dry_run=dry_run, supported_sections=supported_sections)
    sections = e.extract(section_mapping)

    if version_tag is None:
        version_tag = extract_version_tag(sections)

    # TODO: take a note from bumpversion, read in versioning format string
    version_string = f"v{version_tag}"

    date_fmt = config.get("date_format")
    if date_fmt:
        version_string += f" {datetime.now().strftime(date_fmt)}"

    w = writer.new_writer(extension, dry_run=dry_run, issue_link=config.get("issue_link"))

    w.add_version(version_string)
    w.consume(supported_sections, sections)

    click.echo(w)

    _finalise(w, e, version_tag, extension, dry_run, config)

    post_process = config.get("post_process")
    if post_process:
        unique_issues = e.unique_issues(sections)
        per_issue_post_process(post_process, sorted(unique_issues), version_tag, dry_run=dry_run)


def _finalise(
    writer: writer.BaseWriter,
    extractor: extractor.ReleaseNoteExtractor,
    version_tag: str,
    extension: str,
    dry_run: bool,
    config: Dict[str, Any],
):
    if dry_run or click.confirm(
        "Write CHANGELOG for suggested version {}".format(version_tag),
    ):
        writer.write()
        extractor.clean()

        if dry_run or not config["commit"]:
            return

        Git.add_path("CHANGELOG.{extension}".format(extension=extension))
        # TODO: Dont add release notes if using commit messages...
        Git.add_path("release_notes")
        Git.commit(version_tag)

        if config["release"]:
            BumpVersion.release(version_tag)
