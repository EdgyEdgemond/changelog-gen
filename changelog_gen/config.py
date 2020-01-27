import logging
from configparser import (
    ConfigParser,
    NoOptionError,
)
from pathlib import Path


logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self._config = ConfigParser("")

        self._config.add_section("changelog_gen")

    def read(self):
        config = {}

        if not Path("setup.cfg").exists():
            return config

        with open("setup.cfg", "rt", encoding="utf-8") as config_fp:
            config_content = config_fp.read()

        self._config.read_string(config_content)

        for listvaluename in ("allowed_branches",):
            try:
                value = self._config.get("changelog_gen", listvaluename)
            except NoOptionError:
                pass  # no default value then ;)
            else:
                config[listvaluename] = []

                listvalue = list(
                    filter(None, (x.strip() for x in value.splitlines())),
                )

                for value in listvalue:
                    config[listvaluename].extend(value.split(","))

        for boolvaluename in ("release", "commit", "allow_dirty"):
            try:
                config[boolvaluename] = self._config.getboolean(
                    "changelog_gen", boolvaluename,
                )
            except NoOptionError:
                config[boolvaluename] = False

        return config
