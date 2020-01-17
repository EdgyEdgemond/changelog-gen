import subprocess

from changelog_gen import errors


class Git:
    @classmethod
    def get_latest_tag_info(cls):
        try:
            describe_out = (
                subprocess.check_output(
                    [
                        "git",
                        "describe",
                        "--tags",
                        "--dirty",
                        "--long",
                        "--match",
                        "[0-9]*",
                    ],
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("-")
            )
        except subprocess.CalledProcessError:
            raise errors.VcsError("Unable to get version number from git tags")

        info = {"dirty": False}

        if describe_out[-1].strip() == "dirty":
            info["dirty"] = True
            describe_out.pop()

        info["commit_sha"] = describe_out.pop().lstrip("g")
        info["distance_to_latest_tag"] = int(describe_out.pop())
        info["current_version"] = "-".join(describe_out).lstrip("v")

        return info

    @classmethod
    def add_path(cls, path):
        subprocess.check_output(["git", "add", "--update", path])

    @classmethod
    def commit(cls, version):
        subprocess.check_output(
            ["git", "commit", "-m", "Update CHANGELOG for {}".format(version)],
        )
