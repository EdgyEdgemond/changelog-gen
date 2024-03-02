from unittest import mock

import pytest

from changelog_gen import errors, version


class TestBumpVersion:
    @pytest.mark.usefixtures("cwd")
    def test_errors_wrapped(self):
        with pytest.raises(errors.VersionDetectionError):
            version.BumpVersion.get_version_info("patch")

    @pytest.mark.parametrize(
        ("current_version", "new_version", "semver"),
        [
            ("0.0.0", "0.0.1", "patch"),
            ("0.1.0", "0.1.1", "patch"),
            ("1.2.3", "1.2.4", "patch"),
            ("1.2.3", "1.3.0", "minor"),
            ("1.2.3", "2.0.0", "major"),
        ],
    )
    def test_get_version_info(self, cwd, current_version, new_version, semver):
        p = cwd / "setup.cfg"
        p.write_text(
            f"""
[bumpversion]
current_version = {current_version}
commit = false
tag = false
        """.strip(),
        )

        assert version.BumpVersion.get_version_info(semver) == {"current": current_version, "new": new_version}

    @pytest.mark.parametrize(
        ("current_version", "new_version", "semver"),
        [
            ("0.0.0", "0.0.1rc0", "patch"),
            ("0.1.0", "0.1.1rc0", "patch"),
            ("1.2.3", "1.2.4rc0", "patch"),
            ("1.2.3", "1.3.0rc0", "minor"),
            ("1.2.3", "2.0.0rc0", "major"),
            ("1.2.3rc0", "1.2.3rc1", "build"),
            ("1.2.3rc0", "1.2.3", "release"),
        ],
    )
    def test_get_version_info_with_release_flow(self, cwd, current_version, new_version, semver):
        p = cwd / "setup.cfg"
        p.write_text(
            f"""
[bumpversion]
current_version = {current_version}
commit = false
tag = false
parse = ^
    (?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)
    ((?P<release>rc)
    (?P<build>\\d+)  # pre-release version num
    )?
serialize =
    {{major}}.{{minor}}.{{patch}}{{release}}{{build}}
    {{major}}.{{minor}}.{{patch}}

[bumpversion:part:release]
optional_value = _
values =
    rc
    _
        """.strip(),
        )

        assert version.BumpVersion.get_version_info(semver) == {"current": current_version, "new": new_version}

    def test_release(self, monkeypatch):
        monkeypatch.setattr(version.subprocess, "check_output", mock.Mock())
        version.BumpVersion.release("1.2.3")
        assert version.subprocess.check_output.call_args == mock.call(
            ["bumpversion", "--new-version", "1.2.3", "patch"],
        )
