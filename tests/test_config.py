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


@pytest.mark.parametrize("issue_link", [
    "issue_link = https://github.com/EdgyEdgemond/changelog-gen/issues/{}",
    "issue_link=https://github.com/EdgyEdgemond/changelog-gen/issues/{}",
])
def test_config_picks_up_strings_values(config_factory, issue_link):
    config_factory("""
[changelog_gen]
{}
""".format(issue_link))

    c = Config().read()
    assert c["issue_link"] == "https://github.com/EdgyEdgemond/changelog-gen/issues/{}"


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


def test_config_picks_up_section_mapping(config_factory):
    config_factory("""
[changelog_gen]
section_mapping =
  feature=feat
  bug=fix
  test=fix
""")

    c = Config().read()
    assert c["section_mapping"] == {"feature": "feat", "bug": "fix", "test": "fix"}


def test_config_picks_up_custom_sections(config_factory):
    config_factory("""
[changelog_gen]
sections =
  bug=Bugfixes
  feat=New Features
  remove=Removals
""")

    c = Config().read()
    assert c["sections"] == {"bug": "Bugfixes", "feat": "New Features", "remove": "Removals"}
