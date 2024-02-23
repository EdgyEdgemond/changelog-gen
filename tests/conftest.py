import os
import pathlib

import pytest


@pytest.fixture()
def cwd(tmp_path):
    orig = pathlib.Path.cwd()

    try:
        os.chdir(str(tmp_path))
        yield tmp_path
    finally:
        os.chdir(orig)


@pytest.fixture()
def git_repo(git_repo):
    git_repo.run("git config user.email 'you@example.com'")
    git_repo.run("git config user.name 'Your Name'")

    orig = pathlib.Path.cwd()

    try:
        os.chdir(str(git_repo.workspace))
        yield git_repo
    finally:
        os.chdir(orig)
