import pytest

from changelog_gen.config import Config


@pytest.fixture
def configured(cwd):
    p = cwd / "setup.cfg"
    p.write_text("""
[changelog_gen]
release = true
""")


@pytest.fixture
def empty_config(cwd):
    p = cwd / "setup.cfg"
    p.write_text("")


def test_config_handles_missing_file(cwd):
    assert Config().read() == {}


def test_config_handles_empty_file(empty_config):
    assert Config().read() == {}


def test_config_picks_up_configured_values(configured):
    assert Config().read() == {"release": True}
