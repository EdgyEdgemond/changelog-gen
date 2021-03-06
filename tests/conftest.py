import os

import pytest


@pytest.fixture
def cwd(tmp_path):
    orig = os.getcwd()

    try:
        os.chdir(str(tmp_path))
        yield tmp_path
    except Exception:
        raise
    finally:
        os.chdir(orig)


@pytest.fixture
def git_repo(git_repo):
    git_repo.run("git config user.email 'you@example.com'")
    git_repo.run("git config user.name 'Your Name'")

    orig = os.getcwd()

    try:
        os.chdir(str(git_repo.workspace))
        yield git_repo
    except Exception:
        raise
    finally:
        os.chdir(orig)
