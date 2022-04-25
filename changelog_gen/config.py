import dataclasses
import logging
from configparser import (
    ConfigParser,
    NoOptionError,
)
from pathlib import Path
from typing import Optional


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
    auth_env: Optional[str] = None


class Config:
    def __init__(self):
        self._config = ConfigParser("")

        self._config.add_section("changelog_gen")

    def read(self):  # noqa
        config = {}
        object_map = {
            "post_process": PostProcessConfig,
        }

        if not Path("setup.cfg").exists():
            return config

        with open("setup.cfg", "rt", encoding="utf-8") as config_fp:
            config_content = config_fp.read()

        self._config.read_string(config_content)

        for stringvaluename in ("issue_link", "date_format"):
            try:
                config[stringvaluename] = self._config.get(
                    "changelog_gen",
                    stringvaluename,
                )
            except NoOptionError:
                pass

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
            except Exception as e:
                raise RuntimeError(f"Failed to create {objectname}: {str(e)}")

        for boolvaluename in ("release", "commit", "allow_dirty"):
            try:
                config[boolvaluename] = self._config.getboolean(
                    "changelog_gen", boolvaluename,
                )
            except NoOptionError:
                config[boolvaluename] = False

        return config

    def parse_dict_value(self, dictvaluename):
        # TODO(tr) Add unit tests to ensure we handle spaces correctly
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

    def parse_list_value(self, listvaluename):
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
