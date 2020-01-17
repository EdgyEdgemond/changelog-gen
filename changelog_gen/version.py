import subprocess

import click


class BumpVersion:
    def get_version_info(self):
        try:
            describe_out = (
                subprocess.check_output(
                    [
                        "bumpversion",
                        "patch",
                        "--dry-run",
                        "--list",
                    ],
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError:
            click.echo("Unable to get version data from bumpversion")
            raise click.Abort

        bumpversion_data = {v.split("=")[0]: v.split("=")[1] for v in describe_out}

        return {
            "current": bumpversion_data["current_version"],
            "new": bumpversion_data["new_version"],
        }
