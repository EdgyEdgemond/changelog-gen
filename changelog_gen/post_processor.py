import os
from http import HTTPStatus
from typing import List

import click
import requests
from requests.auth import HTTPBasicAuth

from changelog_gen.config import PostProcessConfig


def make_session(cfg: PostProcessConfig) -> requests.Session:
    connection = requests.Session()
    if cfg.auth_env:
        user_auth = os.environ.get(cfg.auth_env)
        if not user_auth:
            click.echo(f'Missing environment variable "{cfg.auth_env}"')
            raise click.Abort()

        try:
            username, api_key = user_auth.split(":")
        except ValueError:
            click.echo(f'Unexpected content in {cfg.auth_env}, need "{{username}}:{{api_key}}"')
            raise click.Abort()
        else:
            connection.auth = HTTPBasicAuth(username, api_key)

    # TODO(tr) A good improvement would be to allow the headers to come from the config as well
    connection.headers = {"content-type": "application/json"}
    return connection


def per_issue_post_process(
    cfg: PostProcessConfig,
    issue_refs: List[str],
    version_tag: str,
    dry_run: bool = False,
):
    if not cfg.url:
        return

    connection = make_session(cfg)

    for issue in issue_refs:
        ep = cfg.url.format(issue_ref=issue, new_version=version_tag)
        body = cfg.body.format(
            issue_ref=issue,
            new_version=version_tag,
        )
        if dry_run:
            click.echo(f"{cfg.verb} {ep} {body}")
        else:
            r = connection.request(
                method=cfg.verb,
                url=ep,
                data=body,
            )
            try:
                click.echo(f"{cfg.verb} {ep}: {HTTPStatus(r.status_code).name}")
                r.raise_for_status()
            except requests.HTTPError as e:
                click.echo(e.response.text)
