import subprocess

import click


class BumpVersion:
    def get_version_info(self, semver):
        try:
            describe_out = (
                subprocess.check_output(
                    [
                        "bumpversion",
                        semver,
                        "--dry-run",
                        "--list",
                        "--allow-dirty",
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
