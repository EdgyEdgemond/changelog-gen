from __future__ import annotations

import importlib.metadata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from changelog_gen import (
    config,
    errors,
    extractor,
    writer,
)
from changelog_gen.cli import util
from changelog_gen.extractor import extract_version_tag
from changelog_gen.post_processor import per_issue_post_process
from changelog_gen.vcs import Git
from changelog_gen.version import BumpVersion


def _version_callback(*, value: bool) -> None:
    """Get current cli version."""
    if value:
        version = importlib.metadata.version("changelog-gen")
        typer.echo(f"changelog {version}")
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


def process_info(info: dict, cfg: config.Config, *, dry_run: bool) -> None:
    """Process git info and raise on invalid state."""
    if dry_run:
        return

    if info["dirty"] and not cfg.allow_dirty:
        typer.echo("Working directory is not clean. Use `allow_dirty` configuration to ignore.")
        raise typer.Exit(code=1)

    allowed_branches = cfg.allowed_branches
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
    allow_dirty: Optional[bool] = typer.Option(None, help="Don't abort if branch contains uncommitted changes."),
    release: Optional[bool] = typer.Option(None, help="Use bumpversion to tag the release."),
    commit: Optional[bool] = typer.Option(None, help="Commit changes made to changelog after writing."),
    reject_empty: Optional[bool] = typer.Option(None, help="Don't accept changes if there are no release notes."),
    _version: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        callback=_version_callback,
        help="Print version and exit.",
    ),
) -> None:
    """Generate changelog entries.

    Read release notes and generate a new CHANGELOG entry for the current version.
    """
    cfg = config.read(
        release=release,
        allow_dirty=allow_dirty,
        commit=commit,
        reject_empty=reject_empty,
        date_format=date_format,
        post_process_url=post_process_url,
        post_process_auth_env=post_process_auth_env,
    )

    try:
        _gen(cfg, version_tag, dry_run=dry_run)
    except errors.ChangelogException as ex:
        typer.echo(ex)
        raise typer.Exit(code=1) from ex


def _gen(cfg: config.Config, version_tag: str | None = None, *, dry_run: bool = False) -> None:
    extension = util.detect_extension()

    if extension is None:
        typer.echo("No CHANGELOG file detected, run `changelog init`")
        raise typer.Exit(code=1)

    process_info(Git.get_latest_tag_info(), cfg, dry_run=dry_run)

    e = extractor.ReleaseNoteExtractor(dry_run=dry_run, type_headers=cfg.type_headers)
    sections = e.extract()

    unique_issues = e.unique_issues(sections)
    if not unique_issues and cfg.reject_empty:
        typer.echo("No changes present and reject_empty configured.")
        raise typer.Exit(code=0)

    if version_tag is None:
        version_tag = extract_version_tag(sections, cfg.semver_mapping)

    version_string = cfg.version_string.format(new_version=version_tag)

    date_fmt = cfg.date_format
    if date_fmt:
        version_string += f" {datetime.now(timezone.utc).strftime(date_fmt)}"

    w = writer.new_writer(extension, dry_run=dry_run, issue_link=cfg.issue_link, commit_link=cfg.commit_link)

    w.add_version(version_string)
    w.consume(cfg.type_headers, sections)

    typer.echo(w)

    processed = _finalise(w, e, version_tag, extension, cfg, dry_run=dry_run)

    post_process = cfg.post_process
    if post_process and processed:
        unique_issues = [r for r in unique_issues if not r.startswith("__")]
        per_issue_post_process(post_process, sorted(unique_issues), version_tag, dry_run=dry_run)


def _finalise(  # noqa: PLR0913
    writer: writer.BaseWriter,
    extractor: extractor.ReleaseNoteExtractor,
    version_tag: str,
    extension: writer.Extension,
    cfg: config.Config,
    *,
    dry_run: bool,
) -> bool:
    if dry_run or typer.confirm(
        f"Write CHANGELOG for suggested version {version_tag}",
    ):
        writer.write()
        extractor.clean()

        if dry_run or not cfg.commit:
            return False

        Git.add_path(f"CHANGELOG.{extension.value}")
        if Path("release_notes").exists():
            Git.add_path("release_notes")
        Git.commit(version_tag)

        if cfg.release:
            try:
                BumpVersion.release(version_tag)
            except Exception as e:  # noqa: BLE001
                Git.revert()
                typer.echo("Error creating release: {e}")
                raise typer.Exit(code=1) from e
        return True

    return False
