from enum import IntEnum

import typer


class Verbosity(IntEnum):
    """Verbosity output levels, QUIET (least) to ALL (most) messaging."""

    QUIET = 0
    DEBUG = 1
    NOISY = 2
    ALL = 3


def quiet_echo(message: str, verbose: int = 0) -> None:
    """Verbose echo, set to QUIET."""
    verbose_echo(message, Verbosity.QUIET, verbose)


def debug_echo(message: str, verbose: int = 0) -> None:
    """Verbose echo, set to DEBUG."""
    verbose_echo(message, Verbosity.DEBUG, verbose)


def noisy_echo(message: str, verbose: int = 0) -> None:
    """Verbose echo, set to NOISY."""
    verbose_echo(message, Verbosity.NOISY, verbose)


def all_echo(message: str, verbose: int = 0) -> None:
    """Verbose echo, set to ALL."""
    verbose_echo(message, Verbosity.ALL, verbose)


def verbose_echo(message: str, required_verbose: Verbosity = Verbosity.ALL, verbose: int = 0) -> None:
    """Echo a verbose message if current verbose setting is high enough."""
    if verbose >= required_verbose:
        typer.echo(message)
