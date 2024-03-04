from __future__ import annotations

import importlib.metadata
import json
import logging
import logging.config
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from warnings import warn

import click
import rtoml
import typer
from rich.logging import RichHandler

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

logger = logging.getLogger(__name__)

VERBOSITY = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


def setup_logging(verbose: int = 0) -> None:
    """Configure the logging."""
    logging.basicConfig(
        level=VERBOSITY.get(verbose, logging.DEBUG),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_level=False,
                show_path=False,
                show_time=False,
                tracebacks_suppress=[click],
            ),
        ],
    )
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.disabled = True
    root_logger = logging.getLogger("")
    root_logger.setLevel(VERBOSITY.get(verbose, logging.DEBUG))


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
        logger.error("Working directory is not clean. Use `allow_dirty` configuration to ignore.")
        raise typer.Exit(code=1)

    allowed_branches = cfg.allowed_branches
    if allowed_branches and info["branch"] not in allowed_branches:
        logger.error("Current branch not in allowed generation branches.")
        raise typer.Exit(code=1)


@init_app.command("changelog-init")
@app.command("init")
def init(
    ctx: typer.Context,
    file_format: writer.Extension = typer.Option("md", help="File format to generate."),
    verbose: int = typer.Option(0, "-v", "--verbose", help="Set output verbosity.", count=True, max=3),
) -> None:
    """Generate an empty CHANGELOG file.

    Detect and raise if a CHANGELOG already exists, if not create a new file.
    """
    if ctx.command.name == "changelog-init":
        warn(
            "`changelog-init` has been deprecated, please use `changelog init`",
            FutureWarning,
            stacklevel=2,
        )
    setup_logging(verbose)
    cfg = config.Config()
    extension = util.detect_extension()
    if extension is not None:
        logger.error("CHANGELOG.%s detected.", extension.value)
        raise typer.Exit(code=1)

    w = writer.new_writer(file_format, cfg)
    w.write()


@app.command("migrate")
def migrate(
    verbose: int = typer.Option(0, "-v", "--verbose", help="Set output verbosity.", count=True, max=3),
) -> None:
    """Generate toml configuration from setup.cfg."""
    setup_logging(verbose)
    setup = Path("setup.cfg")

    if not setup.exists():
        logger.error("setup.cfg not found.")
        raise typer.Exit(code=1)

    cfg = config._process_setup_cfg(setup)  # noqa: SLF001
    config.check_deprecations(cfg)
    if "post_process" in cfg and "headers" in cfg["post_process"]:
        cfg["post_process"]["headers"] = json.loads(cfg["post_process"]["headers"])
    typer.echo(rtoml.dumps({"tool": {"changelog_gen": cfg}}))


@gen_app.command("changelog-gen")
@app.command("generate")
def gen(  # noqa: PLR0913
    ctx: typer.Context,
    version_tag: Optional[str] = typer.Option(None, help="Provide the desired version tag, skip auto generation."),
    version_part: Optional[str] = typer.Option(None, help="Provide the desired version part, skip auto generation."),
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
    verbose: int = typer.Option(0, "-v", "--verbose", help="Set output verbosity.", count=True, max=3),
    _version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        help="Print version and exit.",
    ),
) -> None:
    """Generate changelog entries.

    Read release notes and generate a new CHANGELOG entry for the current version.
    """
    if ctx.command.name == "changelog-gen":
        warn(
            "`changelog-gen` has been deprecated, please use `changelog generate`",
            FutureWarning,
            stacklevel=2,
        )
    setup_logging(verbose)
    cfg = config.read(
        release=release,
        allow_dirty=allow_dirty,
        commit=commit,
        reject_empty=reject_empty,
        date_format=date_format,
        post_process_url=post_process_url,
        post_process_auth_env=post_process_auth_env,
        verbose=verbose,
    )

    try:
        _gen(cfg, version_part, version_tag, dry_run=dry_run)
    except errors.ChangelogException as ex:
        logger.error("%s", ex)  # noqa: TRY400
        raise typer.Exit(code=1) from ex


def _gen(
    cfg: config.Config,
    version_part: str | None = None,
    version_tag: str | None = None,
    *,
    dry_run: bool = False,
) -> None:
    bv = BumpVersion(verbose=cfg.verbose, dry_run=dry_run)
    git = Git(dry_run=dry_run)

    extension = util.detect_extension()

    if extension is None:
        logger.error("No CHANGELOG file detected, run `changelog init`")
        raise typer.Exit(code=1)

    process_info(git.get_current_info(), cfg, dry_run=dry_run)

    version_info_ = bv.get_version_info("patch")
    e = extractor.ReleaseNoteExtractor(cfg=cfg, git=git, dry_run=dry_run)
    sections = e.extract(version_info_["current"])

    unique_issues = e.unique_issues(sections)
    if not unique_issues and cfg.reject_empty:
        logger.error("No changes present and reject_empty configured.")
        raise typer.Exit(code=0)

    if version_part is not None:
        version_info_ = bv.get_version_info(version_part)
        version_tag = version_info_["new"]

    if version_tag is None:
        version_tag = extract_version_tag(sections, cfg, bv)

    version_string = cfg.version_string.format(new_version=version_tag)

    date_fmt = cfg.date_format
    if date_fmt:
        version_string += f" {datetime.now(timezone.utc).strftime(date_fmt)}"

    w = writer.new_writer(extension, cfg, dry_run=dry_run)

    w.add_version(version_string)
    w.consume(cfg.type_headers, sections)

    logger.error(str(w))

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
    bv = BumpVersion(verbose=cfg.verbose, dry_run=dry_run, allow_dirty=cfg.allow_dirty)
    git = Git(dry_run=dry_run, commit=cfg.commit)

    if dry_run or typer.confirm(
        f"Write CHANGELOG for suggested version {version_tag}",
    ):
        writer.write()
        extractor.clean()

        paths = [f"CHANGELOG.{extension.value}"]
        if Path("release_notes").exists():
            paths.append("release_notes")
        git.commit(version_tag, paths)

        if cfg.commit and cfg.release:
            try:
                bv.release(version_tag)
            except Exception as e:  # noqa: BLE001
                git.revert()
                logger.error("Error creating release: %s", str(e))  # noqa: TRY400
                raise typer.Exit(code=1) from e
        return True

    return False
