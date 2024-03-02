import pytest


@pytest.fixture()
def setup(cwd):
    p = cwd / "setup.cfg"
    p.write_text(
        """
[changelog_gen]
release = true
commit = true
allow_dirty = false
reject_empty = false
allowed_branches = master, test
section_mapping =
    bug=fix
    ci=misc
    docs=docs
    refactor=misc
    revert=misc
    style=misc
    test=misc
version_string={new_version}
date_format=on %%Y-%%b-%%d
issue_link = https://github.com/EdgyEdgemond/changelog-gen/issues/{issue_ref}
commit_link = https://github.com/EdgyEdgemond/changelog-gen/issues/{commit_hash}
post_process=
    url=http://url
    verb=PUT
    body={{"body": "version {new_version}"}}
    headers={"content-type": "application/json"}
    auth_env=AUTH_KEY

""",
    )

    return cwd


@pytest.fixture()
def simple_setup(cwd):
    p = cwd / "setup.cfg"
    p.write_text(
        """
[changelog_gen]
release = true
commit = true
allow_dirty = false
reject_empty = false
allowed_branches = master
version_string={new_version}
date_format=on %%Y-%%b-%%d
issue_link = https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::
commit_link = https://github.com/EdgyEdgemond/changelog-gen/issues/::commit_hash::

""",
    )

    return cwd


@pytest.mark.usefixtures("setup")
def test_migrate_generates_toml(cli_runner):
    result = cli_runner.invoke(["migrate"])

    assert result.exit_code == 0
    assert (
        result.output
        == """[tool.changelog_gen]
issue_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::"
commit_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/::commit_hash::"
date_format = "on %Y-%b-%d"
version_string = "{new_version}"
release = true
commit = true
allowed_branches = ["master", "test"]

[tool.changelog_gen.post_process]
url = "http://url"
verb = "PUT"
body = "{\\"body\\": \\"version ::version::\\"}"
auth_env = "AUTH_KEY"

[tool.changelog_gen.post_process.headers]
content-type = "application/json"

[tool.changelog_gen.type_headers]
feat = "Features and Improvements"
fix = "Bug fixes"
docs = "Documentation"
misc = "Miscellaneous"
bug = "Bug fixes"
ci = "Miscellaneous"
refactor = "Miscellaneous"
revert = "Miscellaneous"
style = "Miscellaneous"
test = "Miscellaneous"

"""
    )


@pytest.mark.usefixtures("simple_setup")
def test_migrate_generates_toml_simple_setup(cli_runner):
    result = cli_runner.invoke(["migrate"])

    assert result.exit_code == 0
    assert (
        result.output
        == """[tool.changelog_gen]
issue_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/::issue_ref::"
commit_link = "https://github.com/EdgyEdgemond/changelog-gen/issues/::commit_hash::"
date_format = "on %Y-%b-%d"
version_string = "{new_version}"
release = true
commit = true
allowed_branches = ["master"]

"""
    )


@pytest.mark.usefixtures("cwd")
def test_migrate_no_setup(cli_runner):
    result = cli_runner.invoke(["migrate"])

    assert result.exit_code == 1
    assert result.output == "setup.cfg not found.\n"
