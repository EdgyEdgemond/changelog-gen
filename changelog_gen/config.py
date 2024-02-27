from __future__ import annotations

import contextlib
import dataclasses
import logging
from configparser import (
    ConfigParser,
    NoOptionError,
)
from pathlib import Path
from warnings import warn

import rtoml

logger = logging.getLogger(__name__)

SUPPORTED_SECTIONS = {
    "feat": "Features and Improvements",
    "fix": "Bug fixes",
}


@dataclasses.dataclass
class PostProcessConfig:
    """Post Processor configuration options."""

    url: str = ""
    verb: str = "POST"
    # The body to send as a post-processing command,
    # can have the entries: ::issue_ref::, ::version::
    body: str = '{"body": "Released on ::version::"}'
    # Name of an environment variable to use as HTTP Basic Auth parameters.
    # The variable should contain "{user}:{api_key}"
    auth_env: str | None = None


@dataclasses.dataclass
class Config:
    """Changelog configuration options."""

    issue_link: str | None = None
    date_format: str | None = None

    allowed_branches: list[str] = dataclasses.field(default_factory=list)
    section_mapping: dict = dataclasses.field(default_factory=dict)
    sections: dict = dataclasses.field(default_factory=lambda: SUPPORTED_SECTIONS)

    release: bool = False
    commit: bool = False
    allow_dirty: bool = False
    reject_empty: bool = False

    post_process: PostProcessConfig | None = None


def parse_dict_value(parser: ConfigParser, dictvaluename: str) -> dict | None:
    """Extract a dictionary from configuration."""
    try:
        value = parser.get("changelog_gen", dictvaluename)
    except NoOptionError:
        return None
    else:
        ret = {}
        dictvalue = list(
            filter(None, (x.strip() for x in value.splitlines())),
        )

        for value in dictvalue:
            k, v = value.split("=")
            ret[k.strip()] = v.strip()

        return ret


def parse_list_value(parser: ConfigParser, listvaluename: str) -> list | None:
    """Extract a dictionary from configuration."""
    try:
        value = parser.get("changelog_gen", listvaluename)
    except NoOptionError:
        return None
    else:
        ret = []
        listvalue = list(
            filter(None, (x.strip() for x in value.splitlines())),
        )

        for value in listvalue:
            ret.extend([v.strip() for v in value.split(",")])

        return ret


def parse_boolean_value(parser: ConfigParser, valuename: str) -> bool | None:
    """Extract a boolean from configuration."""
    with contextlib.suppress(NoOptionError):
        return parser.getboolean("changelog_gen", valuename)
    return None


def parse_string_value(parser: ConfigParser, valuename: str) -> str | None:
    """Extract a string from configuration."""
    with contextlib.suppress(NoOptionError):
        return parser.get("changelog_gen", valuename)
    return None


def _process_overrides(overrides: dict) -> tuple[dict, PostProcessConfig | None]:
    """Process provided overrides.

    Remove any unsupplied values (None).
    """
    post_process_url = overrides.pop("post_process_url", "")
    post_process_auth_env = overrides.pop("post_process_auth_env", None)

    post_process = None
    if post_process_url or post_process_auth_env:
        post_process = PostProcessConfig(
            url=post_process_url,
            auth_env=post_process_auth_env,
        )

    overrides = {k: v for k, v in overrides.items() if v is not None}

    return overrides, post_process


def _process_pyproject(pyproject: Path) -> dict:
    cfg = {}
    with pyproject.open() as f:
        data = rtoml.load(f)

        if "tool" not in data or "changelog_gen" not in data["tool"]:
            return cfg

        return data["tool"]["changelog_gen"]


def _process_setup_cfg(setup: Path) -> dict:
    cfg = {}
    parser = ConfigParser("")

    parser.add_section("changelog_gen")

    with setup.open(encoding="utf-8") as config_fp:
        config_content = config_fp.read()

    parser.read_string(config_content)

    for valuename, parse_func in [
        ("issue_link", parse_string_value),
        ("date_format", parse_string_value),
        ("allowed_branches", parse_list_value),
        ("section_mapping", parse_dict_value),
        ("sections", parse_dict_value),
        ("release", parse_boolean_value),
        ("commit", parse_boolean_value),
        ("allow_dirty", parse_boolean_value),
        ("reject_empty", parse_boolean_value),
    ]:
        value = parse_func(parser, valuename)
        if value:
            cfg[valuename] = value

    for objectname, object_class in [
        ("post_process", PostProcessConfig),
    ]:
        dictvalue = parse_dict_value(parser, objectname)
        if dictvalue is None:
            continue
        try:
            cfg[objectname] = object_class(**dictvalue)
        except Exception as e:  # noqa: BLE001
            msg = f"Failed to create {objectname}: {e!s}"
            raise RuntimeError(msg) from e

    return cfg


# TODO(edgy): Support pyproject.toml configuration
# https://github.com/EdgyEdgemond/changelog-gen/issues/55
def read(**kwargs) -> Config:
    """Read configuration from local environment.

    Supported configuration locations (checked in order):
    * pyproject.toml
    * setup.cfg
    """
    overrides, post_process = _process_overrides(kwargs)
    cfg = {}

    pyproject = Path("pyproject.toml")
    setup = Path("setup.cfg")

    if pyproject.exists():
        # parse pyproject
        cfg = _process_pyproject(pyproject)

    if not cfg and setup.exists():
        cfg = _process_setup_cfg(setup)

    if "post_process" not in cfg and post_process:
        cfg["post_process"] = post_process

    if "post_process" in cfg and post_process:
        cfg["post_process"].url = post_process.url or cfg["post_process"].url
        cfg["post_process"].auth_env = post_process.auth_env or cfg["post_process"].auth_env

    cfg.update(overrides)

    if cfg.get("post_process"):
        url = cfg["post_process"].url
        body = cfg["post_process"].body
        if "{issue_ref}" in url or "{new_version}" in url:
            warn(
                "{replace} format strings are not supported in `post_process.url` configuration, use ::replace:: instead.",  # noqa: E501
                DeprecationWarning,
                stacklevel=2,
            )
            cfg["post_process"].url = url.format(issue_ref="::issue_ref::", new_version="::version::")
        if "{issue_ref}" in body or "{new_version}" in body:
            warn(
                "{replace} format strings are not supported in `post_process.body` configuration, use ::replace:: instead.",  # noqa: E501
                DeprecationWarning,
                stacklevel=2,
            )
            cfg["post_process"].body = body.format(issue_ref="::issue_ref::", new_version="::version::")

    if cfg.get("issue_link") and "{issue_ref}" in cfg["issue_link"]:
        warn(
            "{replace} format strings are not supported in `issue_link` configuration, use ::replace:: instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        cfg["issue_link"] = cfg["issue_link"].format(issue_ref="::issue_ref::", new_version="::version::")

    return Config(**cfg)
