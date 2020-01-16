import subprocess


class Git:
    def get_latest_tag_info(self):
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
            click.echo("Unable to get version number from git tags")
            raise click.Abort

        info = {"dirty": False}

        if describe_out[-1].strip() == "dirty":
            info["dirty"] = True
            describe_out.pop()

        info["commit_sha"] = describe_out.pop().lstrip("g")
        info["distance_to_latest_tag"] = int(describe_out.pop())
        info["current_version"] = "-".join(describe_out).lstrip("v")

        return info
