"""Extended authentication CLI commands for MFA, Roles, and OAuth2."""

from getpass import getpass

import requests
import typer
from rich import print
from rich.console import Console
from rich.table import Table

from cli.client import APIClient
from cli.config import config
from cli.utils import confirm_action

# Initialize
console = Console()

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
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    try:
        result = client.mfa_setup()

        print("\n🔐 [bold]MFA Setup[/bold]")
        print("=" * 60)
        print(
            "\n📱 [bold green]Scan this QR code with your authenticator app:[/bold green]"
        )
        print("   (Google Authenticator, Authy, 1Password, etc.)")

        # Display QR code (as base64 data URI)
        print(f"\n[dim]QR Code: {result['qr_code'][:50]}...[/dim]")
        print("\n💡 Or manually enter this secret key:")
        print(f"   [bold cyan]{result['secret']}[/bold cyan]")

        # Try to copy secret to clipboard
        try:
            import pyperclip

            pyperclip.copy(result["secret"])
            print("   ✅ Secret copied to clipboard!")
        except (ImportError, Exception):
            print("   💡 Copy the secret manually")

        # Display backup codes
        print(
            "\n🔑 [bold yellow]BACKUP CODES (Save these in a safe place!):[/bold yellow]"
        )
        print("=" * 60)
        for i, code in enumerate(result["backup_codes"], 1):
            print(f"   {i:2}. {code}")

        print("\n⚠️  [bold red]IMPORTANT:[/bold red]")
        print("   • Save these backup codes NOW - they won't be shown again!")
        print("   • Store them in a password manager or safe place")
        print("   • You'll need them if you lose your phone")

        print("\n📝 [bold]Next step:[/bold]")
        print("   Run: [cyan]cli auth mfa enable[/cyan]")
        print("   Enter the 6-digit code from your authenticator app")

    except requests.exceptions.HTTPError as e:
        if "already enabled" in str(e):
            print("❌ MFA is already enabled for your account")
            print(
                "💡 Use [cyan]cli auth mfa disable[/cyan] first if you want to reset it"
            )
        else:
            print(f"❌ MFA setup failed: {e}")
        raise typer.Exit(1) from None


@mfa_app.command("enable")
def mfa_enable():
    """Enable MFA by verifying a code from your authenticator app."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    print("\n🔐 [bold]Enable MFA[/bold]")
    print("Open your authenticator app and enter the 6-digit code:\n")

    code = typer.prompt("6-digit code")

    if len(code) != 6 or not code.isdigit():
        print("❌ Invalid code format. Must be 6 digits.")
        raise typer.Exit(1) from None

    try:
        client.mfa_verify(code)
        print("\n✅ [bold green]MFA enabled successfully![/bold green]")
        print("🔒 Your account is now protected with two-factor authentication")
        print("\n💡 Next time you login, you'll need:")
        print("   1. Your password")
        print("   2. A code from your authenticator app")

    except requests.exceptions.HTTPError as e:
        if "Invalid" in str(e):
            print("❌ Invalid code. Please try again.")
        else:
            print(f"❌ Failed to enable MFA: {e}")
        raise typer.Exit(1) from None


@mfa_app.command("disable")
def mfa_disable():
    """Disable MFA for your account."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    print("\n🔓 [bold]Disable MFA[/bold]")
    print("⚠️  This will remove two-factor authentication protection\n")

    if not confirm_action("Are you sure you want to disable MFA?"):
        print("Cancelled")
        return

    password = getpass("Enter your password to confirm: ")

    try:
        client.mfa_disable(password)
        print("\n✅ [bold]MFA disabled[/bold]")
        print("🔓 Two-factor authentication has been removed from your account")

    except requests.exceptions.HTTPError as e:
        if "Invalid password" in str(e):
            print("❌ Invalid password")
        else:
            print(f"❌ Failed to disable MFA: {e}")
        raise typer.Exit(1) from None


@mfa_app.command("backup-codes")
def mfa_backup_codes():
    """Regenerate MFA backup codes."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    print("\n🔑 [bold]Regenerate Backup Codes[/bold]")
    print("⚠️  This will invalidate your existing backup codes\n")

    if not confirm_action("Generate new backup codes?"):
        print("Cancelled")
        return

    try:
        result = client.mfa_regenerate_backup_codes()

        print("\n✅ [bold green]New backup codes generated![/bold green]")
        print("=" * 60)
        for i, code in enumerate(result["backup_codes"], 1):
            print(f"   {i:2}. {code}")
        print("=" * 60)

        print("\n⚠️  [bold red]IMPORTANT:[/bold red]")
        print("   • Save these codes in a safe place")
        print("   • Your old backup codes are now invalid")

    except requests.exceptions.HTTPError as e:
        if "not enabled" in str(e):
            print("❌ MFA is not enabled on your account")
            print("💡 Run [cyan]cli auth mfa setup[/cyan] first")
        else:
            print(f"❌ Failed to regenerate codes: {e}")
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
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    try:
        roles = client.list_roles()

        print("\n👥 [bold]Available Roles[/bold]")
        print("=" * 60)

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Name", style="green")
        table.add_column("Description")

        for role in roles:
            table.add_row(str(role["id"]), role["name"], role.get("description", ""))

        console.print(table)

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to list roles: {e}")
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
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    try:
        role = client.create_role(name, description)
        print(f"✅ [bold green]Role '{role['name']}' created[/bold green]")
        if role.get("description"):
            print(f"   Description: {role['description']}")

    except requests.exceptions.HTTPError as e:
        if "already exists" in str(e).lower():
            print(f"❌ Role '{name}' already exists")
        elif "403" in str(e) or "Forbidden" in str(e):
            print("❌ Permission denied - admin role required")
        else:
            print(f"❌ Failed to create role: {e}")
        raise typer.Exit(1) from None


@role_app.command("my-roles")
def my_roles():
    """Show your assigned roles."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    try:
        roles = client.get_my_roles()

        if not roles:
            print("\n📋 You have no roles assigned")
            print("💡 Contact an administrator to assign roles")
            return

        print("\n👤 [bold]Your Roles[/bold]")
        print("=" * 60)

        for role in roles:
            print(f"   • [green]{role['name']}[/green]")
            if role.get("description"):
                print(f"     [dim]{role['description']}[/dim]")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to get roles: {e}")
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
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    try:
        client.assign_role(user_id, role_name)
        print(
            f"✅ [bold green]Role '{role_name}' assigned to user {user_id}[/bold green]"
        )

    except requests.exceptions.HTTPError as e:
        if "403" in str(e) or "Forbidden" in str(e):
            print("❌ Permission denied - admin role required")
        elif "404" in str(e) or "not found" in str(e):
            print(f"❌ Role '{role_name}' not found")
        else:
            print(f"❌ Failed to assign role: {e}")
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
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    if not confirm_action(f"Remove role '{role_name}' from user {user_id}"):
        print("Cancelled")
        return

    try:
        client.remove_role(user_id, role_name)
        print(f"✅ [bold]Role '{role_name}' removed from user {user_id}[/bold]")

    except requests.exceptions.HTTPError as e:
        if "403" in str(e):
            print("❌ Permission denied - admin role required")
        else:
            print(f"❌ Failed to remove role: {e}")
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
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    try:
        result = client.create_oauth_client(
            client_name=name, redirect_uris=[redirect_uri]
        )

        print("\n✅ [bold green]OAuth2 Client Created![/bold green]")
        print("=" * 70)
        print(f"\n📱 Client Name: [bold]{result['client_name']}[/bold]")
        print("\n🆔 Client ID:")
        print(f"   [cyan]{result['client_id']}[/cyan]")
        print("\n🔑 Client Secret:")
        print(f"   [yellow]{result['client_secret']}[/yellow]")
        print("\n🔗 Redirect URIs:")
        for uri in result["redirect_uris"]:
            print(f"   • {uri}")

        print("\n" + "=" * 70)
        print("⚠️  [bold red]SAVE THE CLIENT SECRET NOW![/bold red]")
        print("   It will NOT be shown again!")
        print("=" * 70)

        # Try to copy client secret to clipboard
        try:
            import pyperclip

            pyperclip.copy(result["client_secret"])
            print("\n✅ Client secret copied to clipboard!")
        except (ImportError, Exception):
            print("\n💡 Copy the client secret manually")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to create OAuth2 client: {e}")
        raise typer.Exit(1) from None


@oauth_app.command("list")
def list_oauth_clients():
    """List your OAuth2 client applications."""
    client = APIClient()

    try:
        config.get_auth_headers()
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    try:
        clients = client.list_oauth_clients()

        if not clients:
            print("\n📋 No OAuth2 clients found")
            print("💡 Create one with: [cyan]cli oauth create[/cyan]")
            return

        print(f"\n🔐 [bold]Your OAuth2 Clients ({len(clients)})[/bold]")
        print("=" * 80)

        for oauth_client in clients:
            print(f"\n📱 [bold]{oauth_client['client_name']}[/bold]")
            print(f"   ID: [cyan]{oauth_client['client_id']}[/cyan]")
            print(f"   Grant Types: {oauth_client['grant_types']}")
            print(f"   Scopes: {oauth_client['scope']}")
            print("   Redirect URIs:")
            for uri in oauth_client["redirect_uris"]:
                print(f"      • {uri}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to list OAuth2 clients: {e}")
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
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from None

    print("\n⚠️  [bold]Delete OAuth2 Client[/bold]")
    print(f"Client ID: {client_id}")
    print("\nThis will:")
    print("   • Revoke all access tokens")
    print("   • Prevent new authorizations")
    print("   • This action cannot be undone")

    if not confirm_action("\nDelete this OAuth2 client?"):
        print("Cancelled")
        return

    try:
        client.delete_oauth_client(client_id)
        print("\n✅ [bold green]OAuth2 client deleted successfully[/bold green]")

    except requests.exceptions.HTTPError as e:
        if "404" in str(e) or "not found" in str(e):
            print(
                "❌ OAuth2 client not found or you don't have permission to delete it"
            )
        else:
            print(f"❌ Failed to delete OAuth2 client: {e}")
        raise typer.Exit(1) from None
