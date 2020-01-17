from pathlib import Path

import click

import changelog_gen
from changelog_gen.writer import SUPPORTED_EXTENSIONS


def common_options(command):
    """
    Mark ``cli`` commands with common flags.

    Used to mark ``cli`` commands with the flags that add the option
    flags that we want to include in all of them.
    """
    options = [
        click.version_option(
            changelog_gen.VERSION, "-v", "--version", prog_name="changelog-gen",
        ),
        click.help_option("--help", help="Show this message and exit."),
    ]

    for option in options:
        command = option(command)

    return command


def detect_extension():
    for ext in SUPPORTED_EXTENSIONS:
        if Path("CHANGELOG.{ext}".format(ext=ext)).exists():
            return ext
