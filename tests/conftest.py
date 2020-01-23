import os

import pytest


@pytest.fixture
def cwd(tmp_path):
    orig = os.getcwd()

    try:
        os.chdir(tmp_path)
        yield tmp_path
    except Exception:
        raise
    finally:
        os.chdir(orig)


@pytest.fixture
def git_repo(git_repo):
    orig = os.getcwd()

    try:
        os.chdir(git_repo.workspace)
        yield git_repo
    except Exception:
        raise
    finally:
        os.chdir(orig)
