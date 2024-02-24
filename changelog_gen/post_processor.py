import os
import typing
from http import HTTPStatus

import httpx
import typer

if typing.TYPE_CHECKING:
    from changelog_gen.config import PostProcessConfig


def make_client(cfg: "PostProcessConfig") -> httpx.Client:
    """Generate HTTPx client with authorization if configured."""
    auth = None
    if cfg.auth_env:
        user_auth = os.environ.get(cfg.auth_env)
        if not user_auth:
            typer.echo(f'Missing environment variable "{cfg.auth_env}"')
            raise typer.Exit(code=1)

        try:
            username, api_key = user_auth.split(":")
        except ValueError as e:
            typer.echo(f'Unexpected content in {cfg.auth_env}, need "{{username}}:{{api_key}}"')
            raise typer.Exit(code=1) from e
        else:
            auth = httpx.BasicAuth(username=username, password=api_key)

    return httpx.Client(
        auth=auth,
        headers=cfg.headers,
    )


def per_issue_post_process(
    cfg: "PostProcessConfig",
    issue_refs: list[str],
    version_tag: str,
    *,
    dry_run: bool = False,
) -> None:
    """Run post process for all provided issue references."""
    if not cfg.url:
        return

    client = make_client(cfg)

    for issue in issue_refs:
        url, body = cfg.url, cfg.body
        for find, replace in [
            ("$ISSUE_REF", issue),
            ("$VERSION", version_tag),
        ]:
            url = url.replace(find, replace)
            body = body.replace(find, replace)

        if dry_run:
            typer.echo(f"{cfg.verb} {url} {body}")
        else:
            r = client.request(
                method=cfg.verb,
                url=url,
                content=body,
            )
            try:
                typer.echo(f"{cfg.verb} {url}: {HTTPStatus(r.status_code).name}")
                r.raise_for_status()
            except httpx.HTTPError as e:
                typer.echo(e.response.text)
