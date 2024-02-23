from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

import typer

import changelog_gen
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

# TODO(edgy): use config to support reading from files, or from commits
# TODO(edgy): support ConventionalCommits instead of reading from files?


SUPPORTED_SECTIONS = {
    "feat": "Features and Improvements",
    "fix": "Bug fixes",
}


def _version_callback(*, value: bool) -> None:
    """Get current cli version."""
    if value:
        typer.echo(f"changelog {changelog_gen.__version__}")
        raise typer.Exit


def _callback(
    _version: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        callback=_version_callback,
        help="Print version and exit.",
    ),
) -> None: ...


app = typer.Typer(name="changelog", callback=_callback)
init_app = typer.Typer(name="init")
gen_app = typer.Typer(name="generate")


def process_info(info: dict, config: dict, *, dry_run: bool) -> None:
    if dry_run:
        return

    if info["dirty"] and not config.get("allow_dirty", False):
        typer.echo("Working directory is not clean. Use `allow_dirty` configuration to ignore.")
        raise typer.Exit(code=1)

    allowed_branches = config.get("allowed_branches")
    if allowed_branches and info["branch"] not in allowed_branches:
        typer.echo("Current branch not in allowed generation branches.")
        raise typer.Exit(code=1)


@init_app.command("init")
@app.command("init")
def init(
    file_format: writer.Extension = typer.Option("md", help="File format to generate."),
    _version: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        callback=_version_callback,
        help="Print version and exit.",
    ),
) -> None:
    """Generate an empty CHANGELOG file.

    Detect and raise if a CHANGELOG already exists, if not create a new file.
    """
    extension = util.detect_extension()
    if extension is not None:
        typer.echo(f"CHANGELOG.{extension.value} detected.")
        raise typer.Exit(code=1)

    w = writer.new_writer(file_format)
    w.write()


@gen_app.command("generate")
@app.command("generate")
def gen(  # noqa: PLR0913
    version_tag: Optional[str] = typer.Option(None, help="Provide the desired version tag, skip auto generation."),
    post_process_url: Optional[str] = typer.Option(
        None,
        help="Rest API endpoint to post release version notifications to.",
    ),
    post_process_auth_env: Optional[str] = typer.Option(
        None,
        help="Name of the ENV variable that contains the rest API basic auth content.",
    ),
    date_format: Optional[str] = typer.Option(None, help="The date format for strftime - empty string allowed."),
    *,
    dry_run: bool = typer.Option(False, help="Don't write release notes, check for errors."),  # noqa: FBT003
    allow_dirty: bool = typer.Option(False, help="Don't abort if branch contains uncommitted changes."),  # noqa: FBT003
    release: bool = typer.Option(False, help="Use bumpversion to tag the release."),  # noqa: FBT003
    commit: bool = typer.Option(False, help="Commit changes made to changelog after writing."),  # noqa: FBT003
    _version: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        callback=_version_callback,
        help="Print version and exit.",
    ),
) -> None:
    """Generate changelog entries.

    Read release notes and generate a new CHANGELOG entry for the current version."""
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
        _gen(config, version_tag, dry_run=dry_run)
    except errors.ChangelogException as ex:
        typer.echo(ex)
        raise typer.Exit(code=1) from ex


def _gen(config: dict[str, Any], version_tag: str | None = None, *, dry_run: bool = False) -> None:
    extension = util.detect_extension()

    if extension is None:
        typer.echo("No CHANGELOG file detected, run `changelog init`")
        raise typer.Exit(code=1)

    process_info(Git.get_latest_tag_info(), config, dry_run=dry_run)

    # TODO(edgy): supported default extensions (steal from conventional commits)
    # TODO(edgy): support multiple extras by default (the usuals)
    section_mapping = config.get("section_mapping", {})
    supported_sections = config.get("sections", SUPPORTED_SECTIONS)

    e = extractor.ReleaseNoteExtractor(dry_run=dry_run, supported_sections=supported_sections)
    sections = e.extract(section_mapping)

    if version_tag is None:
        version_tag = extract_version_tag(sections)

    # TODO(edgy): take a note from bumpversion, read in versioning format string
    version_string = f"v{version_tag}"

    date_fmt = config.get("date_format")
    if date_fmt:
        version_string += f" {datetime.now(UTC).strftime(date_fmt)}"

    w = writer.new_writer(extension, dry_run=dry_run, issue_link=config.get("issue_link"))

    w.add_version(version_string)
    w.consume(supported_sections, sections)

    typer.echo(w)

    _finalise(w, e, version_tag, extension, config, dry_run=dry_run)

    post_process = config.get("post_process")
    if post_process:
        unique_issues = e.unique_issues(sections)
        per_issue_post_process(post_process, sorted(unique_issues), version_tag, dry_run=dry_run)


def _finalise(  # noqa: PLR0913
    writer: writer.BaseWriter,
    extractor: extractor.ReleaseNoteExtractor,
    version_tag: str,
    extension: writer.Extension,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> None:
    if dry_run or typer.confirm(
        f"Write CHANGELOG for suggested version {version_tag}",
    ):
        writer.write()
        extractor.clean()

        if dry_run or not config["commit"]:
            return

        Git.add_path(f"CHANGELOG.{extension.value}")
        # TODO(edgy): Dont add release notes if using commit messages...
        Git.add_path("release_notes")
        Git.commit(version_tag)

        if config["release"]:
            BumpVersion.release(version_tag)
