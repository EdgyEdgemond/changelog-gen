class ChangelogException(Exception):  # noqa: N818
    """Base exception class."""


class NoReleaseNotesError(ChangelogException):
    """No release notes directory found."""


class InvalidSectionError(ChangelogException):
    """Unsupported section detected."""


class VcsError(ChangelogException):
    """Version control error."""


class VersionDetectionError(ChangelogException):
    """Bumpversion error."""


class UnsupportedReplaceError(ChangelogException):
    """Unsupported ::replace:: in configuration string."""
