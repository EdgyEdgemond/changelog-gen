import subprocess

from changelog_gen import errors


class Git:
    @classmethod
    def get_latest_tag_info(cls):
        describe_out = None
        for tags in ["[0-9]*", "v[0-9]*"]:
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
                            tags,
                        ],
                        stderr=subprocess.STDOUT,
                    )
                    .decode()
                    .strip()
                    .split("-")
                )
            except subprocess.CalledProcessError:
                pass
            else:
                break
        else:
            raise errors.VcsError("Unable to get version number from git tags")

        try:
            rev_parse_out = (
                subprocess.check_output(
                    [
                        "git",
                        "rev-parse",
                        "--tags",
                        "--abbrev-ref",
                        "HEAD",
                    ],
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError:
            raise errors.VcsError("Unable to get current git branch")

        info = {
            "dirty": False,
            "branch": rev_parse_out[-1],
        }

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
