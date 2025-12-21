"""Setup commands for initial bootstrap and re-opening setup."""

from getpass import getpass

import requests
import typer
from rich import print

from cli.client import APIClient

setup_app = typer.Typer(help="Initial setup and bootstrap commands")


@setup_app.command("status")
def setup_status():
    """Show setup completion status."""
    client = APIClient()
    try:
        status = client.setup_status()
        print("\n🧭 [bold]Setup Status[/bold]")
        print(f"   Setup complete: {'yes' if status.get('setup_complete') else 'no'}")
        print(f"   Setup reopened: {'yes' if status.get('setup_reopened') else 'no'}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to get setup status: {e}")
        raise typer.Exit(1) from None


@setup_app.command("init")
def setup_init(
    existing_user: str | None = typer.Option(
        None, "--existing-user", "-e", help="Existing username to promote"
    ),
    token: str | None = typer.Option(
        None, "--token", help="Setup unlock token (required if setup was reopened)"
    ),
):
    """Initialize setup by creating or promoting an admin user."""
    client = APIClient()

    try:
        status = client.setup_status()
    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to get setup status: {e}")
        raise typer.Exit(1) from None

    if status.get("setup_complete") and not status.get("setup_reopened"):
        print("✅ Setup is already complete.")
        print("💡 Use [cyan]cli setup unlock[/cyan] with a token to reopen setup.")
        raise typer.Exit(0)

    if status.get("setup_reopened") and not token:
        token = getpass("Setup unlock token: ")

    if existing_user:
        payload = {"existing_username": existing_user}
    else:
        print("\n👤 [bold]Create initial admin[/bold]")
        username = typer.prompt("Admin username")
        while True:
            password = getpass("Password: ")
            confirm_password = getpass("Confirm password: ")
            if password == confirm_password:
                break
            print("❌ Passwords do not match. Please try again.")
        payload = {"username": username, "password": password}

    try:
        result = client.setup_initialize(payload, token=token)
        print("\n✅ [bold green]Setup completed successfully[/bold green]")
        print(
            f"   Admin user: [bold]{result.get('admin_username')}[/bold] "
            f"(id: {result.get('admin_user_id')})"
        )
        print("💡 You can now login via [cyan]cli auth login[/cyan]")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Setup initialization failed: {e}")
        raise typer.Exit(1) from None


@setup_app.command("unlock")
def setup_unlock(
    token: str | None = typer.Option(
        None, "--token", help="Setup unlock token from SETUP_REOPEN_TOKEN"
    ),
):
    """Reopen setup (requires secure token)."""
    client = APIClient()

    if not token:
        token = getpass("Setup unlock token: ")

    try:
        result = client.setup_unlock(token)
        print(f"✅ {result.get('message', 'Setup reopened')}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to reopen setup: {e}")
        raise typer.Exit(1) from None
