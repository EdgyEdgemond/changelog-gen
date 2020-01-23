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
        defaults = {}

        if not Path("setup.cfg").exists():
            return defaults

        with open("setup.cfg", "rt", encoding="utf-8") as config_fp:
            config_content = config_fp.read()
            # config_newlines = config_fp.newlines

        self._config.read_string(config_content)

        # No supported list values yet.
        for listvaluename in ():
            try:
                value = self._config.get("changelog_gen", listvaluename)
                defaults[listvaluename] = list(
                    filter(None, (x.strip() for x in value.splitlines())),
                )
            except NoOptionError:
                pass  # no default value then ;)

        for boolvaluename in ("release", "commit"):
            try:
                defaults[boolvaluename] = self._config.getboolean(
                    "changelog_gen", boolvaluename,
                )
            except NoOptionError:
                pass  # no default value then ;)

        return defaults
