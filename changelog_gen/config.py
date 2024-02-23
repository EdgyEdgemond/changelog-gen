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


@dataclasses.dataclass
class PostProcessConfig:
    url: str = ""
    verb: str = "POST"
    # The body to send as a post-processing command,
    # can have the entries: {issue_ref} {new_version}
    body: str = '{{"body": "Released on v{new_version}"}}'
    # Name of an environment variable to use as HTTP Basic Auth parameters.
    # The variable should contain "{user}:{api_key}"
    auth_env: str | None = None


class Config:
    def __init__(self) -> None:
        self._config = ConfigParser("")

        self._config.add_section("changelog_gen")

    def read(self) -> dict:  # noqa: C901
        config = {}
        object_map = {
            "post_process": PostProcessConfig,
        }

        if not Path("setup.cfg").exists():
            return config

        with Path("setup.cfg").open(encoding="utf-8") as config_fp:
            config_content = config_fp.read()

        self._config.read_string(config_content)

        for stringvaluename in ("issue_link", "date_format"):
            with contextlib.suppress(NoOptionError):
                config[stringvaluename] = self._config.get(
                    "changelog_gen",
                    stringvaluename,
                )

        for listvaluename in ("allowed_branches",):
            listvalue = self.parse_list_value(listvaluename)
            if listvalue:
                config[listvaluename] = listvalue

        for dictvaluename in ("section_mapping", "sections"):
            dictvalue = self.parse_dict_value(dictvaluename)
            if dictvalue:
                config[dictvaluename] = dictvalue

        for objectname, object_class in object_map.items():
            dictvalue = self.parse_dict_value(objectname) or {}
            try:
                config[objectname] = object_class(**dictvalue)
            except Exception as e:  # noqa: BLE001
                msg = f"Failed to create {objectname}: {e!s}"
                raise RuntimeError(msg) from e

        for boolvaluename in ("release", "commit", "allow_dirty"):
            try:
                config[boolvaluename] = self._config.getboolean(
                    "changelog_gen",
                    boolvaluename,
                )
            except NoOptionError:  # noqa: PERF203
                config[boolvaluename] = False

        return config

    def parse_dict_value(self, dictvaluename: str) -> dict:
        # TODO(tr): Add unit tests to ensure we handle spaces correctly
        #  At the moment key and value should NOT have spaces as they are copied verbatim.
        try:
            value = self._config.get("changelog_gen", dictvaluename)
        except NoOptionError:
            pass  # no default value then ;)
        else:
            ret = {}
            dictvalue = list(
                filter(None, (x.strip() for x in value.splitlines())),
            )

            for value in dictvalue:
                k, v = value.split("=")
                ret[k] = v

            return ret

    def parse_list_value(self, listvaluename: str) -> list:
        try:
            value = self._config.get("changelog_gen", listvaluename)
        except NoOptionError:
            pass  # no default value then ;)
        else:
            ret = []
            listvalue = list(
                filter(None, (x.strip() for x in value.splitlines())),
            )

            for value in listvalue:
                ret.extend(value.split(","))

            return ret
