from __future__ import annotations

import contextlib
import dataclasses
import logging
from configparser import (
    ConfigParser,
    NoOptionError,
)
from pathlib import Path

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
    # can have the entries: {issue_ref} {new_version}
    body: str = '{{"body": "Released on v{new_version}"}}'
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


# TODO(edgy): Support pyproject.toml configuration
# https://github.com/EdgyEdgemond/changelog-gen/issues/50
def read(**kwargs) -> Config:
    """Read configuration from local environment.

    Supported configuration locations:
    * setup.cfg
    """
    parser = ConfigParser("")

    parser.add_section("changelog_gen")

    overrides, post_process = _process_overrides(kwargs)
    cfg = {}

    setup = Path("setup.cfg")
    if not setup.exists():
        return Config()

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

    if "post_process" not in cfg and post_process:
        cfg["post_process"] = post_process

    if "post_process" in cfg and post_process:
        cfg["post_process"].url = post_process.url or cfg["post_process"].url
        cfg["post_process"].auth_env = post_process.auth_env or cfg["post_process"].auth_env

    cfg.update(overrides)

    return Config(**cfg)
