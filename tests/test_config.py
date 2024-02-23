import pytest

from changelog_gen.config import (
    Config,
    PostProcessConfig,
)


@pytest.fixture()
def config_factory(cwd):
    def factory(contents=None):
        p = cwd / "setup.cfg"
        p.touch()
        if contents:
            p.write_text(contents)

    return factory


@pytest.mark.usefixtures("cwd")
def test_config_handles_missing_file():
    assert Config().read() == {}


def test_config_handles_empty_file(config_factory):
    config_factory()
    assert Config().read() == {
        "release": False,
        "allow_dirty": False,
        "commit": False,
        "post_process": PostProcessConfig(),
    }


@pytest.mark.parametrize(
    ("release", "exp_value"),
    [
        ("release=true", True),
        ("release = true", True),
        ("release=True", True),
        ("release = True", True),
        ("release=false", False),
        ("release = false", False),
        ("release=False", False),
        ("release = False", False),
    ],
)
def test_config_picks_up_boolean_values(config_factory, release, exp_value):
    config_factory(
        f"""
[changelog_gen]
{release}
""",
    )

    c = Config().read()
    assert c["release"] is exp_value


@pytest.mark.parametrize(
    "issue_link",
    [
        "issue_link = https://github.com/EdgyEdgemond/changelog-gen/issues/{}",
        "issue_link=https://github.com/EdgyEdgemond/changelog-gen/issues/{}",
    ],
)
def test_config_picks_up_strings_values(config_factory, issue_link):
    config_factory(
        f"""
[changelog_gen]
{issue_link}
""",
    )

    c = Config().read()
    assert c["issue_link"] == "https://github.com/EdgyEdgemond/changelog-gen/issues/{}"


@pytest.mark.parametrize(
    "branches",
    [
        "allowed_branches = master,feature/11",
        "allowed_branches=master,feature/11",
        "allowed_branches = \n  master\n  feature/11",
    ],
)
def test_config_picks_up_list_values(config_factory, branches):
    config_factory(
        f"""
[changelog_gen]
{branches}
""",
    )

    c = Config().read()
    assert c["allowed_branches"] == ["master", "feature/11"]


def test_config_picks_up_section_mapping(config_factory):
    config_factory(
        """
[changelog_gen]
section_mapping =
  feature=feat
  bug=fix
  test=fix
""",
    )

    c = Config().read()
    assert c["section_mapping"] == {"feature": "feat", "bug": "fix", "test": "fix"}


def test_config_picks_up_custom_sections(config_factory):
    config_factory(
        """
[changelog_gen]
sections =
  bug=Bugfixes
  feat=New Features
  remove=Removals
""",
    )

    c = Config().read()
    assert c["sections"] == {"bug": "Bugfixes", "feat": "New Features", "remove": "Removals"}


class TestPostProcessConfig:
    def test_config_picks_up_config(self, config_factory):
        config_factory(
            """
[changelog_gen]
post_process =
    url=https://fake_rest_api/
    verb=PUT
    body={{"issue": "{issue_ref}", "comment": "Released in {new_version}"}}
    auth_env=MY_API_AUTH
        """,
        )

        c = Config().read()
        assert c["post_process"] == PostProcessConfig(
            url="https://fake_rest_api/",
            verb="PUT",
            body='{{"issue": "{issue_ref}", "comment": "Released in {new_version}"}}',
            auth_env="MY_API_AUTH",
        )

    def test_config_rejects_unknown_fields(self, config_factory):
        config_factory(
            """
[changelog_gen]
post_process =
    enabled=false
        """,
        )
        with pytest.raises(RuntimeError, match="^Failed to create post_process: .*"):
            Config().read()
