from unittest import mock

import pytest

from changelog_gen import version


class TestBumpVersion:
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

    def test_release(self, monkeypatch):
        monkeypatch.setattr(version.subprocess, "check_output", mock.Mock())
        version.BumpVersion.release("1.2.3")
        assert version.subprocess.check_output.call_args == mock.call(
            ["bumpversion", "--new-version", "1.2.3", "patch"],
        )
