class ChangelogException(Exception):
    pass


class NoReleaseNotesError(ChangelogException):
    pass


class InvalidSectionError(ChangelogException):
    pass


class VcsError(ChangelogException):
    pass


class VersionDetectionError(ChangelogException):
    pass
