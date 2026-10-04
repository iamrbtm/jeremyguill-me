from __future__ import annotations

import click
from flask import current_app

from .services import create_bootstrap_token, make_password_hash


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


@admin_cli.command("set-password")
@click.option("--username", default="admin", show_default=True)
@click.option("--password", default=None, help="Password (prompted if omitted).")
def set_password(username: str, password: str | None) -> None:
    """Print ADMIN_USERNAME / ADMIN_PASSWORD_HASH values to configure password login."""
    if password is None:
        password = click.prompt("Password", hide_input=True, confirmation_prompt=False)
    digest = make_password_hash(password)
    click.echo(f"ADMIN_USERNAME={username}")
    click.echo(f"ADMIN_PASSWORD_HASH={digest}")
