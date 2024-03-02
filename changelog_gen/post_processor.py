from __future__ import annotations

import logging
import os
import typing
from http import HTTPStatus

import httpx
import typer

if typing.TYPE_CHECKING:
    from changelog_gen.config import PostProcessConfig

logger = logging.getLogger(__name__)


class BearerAuth(httpx.Auth):
    """Implement Bearer token auth class for httpx."""

    def __init__(self: typing.Self, token: str) -> None:
        self.token = f"Bearer {token}"

    def auth_flow(self: typing.Self, request: httpx.Request) -> typing.Generator[httpx.Request, httpx.Response, None]:
        """Send the request, with bearer token."""
        request.headers["Authorization"] = self.token
        yield request


def make_client(cfg: PostProcessConfig) -> httpx.Client:
    """Generate HTTPx client with authorization if configured."""
    auth = None
    if cfg.auth_env:
        user_auth = os.environ.get(cfg.auth_env)
        if not user_auth:
            logger.error('Missing environment variable "%s"', cfg.auth_env)
            raise typer.Exit(code=1)

        if cfg.auth_type == "bearer":
            auth = BearerAuth(user_auth)
        else:
            # Fall back to basic auth
            try:
                username, api_key = user_auth.split(":")
            except ValueError as e:
                logger.error(  # noqa: TRY400
                    "Unexpected content in %s, need '{username}:{api_key}' for basic auth",
                    cfg.auth_env,
                )
                raise typer.Exit(code=1) from e
            else:
                auth = httpx.BasicAuth(username=username, password=api_key)

    return httpx.Client(
        auth=auth,
        headers=cfg.headers,
    )


def per_issue_post_process(
    cfg: PostProcessConfig,
    issue_refs: list[str],
    version_tag: str,
    *,
    dry_run: bool = False,
) -> None:
    """Run post process for all provided issue references."""
    if not cfg.url:
        return
    logger.warning("Post processing:")

    client = make_client(cfg)

    for issue in issue_refs:
        url, body = cfg.url, cfg.body
        for find, replace in [
            ("::issue_ref::", issue),
            ("::version::", version_tag),
        ]:
            url = url.replace(find, replace)
            body = body.replace(find, replace)

        if dry_run:
            logger.warning("  Would request: %s %s %s", cfg.verb, url, body)
        else:
            logger.info("  Request: %s %s", cfg.verb, url)
            r = client.request(
                method=cfg.verb,
                url=url,
                content=body,
            )
            try:
                logger.info("    Response: %s", HTTPStatus(r.status_code).name)
                r.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("Post process request failed.")  # noqa: TRY400
                logger.warning("  %s", e.response.text)
