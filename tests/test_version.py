from unittest import mock

import pytest

from changelog_gen import errors, version


def test_parse_bump_my_version_info():
    assert version.parse_bump_my_version_info(
        "patch",
        [
            "1.2.3 -- bump -+- major --- 2.0.0rc0",
            "               +- minor --- 1.3.0rc0",
            "               +- patch --- 1.2.4rc0",
            '               +- release - invalid: The part has already the maximum value among ["rc", "final"] and cannot be bumped.',  # noqa: E501
            "               +- build --- 1.2.3final1",
        ],
    ) == ("1.2.3", "1.2.4rc0")


def test_parse_bump2version_info():
    assert version.parse_bump2version_info(
        "patch",
        [
            "current_version=0.1.0",
            "commit=false",
            "tag=false",
            "parse=^",
            "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)",
            "((?P<release>rc)",
            "(?P<build>\\d+)  # pre-release version num",
            ")?",
            "serialize=",
            "{major}.{minor}.{patch}{release}{build}",
            "{major}.{minor}.{patch}",
            "new_version=0.1.1rc0",
        ],
    ) == ("0.1.0", "0.1.1rc0")


@pytest.mark.parametrize(
    ("verbose", "lib", "expected_verbosity"),
    [
        (1, "bump-my-version", ["-v"]),
        (2, "bump-my-version", ["-vv"]),
        (3, "bump-my-version", ["-vvv"]),
        (1, "bump2version", ["--verbose"]),
        (2, "bump2version", ["--verbose", "--verbose"]),
        (3, "bump2version", ["--verbose", "--verbose", "--verbose"]),
    ],
)
def test_generate_verbosity(monkeypatch, verbose, lib, expected_verbosity):
    monkeypatch.setattr(version, "bump_library", lib)
    assert version.generate_verbosity(verbose) == expected_verbosity


class TestBumpMyVersion:
    @pytest.mark.usefixtures("cwd")
    def test_errors_wrapped(self):
        with pytest.raises(errors.VersionDetectionError):
            version.BumpVersion().get_version_info("patch")

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
    @pytest.mark.skipif(version.bump_library == "bump2version", reason="bump2version installed")
    def test_get_version_info(self, cwd, current_version, new_version, semver):
        p = cwd / "pyproject.toml"
        p.write_text(
            f"""
[tool.bumpversion]
current_version = "{current_version}"
commit = false
tag = false
        """.strip(),
        )

        assert version.BumpVersion().get_version_info(semver) == {"current": current_version, "new": new_version}

    @pytest.mark.parametrize(
        ("current_version", "new_version", "semver"),
        [
            ("0.0.0", "0.0.1rc0", "patch"),
            ("0.1.0", "0.1.1rc0", "patch"),
            ("1.2.3", "1.2.4rc0", "patch"),
            ("1.2.3", "1.3.0rc0", "minor"),
            ("1.2.3", "2.0.0rc0", "major"),
            ("1.2.3rc0", "1.2.3rc1", "build"),
            ("1.2.3rc1", "1.2.3rc2", "build"),
            ("1.2.3rc1", "1.2.3", "release"),
        ],
    )
    @pytest.mark.skipif(version.bump_library == "bump2version", reason="bump2version installed")
    def test_get_version_info_release_flow(self, cwd, current_version, new_version, semver):
        p = cwd / "pyproject.toml"
        p.write_text(
            f"""
[tool.bumpversion]
current_version = "{current_version}"
commit = false
tag = false
parse = '''(?x)
    (?P<major>0|[1-9]\\d*)\\.
    (?P<minor>0|[1-9]\\d*)\\.
    (?P<patch>0|[1-9]\\d*)
    (?:
        (?P<release>[a-zA-Z-]+)       # pre-release label
        (?P<build>0|[1-9]\\d*)        # pre-release version number
    )?                                # pre-release section is optional
'''
serialize = [
    "{{major}}.{{minor}}.{{patch}}{{release}}{{build}}",
    "{{major}}.{{minor}}.{{patch}}",
]
parts.release.values = ["rc", "final"]
parts.release.optional_value = "final"
        """.strip(),
        )

        assert version.BumpVersion().get_version_info(semver) == {"current": current_version, "new": new_version}

    @pytest.mark.skipif(version.bump_library == "bump2version", reason="bump2version installed")
    def test_release(self, monkeypatch):
        monkeypatch.setattr(version.subprocess, "check_output", mock.Mock(return_value=b""))
        version.BumpVersion().release("1.2.3")
        assert version.subprocess.check_output.call_args == mock.call(
            ["bump-my-version", "bump", "patch", "--new-version", "1.2.3"],
            stderr=version.subprocess.STDOUT,
        )


@pytest.mark.backwards_compat()
@pytest.mark.skipif(version.bump_library == "bump-my-version", reason="bump-my-version installed")
class TestBump2Version:
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

        assert version.BumpVersion().get_version_info(semver) == {"current": current_version, "new": new_version}

    @pytest.mark.parametrize(
        ("current_version", "new_version", "semver"),
        [
            ("0.0.0", "0.0.1rc0", "patch"),
            ("0.1.0", "0.1.1rc0", "patch"),
            ("1.2.3", "1.2.4rc0", "patch"),
            ("1.2.3", "1.3.0rc0", "minor"),
            ("1.2.3", "2.0.0rc0", "major"),
            ("1.2.3rc0", "1.2.3rc1", "build"),
            ("1.2.3rc1", "1.2.3rc2", "build"),
            ("1.2.3rc1", "1.2.3", "release"),
        ],
    )
    def test_get_version_info_release_flow(self, cwd, current_version, new_version, semver):
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

        assert version.BumpVersion().get_version_info(semver) == {"current": current_version, "new": new_version}

    def test_release(self, monkeypatch):
        monkeypatch.setattr(version.subprocess, "check_output", mock.Mock(return_value=b""))
        version.BumpVersion().release("1.2.3")
        assert version.subprocess.check_output.call_args == mock.call(
            ["bumpversion", "patch", "--new-version", "1.2.3"],
            stderr=version.subprocess.STDOUT,
        )
