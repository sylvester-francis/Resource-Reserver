"""Extended authentication CLI commands for MFA, Roles, and OAuth2."""

from getpass import getpass

import requests
import typer

from cli.client import APIClient
from cli.config import config
from cli.ui import error, hint, info, render_table, section, success, warning
from cli.utils import confirm_action

# MFA commands
mfa_app = typer.Typer(help="Multi-Factor Authentication (MFA) commands")

# Role commands
role_app = typer.Typer(help="Role management commands")

# OAuth2 commands
oauth_app = typer.Typer(help="OAuth2 client management commands")


# ============================================================================
# MFA Commands
# ============================================================================


@mfa_app.command("setup")
def mfa_setup():
    """Setup Multi-Factor Authentication (MFA) for your account."""
    client = APIClient()

    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    try:
        result = client.mfa_setup()

        section("MFA setup")
        info(
            "Scan this QR code with your authenticator app (Google Authenticator, Authy, 1Password, etc.)"
        )
        hint(f"QR Code (base64): {result['qr_code'][:50]}...")
        hint("Or manually enter this secret key:")
        info(f"{result['secret']}")

        # Try to copy secret to clipboard
        try:
            import pyperclip

            pyperclip.copy(result["secret"])
            success("Secret copied to clipboard.")
        except (ImportError, Exception):
            hint("Copy the secret manually if clipboard is unavailable.")

        # Display backup codes
        section("Backup codes")
        for i, code in enumerate(result["backup_codes"], 1):
            info(f"{i:2}. {code}")

        warning(
            "Save these backup codes now; they won't be shown again. Store them securely."
        )

        hint(
            "Next: run `cli auth mfa enable` and enter the 6-digit code from your authenticator app."
        )

    except requests.exceptions.HTTPError as e:
        if "already enabled" in str(e):
            warning("MFA is already enabled for your account.")
            hint("Use `cli auth mfa disable` first if you want to reset it.")
        else:
            error(f"MFA setup failed: {e}")
        raise typer.Exit(1) from None


@mfa_app.command("enable")
def mfa_enable():
    """Enable MFA by verifying a code from your authenticator app."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    section("Enable MFA")
    hint("Open your authenticator app and enter the 6-digit code.")

    code = typer.prompt("6-digit code")

    if len(code) != 6 or not code.isdigit():
        error("Invalid code format. Must be 6 digits.")
        raise typer.Exit(1) from None

    try:
        client.mfa_verify(code)
        success("MFA enabled successfully.")
        hint(
            "Next login requires your password and a code from your authenticator app."
        )

    except requests.exceptions.HTTPError as e:
        if "Invalid" in str(e):
            error("Invalid code. Please try again.")
        else:
            error(f"Failed to enable MFA: {e}")
        raise typer.Exit(1) from None


@mfa_app.command("disable")
def mfa_disable():
    """Disable MFA for your account."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    section("Disable MFA")
    warning("This will remove two-factor authentication protection.")

    if not confirm_action("Are you sure you want to disable MFA?"):
        warning("Cancelled.")
        return

    password = getpass("Enter your password to confirm: ")

    try:
        client.mfa_disable(password)
        success("MFA disabled.")
        hint("Two-factor authentication has been removed from your account.")

    except requests.exceptions.HTTPError as e:
        if "Invalid password" in str(e):
            error("Invalid password.")
        else:
            error(f"Failed to disable MFA: {e}")
        raise typer.Exit(1) from None


@mfa_app.command("backup-codes")
def mfa_backup_codes():
    """Regenerate MFA backup codes."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    section("Regenerate backup codes")
    warning("This will invalidate your existing backup codes.")

    if not confirm_action("Generate new backup codes?"):
        warning("Cancelled.")
        return

    try:
        result = client.mfa_regenerate_backup_codes()

        success("New backup codes generated.")
        for i, code in enumerate(result["backup_codes"], 1):
            info(f"{i:2}. {code}")

        warning(
            "Save these codes in a safe place. Your old backup codes are now invalid."
        )

    except requests.exceptions.HTTPError as e:
        if "not enabled" in str(e):
            warning("MFA is not enabled on your account.")
            hint("Run `cli auth mfa setup` first.")
        else:
            error(f"Failed to regenerate codes: {e}")
        raise typer.Exit(1) from None


# ============================================================================
# Role Commands
# ============================================================================


@role_app.command("list")
def list_roles():
    """List all available roles in the system."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    try:
        roles = client.list_roles()

        if not roles:
            info("No roles found.")
            return

        section("Available roles")
        rows = [
            (role["id"], role["name"], role.get("description", "")) for role in roles
        ]
        render_table(["ID", "Name", "Description"], rows, title="Roles")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to list roles: {e}")
        raise typer.Exit(1) from None


@role_app.command("create")
def create_role(
    name: str = typer.Argument(..., help="Role name (e.g., admin, user, guest)"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Role description"
    ),
):
    """Create a new role (admin only)."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    try:
        role = client.create_role(name, description)
        success(f"Role '{role['name']}' created.")
        if role.get("description"):
            info(f"Description: {role['description']}")

    except requests.exceptions.HTTPError as e:
        if "already exists" in str(e).lower():
            warning(f"Role '{name}' already exists.")
        elif "403" in str(e) or "Forbidden" in str(e):
            error("Permission denied - admin role required.")
        else:
            error(f"Failed to create role: {e}")
        raise typer.Exit(1) from None


@role_app.command("my-roles")
def my_roles():
    """Show your assigned roles."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    try:
        roles = client.get_my_roles()

        if not roles:
            info("You have no roles assigned.")
            hint("Contact an administrator to assign roles.")
            return

        section("Your roles")
        for role in roles:
            info(role["name"])
            if role.get("description"):
                hint(f"  {role['description']}")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to get roles: {e}")
        raise typer.Exit(1) from None


@role_app.command("assign")
def assign_role(
    user_id: int = typer.Argument(..., help="User ID to assign role to"),
    role_name: str = typer.Argument(..., help="Role name (admin, user, guest)"),
):
    """Assign a role to a user (admin only)."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    try:
        client.assign_role(user_id, role_name)
        success(f"Role '{role_name}' assigned to user {user_id}.")

    except requests.exceptions.HTTPError as e:
        if "403" in str(e) or "Forbidden" in str(e):
            error("Permission denied - admin role required.")
        elif "404" in str(e) or "not found" in str(e):
            error(f"Role '{role_name}' not found.")
        else:
            error(f"Failed to assign role: {e}")
        raise typer.Exit(1) from None


@role_app.command("remove")
def remove_role(
    user_id: int = typer.Argument(..., help="User ID to remove role from"),
    role_name: str = typer.Argument(..., help="Role name to remove"),
):
    """Remove a role from a user (admin only)."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    if not confirm_action(f"Remove role '{role_name}' from user {user_id}"):
        warning("Cancelled.")
        return

    try:
        client.remove_role(user_id, role_name)
        success(f"Role '{role_name}' removed from user {user_id}.")

    except requests.exceptions.HTTPError as e:
        if "403" in str(e):
            error("Permission denied - admin role required.")
        else:
            error(f"Failed to remove role: {e}")
        raise typer.Exit(1) from None


# ============================================================================
# OAuth2 Commands
# ============================================================================


@oauth_app.command("create")
def create_oauth_client(
    name: str = typer.Argument(..., help="Client application name"),
    redirect_uri: str = typer.Argument(..., help="Redirect URI for OAuth2 flow"),
):
    """Create a new OAuth2 client application."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    try:
        result = client.create_oauth_client(
            client_name=name, redirect_uris=[redirect_uri]
        )

        section("OAuth2 client created")
        success(f"Client Name: {result['client_name']}")
        info(f"Client ID: {result['client_id']}")
        info(f"Client Secret: {result['client_secret']}")
        info("Redirect URIs:")
        for uri in result["redirect_uris"]:
            hint(f"- {uri}")

        warning("Save the client secret now; it will not be shown again.")

        # Try to copy client secret to clipboard
        try:
            import pyperclip

            pyperclip.copy(result["client_secret"])
            success("Client secret copied to clipboard.")
        except (ImportError, Exception):
            hint("Copy the client secret manually if clipboard is unavailable.")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to create OAuth2 client: {e}")
        raise typer.Exit(1) from None


@oauth_app.command("list")
def list_oauth_clients():
    """List your OAuth2 client applications."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    try:
        clients = client.list_oauth_clients()

        if not clients:
            info("No OAuth2 clients found.")
            hint("Create one with: cli oauth create")
            return

        section(f"Your OAuth2 clients ({len(clients)})")

        for oauth_client in clients:
            info(f"{oauth_client['client_name']}")
            hint(f"ID: {oauth_client['client_id']}")
            hint(f"Grant Types: {oauth_client['grant_types']}")
            hint(f"Scopes: {oauth_client['scope']}")
            hint("Redirect URIs:")
            for uri in oauth_client["redirect_uris"]:
                hint(f"  - {uri}")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to list OAuth2 clients: {e}")
        raise typer.Exit(1) from None


@oauth_app.command("delete")
def delete_oauth_client(
    client_id: str = typer.Argument(..., help="Client ID to delete"),
):
    """Delete an OAuth2 client application."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from None

    section("Delete OAuth2 client")
    info(f"Client ID: {client_id}")
    warning(
        "This will revoke all access tokens and prevent new authorizations. This action cannot be undone."
    )

    if not confirm_action("\nDelete this OAuth2 client?"):
        warning("Cancelled.")
        return

    try:
        client.delete_oauth_client(client_id)
        success("OAuth2 client deleted successfully.")

    except requests.exceptions.HTTPError as e:
        if "404" in str(e) or "not found" in str(e):
            error("OAuth2 client not found or you lack permission to delete it.")
        else:
            error(f"Failed to delete OAuth2 client: {e}")
        raise typer.Exit(1) from None
