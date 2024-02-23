import os
import typing
from http import HTTPStatus

import click
import httpx

if typing.TYPE_CHECKING:
    from changelog_gen.config import PostProcessConfig


def make_client(cfg: "PostProcessConfig") -> httpx.Client:
    auth = None
    if cfg.auth_env:
        user_auth = os.environ.get(cfg.auth_env)
        if not user_auth:
            click.echo(f'Missing environment variable "{cfg.auth_env}"')
            raise click.Abort

        try:
            username, api_key = user_auth.split(":")
        except ValueError as e:
            click.echo(f'Unexpected content in {cfg.auth_env}, need "{{username}}:{{api_key}}"')
            raise click.Abort from e
        else:
            auth = httpx.BasicAuth(username=username, password=api_key)

    # TODO(tr): A good improvement would be to allow the headers to come from the config as well
    # Does setup.cfg support dicts easily? migrate to pyproject.toml support
    return httpx.Client(
        auth=auth,
        headers={"content-type": "application/json"},
    )


def per_issue_post_process(
    cfg: "PostProcessConfig",
    issue_refs: list[str],
    version_tag: str,
    *,
    dry_run: bool = False,
) -> None:
    if not cfg.url:
        return

    client = make_client(cfg)

    for issue in issue_refs:
        ep = cfg.url.format(issue_ref=issue, new_version=version_tag)
        body = cfg.body.format(
            issue_ref=issue,
            new_version=version_tag,
        )
        if dry_run:
            click.echo(f"{cfg.verb} {ep} {body}")
        else:
            r = client.request(
                method=cfg.verb,
                url=ep,
                data=body,
            )
            try:
                click.echo(f"{cfg.verb} {ep}: {HTTPStatus(r.status_code).name}")
                r.raise_for_status()
            except httpx.HTTPError as e:
                click.echo(e.response.text)
