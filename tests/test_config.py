import pytest

from changelog_gen import config


@pytest.fixture()
def config_factory(cwd):
    def factory(contents=None):
        p = cwd / "setup.cfg"
        p.touch()
        if contents:
            p.write_text(contents)

    return factory


@pytest.fixture()
def pyproject_factory(cwd):
    def factory(contents=None):
        p = cwd / "pyproject.toml"
        p.touch()
        if contents:
            p.write_text(contents)

    return factory


@pytest.fixture()
def _empty_config(config_factory):
    config_factory()


@pytest.mark.usefixtures("cwd")
def test_read_handles_missing_file():
    assert config.read() == config.Config()


@pytest.mark.usefixtures("_empty_config")
def test_read_handles_empty_file():
    assert config.read() == config.Config()


class TestPyprojectToml:
    @pytest.mark.parametrize(
        ("value", "exp_key", "exp_value"),
        [
            ("release = true", "release", True),
            ("commit = true", "commit", True),
            ("allow_dirty = true", "allow_dirty", True),
            ("reject_empty = true", "reject_empty", True),
            ("release = false", "release", False),
            ("commit = false", "commit", False),
            ("allow_dirty = false", "allow_dirty", False),
            ("reject_empty = false", "reject_empty", False),
        ],
    )
    def test_read_picks_up_boolean_values(self, pyproject_factory, value, exp_key, exp_value):
        pyproject_factory(
            f"""
[tool.changelog_gen]
{value}
""",
        )

        c = config.read()
        assert getattr(c, exp_key) == exp_value

    def test_read_picks_up_strings_values(self, pyproject_factory):
        pyproject_factory(
            """
[tool.changelog_gen]
issue_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/$ISSUE_REF"
""",
        )

        c = config.read()
        assert c.issue_link == "https://github.com/EdgyEdgemond/changelog-gen/issues/$ISSUE_REF"

    def test_read_issue_link_backwards_compat(self, pyproject_factory):
        pyproject_factory(
            """
[tool.changelog_gen]
issue_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/{issue_ref}"
""",
        )

        c = config.read()
        assert c.issue_link == "https://github.com/EdgyEdgemond/changelog-gen/issues/$ISSUE_REF"

    def test_read_picks_up_list_values(self, pyproject_factory):
        pyproject_factory(
            """
[tool.changelog_gen]
allowed_branches = [
    "master",
    "feature/11",
]
""",
        )

        c = config.read()
        assert c.allowed_branches == ["master", "feature/11"]

    def test_read_picks_up_section_mapping(self, pyproject_factory):
        pyproject_factory(
            """
[tool.changelog_gen.section_mapping]
feature = "feat"
bug = "fix"
test = "fix"
""",
        )

        c = config.read()
        assert c.section_mapping == {"feature": "feat", "bug": "fix", "test": "fix"}

    def test_read_picks_up_custom_sections(self, pyproject_factory):
        pyproject_factory(
            """
[tool.changelog_gen.sections]
bug = "Bugfixes"
feat = "New Features"
remove = "Chore"
ci = "Chore"
""",
        )

        c = config.read()
        assert c.sections == {"bug": "Bugfixes", "feat": "New Features", "remove": "Chore", "ci": "Chore"}


class TestSetupConfig:
    @pytest.mark.parametrize(
        ("value", "exp_key", "exp_value"),
        [
            ("release=true", "release", True),
            ("commit = true", "commit", True),
            ("allow_dirty=True", "allow_dirty", True),
            ("reject_empty = True", "reject_empty", True),
            ("release=false", "release", False),
            ("commit = false", "commit", False),
            ("allow_dirty=False", "allow_dirty", False),
            ("reject_empty = False", "reject_empty", False),
        ],
    )
    def test_read_picks_up_boolean_values(self, config_factory, value, exp_key, exp_value):
        config_factory(
            f"""
[changelog_gen]
{value}
""",
        )

        c = config.read()
        assert getattr(c, exp_key) == exp_value

    @pytest.mark.parametrize(
        "issue_link",
        [
            "issue_link = https://github.com/EdgyEdgemond/changelog-gen/issues/{}",
            "issue_link=https://github.com/EdgyEdgemond/changelog-gen/issues/{}",
        ],
    )
    def test_read_picks_up_strings_values(self, config_factory, issue_link):
        config_factory(
            f"""
[changelog_gen]
{issue_link}
""",
        )

        c = config.read()
        assert c.issue_link == "https://github.com/EdgyEdgemond/changelog-gen/issues/{}"

    @pytest.mark.parametrize(
        "branches",
        [
            "allowed_branches = master,feature/11",
            "allowed_branches=master,feature/11",
            "allowed_branches = \n  master\n  feature/11",
        ],
    )
    def test_read_picks_up_list_values(self, config_factory, branches):
        config_factory(
            f"""
[changelog_gen]
{branches}
""",
        )

        c = config.read()
        assert c.allowed_branches == ["master", "feature/11"]

    def test_read_picks_up_section_mapping(self, config_factory):
        config_factory(
            """
[changelog_gen]
section_mapping =
  feature=feat
  bug=fix
  test=fix
""",
        )

        c = config.read()
        assert c.section_mapping == {"feature": "feat", "bug": "fix", "test": "fix"}

    def test_read_picks_up_custom_sections(self, config_factory):
        config_factory(
            """
[changelog_gen]
sections =
  bug= Bugfixes
  feat =New Features
  remove = Chore
  ci=Chore
""",
        )

        c = config.read()
        assert c.sections == {"bug": "Bugfixes", "feat": "New Features", "remove": "Chore", "ci": "Chore"}


class TestPostProcessConfig:
    def test_read_picks_up_no_post_process_config(self, config_factory):
        config_factory(
            """
[changelog_gen]
release = true
        """,
        )

        c = config.read()
        assert c.post_process is None

    def test_read_picks_up_post_process_config(self, config_factory):
        config_factory(
            """
[changelog_gen]
post_process =
    url=https://fake_rest_api/$ISSUE_REF
    verb=PUT
    body={"issue": "$ISSUE_REF", "comment": "Released in $VERSION"}
    auth_env=MY_API_AUTH
    headers={"content-type": "application/json"}
""",
        )

        c = config.read()
        assert c.post_process == config.PostProcessConfig(
            url="https://fake_rest_api/$ISSUE_REF",
            verb="PUT",
            body='{"issue": "$ISSUE_REF", "comment": "Released in $VERSION"}',
            auth_env="MY_API_AUTH",
            headers={"content-type": "application/json"},
        )

    def test_read_picks_up_post_process_config_pyproject(self, pyproject_factory):
        pyproject_factory(
            """
[tool.changelog_gen.post_process]
url = "https://fake_rest_api/$ISSUE_REF"
verb = "PUT"
body = '{"issue": "$ISSUE_REF", "comment": "Released in $VERSION"}'
auth_env = "MY_API_AUTH"
[tool.changelog_gen.post_process.headers]
content-type = "application/json"
""",
        )

        c = config.read()
        assert c.post_process == config.PostProcessConfig(
            url="https://fake_rest_api/$ISSUE_REF",
            verb="PUT",
            body='{"issue": "$ISSUE_REF", "comment": "Released in $VERSION"}',
            auth_env="MY_API_AUTH",
            headers={"content-type": "application/json"},
        )

    def test_read_picks_up_post_process_config_backwards_compat(self, config_factory):
        config_factory(
            """
[changelog_gen]
post_process =
    url=https://fake_rest_api/{issue_ref}
    verb=PUT
    body={{"issue": "{issue_ref}", "comment": "Released in {new_version}"}}
    auth_env=MY_API_AUTH
        """,
        )

        c = config.read()
        assert c.post_process == config.PostProcessConfig(
            url="https://fake_rest_api/$ISSUE_REF",
            verb="PUT",
            body='{"issue": "$ISSUE_REF", "comment": "Released in $VERSION"}',
            auth_env="MY_API_AUTH",
        )

    def test_read_picks_up_post_process_override(self, config_factory):
        config_factory(
            """
[changelog_gen]
commit=False
        """,
        )

        c = config.read(
            post_process_url="https://fake_rest_api/",
            post_process_auth_env="MY_API_AUTH",
        )
        assert c.post_process == config.PostProcessConfig(
            url="https://fake_rest_api/",
            auth_env="MY_API_AUTH",
        )

    def test_read_rejects_unknown_fields(self, config_factory):
        config_factory(
            """
[changelog_gen]
post_process =
    enabled=false
        """,
        )
        with pytest.raises(RuntimeError, match="^Failed to create post_process: .*"):
            config.read()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("release", True),
        ("commit", True),
        ("allow_dirty", True),
        ("reject_empty", True),
        ("date_format", "%Y-%m-%d"),
    ],
)
def test_read_overrides(config_factory, key, value):
    config_factory(
        """
[bumpversion]
commit=true
""",
    )

    c = config.read(**{key: value})
    assert getattr(c, key) == value


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("release", True),
        ("commit", True),
        ("allow_dirty", True),
        ("reject_empty", True),
        ("date_format", "%Y-%m-%d"),
    ],
)
def test_read_overrides_pyproject(pyproject_factory, key, value):
    pyproject_factory(
        """[tool.changelog-gen]
place = "holder"
""",
    )

    c = config.read(**{key: value})
    assert getattr(c, key) == value
