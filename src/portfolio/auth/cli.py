from __future__ import annotations

import click
from flask import current_app

from .services import create_bootstrap_token


@click.group("admin")
def admin_cli() -> None:
    """Administrative console commands."""


@admin_cli.command("bootstrap-passkeys")
def bootstrap_passkeys() -> None:
    token = create_bootstrap_token("initial")
    click.echo(f"{current_app.config['PUBLIC_ORIGIN']}/admin/bootstrap?token={token}")


@admin_cli.command("recover-passkeys")
@click.option("--confirm", prompt="Type RECOVER to revoke sessions and recover passkeys")
def recover_passkeys(confirm: str) -> None:
    if confirm != "RECOVER":
        raise click.ClickException("Recovery cancelled")
    token = create_bootstrap_token("recovery")
    click.echo(f"{current_app.config['PUBLIC_ORIGIN']}/admin/bootstrap?token={token}")
