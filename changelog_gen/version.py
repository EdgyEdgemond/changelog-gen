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
        info = {}

        print(describe_out)

        return info
