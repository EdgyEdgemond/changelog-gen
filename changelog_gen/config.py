from __future__ import annotations

import contextlib
import dataclasses
import json
import logging
import re
import typing
from configparser import (
    ConfigParser,
    NoOptionError,
)
from pathlib import Path
from warnings import warn

import rtoml

from changelog_gen import errors

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class CommitType:
    """Represent a supported commit_type."""

    header: str
    semver: str = "patch"


SUPPORTED_TYPES = {
    "feat": CommitType(
        header="Features and Improvements",
        semver="minor",
    ),
    "fix": CommitType(
        header="Bug fixes",
        semver="patch",
    ),
    "bug": CommitType(
        header="Bug fixes",
        semver="patch",
    ),
    "docs": CommitType(
        header="Documentation",
        semver="patch",
    ),
    "chore": CommitType(
        header="Miscellaneous",
        semver="patch",
    ),
    "ci": CommitType(
        header="Miscellaneous",
        semver="patch",
    ),
    "perf": CommitType(
        header="Miscellaneous",
        semver="patch",
    ),
    "refactor": CommitType(
        header="Miscellaneous",
        semver="patch",
    ),
    "revert": CommitType(
        header="Miscellaneous",
        semver="patch",
    ),
    "style": CommitType(
        header="Miscellaneous",
        semver="patch",
    ),
    "test": CommitType(
        header="Miscellaneous",
        semver="patch",
    ),
}

# Deprecated
SUPPORTED_SECTIONS = {
    "feat": "Features and Improvements",
    "fix": "Bug fixes",
    "docs": "Documentation",
    "misc": "Miscellaneous",
}

DEFAULT_SECTION_MAPPING = {
    "bug": "fix",
    "chore": "misc",
    "ci": "misc",
    "docs": "docs",
    "perf": "misc",
    "refactor": "misc",
    "revert": "misc",
    "style": "misc",
    "test": "misc",
}


def extract_dict_value(parser: ConfigParser, dictvaluename: str) -> dict | None:
    """Extract a dictionary from configuration."""
    try:
        value = parser.get("changelog_gen", dictvaluename)
    except NoOptionError:
        return None

    return parse_dict_value(value)


def parse_dict_value(value: str) -> dict:
    """Process a dict from a configuration string."""
    ret = {}
    dictvalue = list(
        filter(None, (x.strip() for x in value.splitlines())),
    )

    for value in dictvalue:
        k, v = value.split("=")
        ret[k.strip()] = v.strip()

    return ret


def extract_list_value(parser: ConfigParser, listvaluename: str) -> list | None:
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


def extract_boolean_value(parser: ConfigParser, valuename: str) -> bool | None:
    """Extract a boolean from configuration."""
    with contextlib.suppress(NoOptionError):
        return parser.getboolean("changelog_gen", valuename)
    return None


def extract_string_value(parser: ConfigParser, valuename: str) -> str | None:
    """Extract a string from configuration."""
    with contextlib.suppress(NoOptionError):
        return parser.get("changelog_gen", valuename)
    return None


@dataclasses.dataclass
class PostProcessConfig:
    """Post Processor configuration options."""

    url: str | None = None
    verb: str = "POST"
    # The body to send as a post-processing command,
    # can have the entries: ::issue_ref::, ::version::
    body: str = '{"body": "Released on ::version::"}'
    auth_type: str = "basic"  # future proof config
    headers: dict | None = None
    # Name of an environment variable to use as HTTP Basic Auth parameters.
    # The variable should contain "{user}:{api_key}"
    auth_env: str | None = None

    @classmethod
    def from_dict(cls: type[PostProcessConfig], data: dict) -> PostProcessConfig:
        """Convert a dictionary of key value pairs into a PostProcessConfig object."""
        if "headers" in data and isinstance(data["headers"], str):
            data["headers"] = json.loads(data["headers"])
        return cls(**data)


@dataclasses.dataclass
class Config:
    """Changelog configuration options."""

    verbose: int = 0

    issue_link: str | None = None
    commit_link: str | None = None
    date_format: str | None = None
    version_string: str = "v{new_version}"

    allowed_branches: list[str] = dataclasses.field(default_factory=list)
    commit_types: dict[str, CommitType] = dataclasses.field(default_factory=lambda: SUPPORTED_TYPES)

    release: bool = False
    commit: bool = False
    allow_dirty: bool = False
    reject_empty: bool = False

    post_process: PostProcessConfig | None = None

    @property
    def semver_mappings(self: typing.Self) -> dict[str, str]:
        """Generate `type: semver` mapping from commit types."""
        return {ct: c.semver for ct, c in self.commit_types.items()}

    @property
    def type_headers(self: typing.Self) -> dict[str, str]:
        """Generate `type: header` mapping from commit types."""
        return {ct: c.header for ct, c in self.commit_types.items()}

    @classmethod
    def from_dict(cls: type[Config], data: dict) -> Config:
        """Convert a dictionary of key value pairs into a Config object."""
        if "commit_types" in data:
            for k, v in data["commit_types"].items():
                value = json.loads(v) if isinstance(v, str) else v
                data["commit_types"][k] = CommitType(**value)
        return cls(**data)


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

    for valuename, extract_func in [
        ("issue_link", extract_string_value),
        ("commit_link", extract_string_value),
        ("date_format", extract_string_value),
        ("version_string", extract_string_value),
        ("allowed_branches", extract_list_value),
        ("commit_types", extract_dict_value),
        ("sections", extract_dict_value),
        ("section_mapping", extract_dict_value),
        ("post_process", extract_dict_value),
        ("release", extract_boolean_value),
        ("commit", extract_boolean_value),
        ("allow_dirty", extract_boolean_value),
        ("reject_empty", extract_boolean_value),
    ]:
        value = extract_func(parser, valuename)
        if value:
            cfg[valuename] = value

    if cfg != {}:
        warn(
            "setup.cfg use is deprecated, run `changelog migrate` to generate equivalent toml to paste into pyproject.toml",  # noqa: E501
            FutureWarning,
            stacklevel=2,
        )

    return cfg


def check_deprecations(cfg: dict) -> None:
    """Check parsed configuration dict for deprecated features."""
    if cfg.get("post_process"):
        url = cfg["post_process"].get("url", "")
        body = cfg["post_process"].get("body", "")
        if "{issue_ref}" in url or "{new_version}" in url:
            warn(
                "{replace} format strings are not supported in `post_process.url` configuration, use ::replace:: instead.",  # noqa: E501
                FutureWarning,
                stacklevel=2,
            )
            cfg["post_process"]["url"] = url.format(issue_ref="::issue_ref::", new_version="::version::")
        if "{issue_ref}" in body or "{new_version}" in body:
            warn(
                "{replace} format strings are not supported in `post_process.body` configuration, use ::replace:: instead.",  # noqa: E501
                FutureWarning,
                stacklevel=2,
            )
            cfg["post_process"]["body"] = body.format(issue_ref="::issue_ref::", new_version="::version::")

    if cfg.get("issue_link") and "{issue_ref}" in cfg["issue_link"]:
        warn(
            "{replace} format strings are not supported in `issue_link` configuration, use ::replace:: instead.",
            FutureWarning,
            stacklevel=2,
        )
        cfg["issue_link"] = cfg["issue_link"].format(issue_ref="::issue_ref::", new_version="::version::")

    if cfg.get("commit_link") and "{commit_hash}" in cfg["commit_link"]:
        warn(
            "{replace} format strings are not supported in `commit_link` configuration, use ::replace:: instead.",
            FutureWarning,
            stacklevel=2,
        )
        cfg["commit_link"] = cfg["commit_link"].format(commit_hash="::commit_hash::")

    if cfg.get("section_mapping") or cfg.get("sections"):
        warn(
            "`sections` and `section_mapping` are no longer supported, use `commit_types` instead.",
            FutureWarning,
            stacklevel=2,
        )

    if cfg.get("section_mapping") or cfg.get("sections") and not cfg.get("commit_types"):
        sm = cfg.pop("section_mapping", DEFAULT_SECTION_MAPPING.copy())
        s = cfg.pop("sections", SUPPORTED_SECTIONS.copy())

        commit_types = {k: {"header": v, "semver": "minor" if k == "feat" else "patch"} for k, v in s.items()}
        for type_, section in sm.items():
            header = s.get(section, "Unknown")
            commit_types[type_] = {"header": header, "semver": "minor" if section == "feat" else "patch"}

        cfg["commit_types"] = commit_types


def read(**kwargs) -> Config:  # noqa: C901
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
        cfg["post_process"] = {
            "url": post_process.url,
            "auth_env": post_process.auth_env,
        }

    if "post_process" in cfg and post_process:
        cfg["post_process"]["url"] = post_process.url or cfg["post_process"].get("url")
        cfg["post_process"]["auth_env"] = post_process.auth_env or cfg["post_process"].get("auth_env")

    cfg.update(overrides)

    check_deprecations(cfg)

    for replace_key_path in [
        ("issue_link",),
        ("commit_link",),
        ("post_process", "url"),
        ("post_process", "body"),
    ]:
        data, value = cfg, None
        for key in replace_key_path:
            value = data.get(key)
            if key in data:
                data = data[key]

        # check for non supported replace keys
        supported = {"::issue_ref::", "::version::", "::commit_hash::"}
        unsupported = sorted(set(re.findall(r"(::.*?::)", value or "") or []) - supported)
        if unsupported:
            msg = f"""Replace string(s) ('{"', '".join(unsupported)}') not supported."""
            raise errors.UnsupportedReplaceError(msg)

    if cfg.get("post_process"):
        pp = cfg["post_process"]
        try:
            cfg["post_process"] = PostProcessConfig.from_dict(pp)
        except Exception as e:  # noqa: BLE001
            msg = f"Failed to create post_process: {e!s}"
            raise RuntimeError(msg) from e

    return Config.from_dict(cfg)
