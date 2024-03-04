import pytest

from changelog_gen import config, errors


@pytest.fixture()
def config_factory(cwd):
    def factory(contents=None):
        p = cwd / "pyproject.toml"
        p.touch()
        if contents:
            p.write_text(contents)

    return factory


@pytest.fixture()
def setup_factory(cwd):
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
    def test_read_picks_up_boolean_values(self, config_factory, value, exp_key, exp_value):
        config_factory(
            f"""
[tool.changelog_gen]
{value}
""",
        )

        c = config.read()
        assert getattr(c, exp_key) == exp_value

    def test_read_picks_up_strings_values(self, config_factory):
        config_factory(
            """
[tool.changelog_gen]
issue_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::"
""",
        )

        c = config.read()
        assert c.issue_link == "https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::"

    @pytest.mark.backwards_compat()
    def test_read_issue_link_backwards_compat(self, config_factory):
        config_factory(
            """
[tool.changelog_gen]
issue_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/{issue_ref}"
""",
        )

        c = config.read()
        assert c.issue_link == "https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::"

    def test_read_picks_up_list_values(self, config_factory):
        config_factory(
            """
[tool.changelog_gen]
allowed_branches = [
    "main",
    "feature/11",
]
""",
        )

        c = config.read()
        assert c.allowed_branches == ["main", "feature/11"]

    def test_read_picks_up_commit_types(self, config_factory):
        config_factory(
            """
[tool.changelog_gen.commit_types]
bug.header = "Bug fixes"
docs.header = "Documentation"
feat.header = "Features and Improvements"
feat.semver = "minor"
feature.header = "Features and Improvements"
feature.semver = "minor"
fix.header = "Bug fixes"
misc.header = "Miscellaneous"
test.header = "Bug fixes"
""",
        )

        c = config.read()
        assert c.commit_types == {
            "bug": config.CommitType(
                header="Bug fixes",
            ),
            "docs": config.CommitType(
                header="Documentation",
            ),
            "feat": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "feature": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "fix": config.CommitType(
                header="Bug fixes",
            ),
            "misc": config.CommitType(
                header="Miscellaneous",
            ),
            "test": config.CommitType(
                header="Bug fixes",
            ),
        }

    @pytest.mark.backwards_compat()
    def test_read_picks_up_section_mapping_backwards_compat(self, config_factory):
        config_factory(
            """
[tool.changelog_gen.section_mapping]
feature = "feat"
bug = "fix"
test = "fix"
""",
        )

        c = config.read()
        assert c.commit_types == {
            "bug": config.CommitType(
                header="Bug fixes",
            ),
            "docs": config.CommitType(
                header="Documentation",
            ),
            "feat": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "feature": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "fix": config.CommitType(
                header="Bug fixes",
            ),
            "misc": config.CommitType(
                header="Miscellaneous",
            ),
            "test": config.CommitType(
                header="Bug fixes",
            ),
        }

    @pytest.mark.backwards_compat()
    def test_read_picks_up_custom_sections_backwards_compat(self, config_factory):
        config_factory(
            """
[tool.changelog_gen.sections]
bug = "Bugfixes"
feat = "New Features"
remove = "Chore"
ci = "Chore"

[tool.changelog_gen.section_mapping]
bug = "bug"
ci = "ci"
chore = "misc"
docs = "docs"
perf = "misc"
refactor = "misc"
revert = "misc"
style = "misc"
test = "misc"
""",
        )

        c = config.read()
        assert c.commit_types == {
            "bug": config.CommitType(
                header="Bugfixes",
            ),
            "feat": config.CommitType(
                header="New Features",
                semver="minor",
            ),
            "remove": config.CommitType(
                header="Chore",
            ),
            "ci": config.CommitType(
                header="Chore",
            ),
            "chore": config.CommitType(
                header="Unknown",
            ),
            "docs": config.CommitType(
                header="Unknown",
            ),
            "perf": config.CommitType(
                header="Unknown",
            ),
            "refactor": config.CommitType(
                header="Unknown",
            ),
            "revert": config.CommitType(
                header="Unknown",
            ),
            "style": config.CommitType(
                header="Unknown",
            ),
            "test": config.CommitType(
                header="Unknown",
            ),
        }


@pytest.mark.backwards_compat()
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
    def test_read_picks_up_boolean_values(self, setup_factory, value, exp_key, exp_value):
        setup_factory(
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
            "issue_link = https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::",
            "issue_link=https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::",
        ],
    )
    def test_read_picks_up_strings_values(self, setup_factory, issue_link):
        setup_factory(
            f"""
[changelog_gen]
{issue_link}
""",
        )

        c = config.read()
        assert c.issue_link == "https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::"

    @pytest.mark.parametrize(
        "branches",
        [
            "allowed_branches = main,feature/11",
            "allowed_branches=main,feature/11",
            "allowed_branches = \n  main\n  feature/11",
        ],
    )
    def test_read_picks_up_list_values(self, setup_factory, branches):
        setup_factory(
            f"""
[changelog_gen]
{branches}
""",
        )

        c = config.read()
        assert c.allowed_branches == ["main", "feature/11"]

    def test_read_picks_up_commit_types(self, setup_factory):
        setup_factory(
            """
[changelog_gen]
commit_types =
  bug = {"header": "Bug fixes"}
  docs = {"header": "Documentation"}
  feat = {"header": "Features and Improvements", "semver": "minor"}
  feature = {"header": "Features and Improvements", "semver": "minor"}
  fix = {"header": "Bug fixes"}
  misc = {"header": "Miscellaneous"}
  test = {"header": "Bug fixes"}
""",
        )

        c = config.read()
        assert c.commit_types == {
            "bug": config.CommitType(
                header="Bug fixes",
            ),
            "docs": config.CommitType(
                header="Documentation",
            ),
            "feat": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "feature": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "fix": config.CommitType(
                header="Bug fixes",
            ),
            "misc": config.CommitType(
                header="Miscellaneous",
            ),
            "test": config.CommitType(
                header="Bug fixes",
            ),
        }

    def test_read_picks_up_section_mapping(self, setup_factory):
        setup_factory(
            """
[changelog_gen]
section_mapping =
  feature=feat
  bug=fix
  test=fix
""",
        )

        c = config.read()
        assert c.commit_types == {
            "bug": config.CommitType(
                header="Bug fixes",
            ),
            "docs": config.CommitType(
                header="Documentation",
            ),
            "feat": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "feature": config.CommitType(
                header="Features and Improvements",
                semver="minor",
            ),
            "fix": config.CommitType(
                header="Bug fixes",
            ),
            "misc": config.CommitType(
                header="Miscellaneous",
            ),
            "test": config.CommitType(
                header="Bug fixes",
            ),
        }

    def test_read_picks_up_custom_sections(self, setup_factory):
        setup_factory(
            """
[changelog_gen]
sections =
  bug= Bugfixes
  feat =New Features
  remove = Chore
  ci=Chore

section_mapping =
  bug = bug
  ci = ci
  chore = misc
  docs = docs
  perf = misc
  refactor = misc
  revert = misc
  style = misc
  test = misc
""",
        )

        c = config.read()
        assert c.commit_types == {
            "bug": config.CommitType(
                header="Bugfixes",
            ),
            "feat": config.CommitType(
                header="New Features",
                semver="minor",
            ),
            "remove": config.CommitType(
                header="Chore",
            ),
            "ci": config.CommitType(
                header="Chore",
            ),
            "chore": config.CommitType(
                header="Unknown",
            ),
            "docs": config.CommitType(
                header="Unknown",
            ),
            "perf": config.CommitType(
                header="Unknown",
            ),
            "refactor": config.CommitType(
                header="Unknown",
            ),
            "revert": config.CommitType(
                header="Unknown",
            ),
            "style": config.CommitType(
                header="Unknown",
            ),
            "test": config.CommitType(
                header="Unknown",
            ),
        }


class TestPostProcessConfig:
    def test_read_picks_up_no_post_process_config(self, config_factory):
        config_factory(
            """
[tool.changelog_gen]
release = true
        """,
        )

        c = config.read()
        assert c.post_process is None

    def test_read_picks_up_post_process_config_pyproject(self, config_factory):
        config_factory(
            """
[tool.changelog_gen.post_process]
url = "https://fake_rest_api/::issue_ref::"
verb = "PUT"
body = '{"issue": "::issue_ref::", "comment": "Released in ::version::"}'
auth_env = "MY_API_AUTH"
headers."content-type" = "application/json"
""",
        )

        c = config.read()
        assert c.post_process == config.PostProcessConfig(
            url="https://fake_rest_api/::issue_ref::",
            verb="PUT",
            body='{"issue": "::issue_ref::", "comment": "Released in ::version::"}',
            auth_env="MY_API_AUTH",
            headers={"content-type": "application/json"},
        )

    def test_read_picks_up_unexpected_replaces(self, config_factory):
        config_factory(
            """
[tool.changelog_gen.post_process]
url = "https://fake_rest_api/::issue_ref::"
verb = "PUT"
body = '{"issue": "::issue_ref::", "comment": "Released in ::version_tag::", "other": "::unexpected::"}'
auth_env = "MY_API_AUTH"
        """,
        )

        with pytest.raises(errors.UnsupportedReplaceError) as e:
            config.read()

        assert str(e.value) == "Replace string(s) ('::unexpected::', '::version_tag::') not supported."

    @pytest.mark.backwards_compat()
    def test_read_picks_up_post_process_config_backwards_compat(self, config_factory):
        config_factory(
            """
[tool.changelog_gen.post_process]
url = "https://fake_rest_api/{issue_ref}"
verb = "PUT"
body = '{{"issue": "{issue_ref}", "comment": "Released in {new_version}"}}'
auth_env = "MY_API_AUTH"
headers = '{"content-type": "application/json"}'
""",
        )

        c = config.read()
        assert c.post_process == config.PostProcessConfig(
            url="https://fake_rest_api/::issue_ref::",
            verb="PUT",
            body='{"issue": "::issue_ref::", "comment": "Released in ::version::"}',
            auth_env="MY_API_AUTH",
            headers={"content-type": "application/json"},
        )

    def test_read_picks_up_post_process_override(self, config_factory):
        config_factory(
            """
[tool.changelog_gen]
commit = false
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
[tool.changelog_gen.post_process]
enabled = false
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
def test_read_overrides_pyproject(config_factory, key, value):
    config_factory("")

    c = config.read(**{key: value})
    assert getattr(c, key) == value
