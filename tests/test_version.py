from unittest import mock

from changelog_gen import version


# TODO: mock a bumpversion config in cwd fixture instead of mocking subprocess
class TestBumpVersion:
    def test_get_version_info(self, monkeypatch):
        monkeypatch.setattr(version.subprocess, "check_output", mock.Mock())
        version.subprocess.check_output.return_value = b"current_version=1.0.0\ncommit=False\nnew_version=1.1.0"

        assert version.BumpVersion.get_version_info("patch") == {"current": "1.0.0", "new": "1.1.0"}

    def test_release(self, monkeypatch):
        monkeypatch.setattr(version.subprocess, "check_output", mock.Mock())
        version.BumpVersion.release("1.2.3")
        assert version.subprocess.check_output.call_args == mock.call(
            ["bumpversion", "--new-version", "1.2.3", "patch"],
        )
