import pytest

from changelog_gen.config import Config


@pytest.fixture
def config_factory(cwd):
    def factory(contents=None):
        p = cwd / "setup.cfg"
        p.touch()
        if contents:
            p.write_text(contents)
    return factory


def test_config_handles_missing_file(cwd):
    assert Config().read() == {}


def test_config_handles_empty_file(config_factory):
    config_factory()
    assert Config().read() == {"release": False, "allow_dirty": False, "commit": False}


@pytest.mark.parametrize("release", [
    "release=true",
    "release = true",
])
def test_config_picks_up_boolean_values(config_factory, release):
    config_factory("""
[changelog_gen]
{}
""".format(release))

    c = Config().read()
    assert c["release"] is True


@pytest.mark.parametrize("branches", [
    "allowed_branches = master,feature/11",
    "allowed_branches=master,feature/11",
    "allowed_branches = \n  master\n  feature/11",
])
def test_config_picks_up_list_values(config_factory, branches):
    config_factory("""
[changelog_gen]
{}
""".format(branches))

    c = Config().read()
    assert c["allowed_branches"] == ["master", "feature/11"]
