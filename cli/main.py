import typer
import requests
from rich import print

from typing import Optional
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path

from cli.client import APIClient
from cli.config import config
from cli.utils import (
    parse_datetime,
    parse_duration,
    format_datetime,
    format_duration,
    confirm_action,
    prompt_for_optional,
)

# Initialize CLI app and API client
app = typer.Typer(
    help="Resource Reservation System CLI - Professional interface for resource management",  # noqa : E501
    rich_markup_mode="rich",
)
client = APIClient()


# Authentication commands
auth_app = typer.Typer(help="Authentication commands")
app.add_typer(auth_app, name="auth")


@auth_app.command("register")
def register():
    """Register a new user account."""
    print("🔐 Create a new account")
    username = typer.prompt("Username")

    while True:
        password = getpass("Password: ")
        confirm_password = getpass("Confirm password: ")

        if password == confirm_password:
            break
        print("❌ Passwords do not match. Please try again.")

    try:
        user = client.register(username, password)
        print(
            f"✅ Successfully registered user: [bold green]{user['username']}[/bold green]"  # noqa : E501
        )
        print("💡 You can now login with: [cyan]cli auth login[/cyan]")
    except requests.exceptions.HTTPError as e:
        if "already" in str(e).lower():
            print("❌ Username already exists. Please choose a different username.")  # noqa : E501
        else:
            print(f"❌ Registration failed: {e}")
        raise typer.Exit(1)


@auth_app.command("login")
def login():
    """Login to your account."""
    print("🔑 Login to your account")
    username = typer.prompt("Username")
    password = getpass("Password: ")

    try:
        token = client.login(username, password)
        config.save_token(token)
        print(f"✅ Welcome back, [bold green]{username}[/bold green]!")
    except requests.exceptions.HTTPError:
        print("❌ Invalid username or password")
        raise typer.Exit(1)


@auth_app.command("logout")
def logout():
    """Logout from your account."""
    config.clear_token()
    print("👋 Successfully logged out")


@auth_app.command("status")
def auth_status():
    """Check authentication status."""
    token = config.load_token()
    if token:
        print("✅ You are logged in")
        try:
            # Test the token by making a request
            client.get_my_reservations()
            print("🔗 Connection to API: [green]OK[/green]")
        except Exception:
            print("⚠️  Token may be expired. Please login again.")
    else:
        print("❌ You are not logged in")
        print("💡 Use [cyan]cli auth login[/cyan] to sign in")


# Resource commands
resource_app = typer.Typer(help="Resource management commands")
app.add_typer(resource_app, name="resources")


@resource_app.command("list")
def list_resources(
    show_details: bool = typer.Option(
        False, "--details", "-d", help="Show detailed information"
    ),
):
    """List all available resources."""
    try:
        resources = client.list_resources()

        if not resources:
            print("📦 No resources found")
            return

        print(f"\n📦 [bold]Resources ({len(resources)} total)[/bold]")
        print("─" * 50)

        for resource in resources:
            status = "🟢 Available" if resource["available"] else "🔴 Unavailable"  # noqa : E501
            print(f"[cyan]{resource['id']:3}[/cyan] │ [bold]{resource['name']}[/bold]")  # noqa : E501
            print(f"     │ {status}")

            if show_details and resource.get("tags"):
                print(f"     │ Tags: {', '.join(resource['tags'])}")

            print()

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to fetch resources: {e}")
        raise typer.Exit(1)


@resource_app.command("search")
def search_resources(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),  # noqa : E501
    available_from: Optional[str] = typer.Option(
        None, "--from", help="Available from (YYYY-MM-DD HH:MM)"
    ),
    available_until: Optional[str] = typer.Option(
        None, "--until", help="Available until (YYYY-MM-DD HH:MM)"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive mode"
    ),
):
    """Search for resources with advanced filtering."""

    # Interactive mode
    if interactive:
        print("🔍 [bold]Interactive Resource Search[/bold]")
        query = prompt_for_optional("Search query (press Enter to skip)")

        if typer.confirm("Check availability for specific time period?", default=False):  # noqa : E501
            available_from = typer.prompt("Available from (YYYY-MM-DD HH:MM)")
            available_until = typer.prompt("Available until (YYYY-MM-DD HH:MM)")  # noqa : E501

    # Parse datetime inputs
    start_time = None
    end_time = None

    if available_from or available_until:
        if not (available_from and available_until):
            print("❌ Both --from and --until must be specified for time filtering")  # noqa : E501
            raise typer.Exit(1)

        try:
            start_time = parse_datetime(available_from)
            end_time = parse_datetime(available_until)

            if end_time <= start_time:
                print("❌ End time must be after start time")
                raise typer.Exit(1)

        except ValueError as e:
            print(f"❌ {e}")
            raise typer.Exit(1)

    try:
        resources = client.search_resources(query, start_time, end_time)

        if not resources:
            if start_time and end_time:
                print(
                    f"😞 No resources available from {format_datetime(start_time)} to {format_datetime(end_time)}"  # noqa : E501
                )
            else:
                print("😞 No resources found matching your search")
            return

        # Display results
        if start_time and end_time:
            duration = format_duration(start_time, end_time)
            print(f"\n✅ [bold]Found {len(resources)} resources available[/bold]")  # noqa : E501
            print(
                f"📅 Time: {format_datetime(start_time)} to {format_datetime(end_time)} ({duration})"  # noqa : E501
            )
        else:
            print(f"\n🔍 [bold]Found {len(resources)} resources[/bold]")

        print("─" * 60)

        for resource in resources:
            print(f"[cyan]{resource['id']:3}[/cyan] │ [bold]{resource['name']}[/bold]")  # noqa : E501
            if resource.get("tags"):
                print(f"     │ Tags: {', '.join(resource['tags'])}")
            print()

        # Offer to make a reservation if time period was specified
        if start_time and end_time and resources:
            if typer.confirm("Would you like to make a reservation?", default=False):  # noqa : E501
                resource_id = typer.prompt("Enter resource ID", type=int)

                # Validate resource ID
                if resource_id not in [r["id"] for r in resources]:
                    print("❌ Invalid resource ID")
                    return

                try:
                    reservation = client.create_reservation(
                        resource_id, start_time, end_time
                    )
                    selected_resource = next(
                        r for r in resources if r["id"] == resource_id
                    )

                    print("🎉 [bold green]Reservation created![/bold green]")
                    print(f"📋 ID: {reservation['id']}")
                    print(f"🏢 Resource: {selected_resource['name']}")
                    print(
                        f"📅 Time: {format_datetime(start_time)} to {format_datetime(end_time)}"  # noqa : E501
                    )

                except requests.exceptions.HTTPError as e:
                    print(f"❌ Failed to create reservation: {e}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Search failed: {e}")
        raise typer.Exit(1)


@resource_app.command("create")
def create_resource(
    name: str = typer.Argument(..., help="Resource name"),
    tags: Optional[str] = typer.Option("", "--tags", "-t", help="Comma-separated tags"),  # noqa : E501
    available: bool = typer.Option(
        True, "--available/--unavailable", help="Resource availability"
    ),
):
    """Create a new resource."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []  # noqa : E501

    try:
        resource = client.create_resource(name, tag_list, available)
        print(f"✅ [bold green]Created resource:[/bold green] {resource['name']}")  # noqa : E501
        print(f"📋 ID: {resource['id']}")
        if tag_list:
            print(f"🏷️  Tags: {', '.join(tag_list)}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to create resource: {e}")
        raise typer.Exit(1)


@resource_app.command("upload")
def upload_resources(
    file_path: str = typer.Argument(..., help="Path to CSV file"),
    preview: bool = typer.Option(
        False, "--preview", "-p", help="Preview file contents before upload"
    ),
):
    """Upload resources from a CSV file."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    # Validate file exists
    csv_file = Path(file_path)
    if not csv_file.exists():
        print(f"❌ File not found: {file_path}")
        raise typer.Exit(1)

    if not csv_file.suffix.lower() == ".csv":
        print("❌ File must be a CSV file")
        raise typer.Exit(1)

    # Preview option
    if preview:
        try:
            import csv

            with open(csv_file, "r") as f:
                reader = csv.DictReader(f)
                print(f"\n📄 [bold]Preview of {csv_file.name}:[/bold]")
                print("─" * 50)

                for i, row in enumerate(reader):
                    if i >= 5:  # Show first 5 rows
                        print("... (showing first 5 rows)")
                        break
                    print(f"Row {i+1}: {dict(row)}")

                if not typer.confirm("\nProceed with upload?", default=True):
                    print("Upload cancelled")
                    return
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            raise typer.Exit(1)

    try:
        print(f"📤 Uploading {csv_file.name}...")
        result = client.upload_resources_csv(str(csv_file))

        print("✅ [bold green]Upload completed![/bold green]")
        print(f"📊 Created: {result['created_count']} resources")

        if "errors" in result and result["errors"]:
            print(f"⚠️  Errors: {len(result['errors'])}")
            for error in result["errors"][:3]:  # Show first 3 errors
                print(f"   • {error}")
            if len(result["errors"]) > 3:
                print(f"   ... and {len(result['errors']) - 3} more")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Upload failed: {e}")
        raise typer.Exit(1)


# Reservation commands
reservation_app = typer.Typer(help="Reservation management commands")
app.add_typer(reservation_app, name="reservations")


@reservation_app.command("create")
def create_reservation(
    resource_id: int = typer.Argument(..., help="Resource ID to reserve"),
    start: str = typer.Argument(..., help="Start time (YYYY-MM-DD HH:MM)"),
    end: Optional[str] = typer.Argument(
        None, help="End time (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)"
    ),
):
    """Create a new reservation."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    try:
        start_time = parse_datetime(start)

        # Handle end time or duration
        if end:
            try:
                # Try parsing as datetime first
                end_time = parse_datetime(end)
            except ValueError:
                # Try parsing as duration
                try:
                    duration = parse_duration(end)
                    end_time = start_time + duration
                except ValueError:
                    print(
                        "❌ End time must be a datetime (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)"  # noqa : E501
                    )
                    raise typer.Exit(1)
        else:
            # Prompt for end time
            end_input = typer.prompt(
                "End time (YYYY-MM-DD HH:MM) or duration (e.g., 2h)"
            )
            try:
                end_time = parse_datetime(end_input)
            except ValueError:
                try:
                    duration = parse_duration(end_input)
                    end_time = start_time + duration
                except ValueError:
                    print("❌ Invalid end time or duration format")
                    raise typer.Exit(1)

        if end_time <= start_time:
            print("❌ End time must be after start time")
            raise typer.Exit(1)

    except ValueError as e:
        print(f"❌ {e}")
        raise typer.Exit(1)

    try:
        reservation = client.create_reservation(resource_id, start_time, end_time)  # noqa : E501
        duration = format_duration(start_time, end_time)

        print("🎉 [bold green]Reservation created successfully![/bold green]")
        print(f"📋 ID: {reservation['id']}")
        print(f"🏢 Resource: {reservation['resource']['name']}")
        print(f"📅 Time: {format_datetime(start_time)} to {format_datetime(end_time)}")  # noqa : E501
        print(f"⏱️  Duration: {duration}")

    except requests.exceptions.HTTPError as e:
        if "conflicts" in str(e).lower():
            print("❌ [red]Time slot conflicts with existing reservation[/red]")
            print(
                "💡 Use [cyan]cli resources search --from 'START' --until 'END'[/cyan] to find available times"  # noqa : E501
            )
        elif "not found" in str(e).lower():
            print("❌ Resource not found")
            print("💡 Use [cyan]cli resources list[/cyan] to see available resources")  # noqa : E501
        else:
            print(f"❌ Failed to create reservation: {e}")
        raise typer.Exit(1)


@reservation_app.command("list")
def list_my_reservations(
    include_cancelled: bool = typer.Option(
        False,
        "--include-cancelled",
        "-c",
        help="Include cancelled reservations",  # noqa : E501
    ),
    upcoming_only: bool = typer.Option(
        False, "--upcoming", "-u", help="Show only upcoming reservations"
    ),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed information"
    ),
):
    """List your reservations."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    try:
        reservations = client.get_my_reservations(include_cancelled)

        if not reservations:
            print("📅 No reservations found")
            print("💡 Create one with: [cyan]cli reservations create[/cyan]")
            return

        # Filter upcoming if requested
        if upcoming_only:
            now = datetime.now(timezone.utc)
            reservations = [
                r
                for r in reservations
                if datetime.fromisoformat(r["start_time"].replace("Z", "")) > now  # noqa : E501
            ]

        if not reservations:
            print("📅 No upcoming reservations found")
            return

        # Group by status
        active_reservations = [r for r in reservations if r["status"] == "active"]  # noqa : E501
        cancelled_reservations = [r for r in reservations if r["status"] == "cancelled"]  # noqa : E501

        print(f"\n📅 [bold]Your Reservations ({len(reservations)} total)[/bold]")  # noqa : E501
        print("═" * 60)

        # Show active reservations
        if active_reservations:
            print(f"\n✅ [bold green]Active ({len(active_reservations)})[/bold green]")  # noqa : E501
            print("─" * 40)

            for reservation in active_reservations:
                start = format_datetime(
                    datetime.fromisoformat(reservation["start_time"].replace("Z", ""))  # noqa : E501
                )
                end = format_datetime(
                    datetime.fromisoformat(reservation["end_time"].replace("Z", ""))  # noqa : E501
                )
                duration = format_duration(
                    datetime.fromisoformat(reservation["start_time"].replace("Z", "")),  # noqa : E501
                    datetime.fromisoformat(reservation["end_time"].replace("Z", "")),  # noqa : E501
                )

                print(
                    f"[cyan]{reservation['id']:3}[/cyan] │ [bold]{reservation['resource']['name']}[/bold]"  # noqa : E501
                )
                print(f"     │ {start} to {end} ({duration})")

                if detailed:
                    created = format_datetime(
                        datetime.fromisoformat(
                            reservation["created_at"].replace("Z", "")
                        )
                    )
                    print(f"     │ Created: {created}")

                print()

        # Show cancelled reservations if requested
        if include_cancelled and cancelled_reservations:
            print(
                f"\n❌ [bold red]Cancelled ({len(cancelled_reservations)})[/bold red]"  # noqa : E501
            )
            print("─" * 40)

            for reservation in cancelled_reservations:
                start = format_datetime(
                    datetime.fromisoformat(reservation["start_time"].replace("Z", ""))  # noqa : E501
                )
                end = format_datetime(
                    datetime.fromisoformat(reservation["end_time"].replace("Z", ""))  # noqa : E501
                )

                print(
                    f"[cyan]{reservation['id']:3}[/cyan] │ [dim]{reservation['resource']['name']}[/dim]"  # noqa : E501
                )
                print(f"     │ [dim]{start} to {end}[/dim]")

                if reservation.get("cancellation_reason"):
                    print(f"     │ Reason: {reservation['cancellation_reason']}")  # noqa : E501

                if detailed and reservation.get("cancelled_at"):
                    cancelled = format_datetime(
                        datetime.fromisoformat(
                            reservation["cancelled_at"].replace("Z", "")
                        )
                    )
                    print(f"     │ Cancelled: {cancelled}")

                print()

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to fetch reservations: {e}")
        raise typer.Exit(1)


@reservation_app.command("cancel")
def cancel_reservation(
    reservation_id: int = typer.Argument(..., help="Reservation ID to cancel"),
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r", help="Cancellation reason"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),  # noqa : E501
):
    """Cancel a reservation."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    # Get reservation details first for confirmation
    try:
        reservations = client.get_my_reservations()
        reservation = next((r for r in reservations if r["id"] == reservation_id), None)  # noqa : E501

        if not reservation:
            print(f"❌ Reservation {reservation_id} not found or not owned by you")  # noqa : E501
            raise typer.Exit(1)

        if reservation["status"] == "cancelled":
            print(f"❌ Reservation {reservation_id} is already cancelled")
            raise typer.Exit(1)

    except requests.exceptions.HTTPError:
        # If we can't fetch details, proceed anyway (the API will handle validation) # noqa : E501
        reservation = None

    # Show confirmation with details if available
    if not force:
        if reservation:
            start = format_datetime(
                datetime.fromisoformat(reservation["start_time"].replace("Z", ""))  # noqa : E501
            )
            end = format_datetime(
                datetime.fromisoformat(reservation["end_time"].replace("Z", ""))  # noqa : E501
            )

            print("\n📋 [bold]Reservation Details:[/bold]")
            print(f"ID: {reservation_id}")
            print(f"Resource: {reservation['resource']['name']}")
            print(f"Time: {start} to {end}")
            print()

        if not confirm_action(f"Cancel reservation {reservation_id}?"):
            print("Cancellation aborted")
            return

    # Prompt for reason if not provided
    if not reason:
        reason = prompt_for_optional("Cancellation reason (optional)")

    try:
        result = client.cancel_reservation(reservation_id, reason)  # noqa : F481
        print(
            f"✅ [bold green]Reservation {reservation_id} cancelled successfully[/bold green]"  # noqa : E501
        )

        if reason:
            print(f"📝 Reason: {reason}")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Reservation not found")
        elif "only cancel your own" in str(e).lower():
            print("❌ You can only cancel your own reservations")
        elif "already cancelled" in str(e).lower():
            print("❌ Reservation is already cancelled")
        else:
            print(f"❌ Failed to cancel reservation: {e}")
        raise typer.Exit(1)


@reservation_app.command("history")
def show_reservation_history(
    reservation_id: int = typer.Argument(..., help="Reservation ID"),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed history"
    ),
):
    """Show history for a reservation."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    try:
        history = client.get_reservation_history(reservation_id)

        if not history:
            print(f"📋 No history found for reservation {reservation_id}")
            return

        print(f"\n📋 [bold]History for Reservation {reservation_id}[/bold]")
        print("═" * 60)

        for i, entry in enumerate(history):
            timestamp = format_datetime(
                datetime.fromisoformat(entry["timestamp"].replace("Z", ""))
            )
            action = entry["action"].title()
            details = entry.get("details", "")

            # Color code actions
            if entry["action"] == "created":
                action_colored = f"[green]✅ {action}[/green]"
            elif entry["action"] == "cancelled":
                action_colored = f"[red]❌ {action}[/red]"
            elif entry["action"] == "updated":
                action_colored = f"[yellow]📝 {action}[/yellow]"
            else:
                action_colored = f"[blue]📋 {action}[/blue]"

            print(f"{timestamp} │ {action_colored}")
            if details:
                print(f"{'':19} │ {details}")

            if i < len(history) - 1:  # Don't add separator after last entry
                print(f"{'':19} │")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Reservation not found")
        elif "access denied" in str(e).lower():
            print(
                "❌ Access denied - you can only view history for your own reservations"  # noqa : E501
            )
        else:
            print(f"❌ Failed to fetch history: {e}")
        raise typer.Exit(1)


# System commands
system_app = typer.Typer(help="System and utility commands")
app.add_typer(system_app, name="system")


@system_app.command("status")
def system_status():
    """Check system status and connectivity."""
    print("🔍 [bold]System Status Check[/bold]")
    print("─" * 40)

    # Check API connectivity
    try:
        health = client.health_check()
        print("🌐 API Connection: [green]✅ OK[/green]")
        print(f"📊 API Status: {health.get('status', 'unknown')}")

        if "timestamp" in health:
            api_time = datetime.fromisoformat(health["timestamp"].replace("Z", ""))  # noqa : E501
            print(f"🕐 API Time: {format_datetime(api_time)}")

    except requests.exceptions.HTTPError as e:
        print("🌐 API Connection: [red]❌ Failed[/red]")
        print(f"   Error: {e}")
        return
    except Exception as e:
        print("🌐 API Connection: [red]❌ Error[/red]")
        print(f"   Error: {e}")
        return

    # Check authentication
    token = config.load_token()
    if token:
        try:
            client.get_my_reservations()
            print("🔐 Authentication: [green]✅ Valid[/green]")
        except requests.exceptions.HTTPError:
            print("🔐 Authentication: [yellow]⚠️ Token expired[/yellow]")
            print("   Use: [cyan]cli auth login[/cyan]")
        except Exception:
            print("🔐 Authentication: [red]❌ Error[/red]")
    else:
        print("🔐 Authentication: [red]❌ Not logged in[/red]")
        print("   Use: [cyan]cli auth login[/cyan]")

    # Check configuration
    print(f"⚙️  API URL: {config.api_url}")
    print(f"📁 Config Dir: {config.config_dir}")


@system_app.command("config")
def show_config():
    """Show current configuration."""
    print("⚙️  [bold]Current Configuration[/bold]")
    print("─" * 40)
    print(f"API URL: {config.api_url}")
    print(f"Config Directory: {config.config_dir}")
    print(f"Token File: {config.token_file}")
    print(f"Authenticated: {'Yes' if config.load_token() else 'No'}")


# Quick action commands (shortcuts)
@app.command("reserve")
def quick_reserve(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    start: str = typer.Argument(..., help="Start time (YYYY-MM-DD HH:MM)"),
    duration: str = typer.Argument(..., help="Duration (e.g., 2h, 30m, 1h30m)"),  # noqa : E501
):
    """Quick reserve command (shortcut for reservations create with duration)."""  # noqa : E501
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    try:
        start_time = parse_datetime(start)
        duration_delta = parse_duration(duration)
        end_time = start_time + duration_delta

    except ValueError as e:
        print(f"❌ {e}")
        raise typer.Exit(1)

    try:
        reservation = client.create_reservation(resource_id, start_time, end_time)  # noqa : E501

        print("🎉 [bold green]Quick reservation created![/bold green]")
        print(f"📋 ID: {reservation['id']}")
        print(f"🏢 Resource: {reservation['resource']['name']}")
        print(f"📅 Time: {format_datetime(start_time)} to {format_datetime(end_time)}")  # noqa : E501
        print(f"⏱️  Duration: {duration}")

    except requests.exceptions.HTTPError as e:
        if "conflicts" in str(e).lower():
            print("❌ [red]Time slot conflicts with existing reservation[/red]")
        else:
            print(f"❌ Failed to create reservation: {e}")
        raise typer.Exit(1)


@app.command("find")
def find_and_reserve(
    duration: str = typer.Argument(..., help="Duration needed (e.g., 2h, 30m)"),  # noqa : E501
    query: Optional[str] = typer.Option(
        None, "--query", "-q", help="Resource search query"
    ),
    start_from: Optional[str] = typer.Option(
        None, "--from", help="Earliest start time (YYYY-MM-DD HH:MM)"
    ),
):
    """Find available resources and make a reservation interactively."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    try:
        duration_delta = parse_duration(duration)
    except ValueError as e:
        print(f"❌ {e}")
        raise typer.Exit(1)

    # Get start time
    if start_from:
        try:
            start_time = parse_datetime(start_from)
        except ValueError as e:
            print(f"❌ {e}")
            raise typer.Exit(1)
    else:
        start_input = typer.prompt("When would you like to start? (YYYY-MM-DD HH:MM)")  # noqa : E501
        try:
            start_time = parse_datetime(start_input)
        except ValueError as e:
            print(f"❌ {e}")
            raise typer.Exit(1)

    end_time = start_time + duration_delta

    # Search for available resources
    print(f"\n🔍 Searching for resources available for {duration}...")
    print(f"📅 Time slot: {format_datetime(start_time)} to {format_datetime(end_time)}")  # noqa : E501

    try:
        resources = client.search_resources(query, start_time, end_time)

        if not resources:
            print("😞 No resources available for that time slot")
            print("💡 Try a different time or shorter duration")
            return

        print(f"\n✅ Found {len(resources)} available resources:")
        print("─" * 50)

        for i, resource in enumerate(resources, 1):
            print(f"[cyan]{i:2}[/cyan]. {resource['name']} (ID: {resource['id']})")  # noqa : E501
            if resource.get("tags"):
                print(f"     Tags: {', '.join(resource['tags'])}")

        print()

        # Let user choose
        while True:
            try:
                choice = typer.prompt("Select a resource (number)", type=int)
                if 1 <= choice <= len(resources):
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(resources)}")  # noqa : E501
            except typer.Abort:
                print("Selection cancelled")
                return

        selected_resource = resources[choice - 1]

        # Confirm reservation
        print("\n📋 [bold]Reservation Summary:[/bold]")
        print(f"Resource: {selected_resource['name']}")
        print(f"Time: {format_datetime(start_time)} to {format_datetime(end_time)}")  # noqa : E501
        print(f"Duration: {duration}")
        print()

        if not confirm_action("Create this reservation?", default=True):
            print("Reservation cancelled")
            return

        # Create reservation
        reservation = client.create_reservation(
            selected_resource["id"], start_time, end_time
        )

        print("\n🎉 [bold green]Reservation created successfully![/bold green]")
        print(f"📋 Reservation ID: {reservation['id']}")
        print(f"🏢 Resource: {reservation['resource']['name']}")
        print(f"📅 Time: {format_datetime(start_time)} to {format_datetime(end_time)}")  # noqa : E501

    except requests.exceptions.HTTPError as e:
        print(f"❌ Search failed: {e}")
        raise typer.Exit(1)


@app.command("upcoming")
def show_upcoming_reservations():
    """Show upcoming reservations (shortcut)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1)

    try:
        reservations = client.get_my_reservations()
        now = datetime.now(timezone.utc)

        # Filter to upcoming active reservations
        upcoming = [
            r
            for r in reservations
            if r["status"] == "active"
            and datetime.fromisoformat(r["start_time"].replace("Z", "")) > now
        ]

        if not upcoming:
            print("📅 No upcoming reservations")
            print(
                "💡 Create one with: [cyan]cli reserve[/cyan] or [cyan]cli find[/cyan]"  # noqa : E501
            )
            return

        # Sort by start time
        upcoming.sort(key=lambda r: r["start_time"])

        print(f"\n📅 [bold]Upcoming Reservations ({len(upcoming)})[/bold]")
        print("═" * 60)

        for reservation in upcoming:
            start_dt = datetime.fromisoformat(
                reservation["start_time"].replace("Z", "")
            )
            end_dt = datetime.fromisoformat(reservation["end_time"].replace("Z", ""))  # noqa : E501

            # Calculate time until start
            time_until = start_dt - now
            if time_until.days > 0:
                time_str = f"in {time_until.days} days"
            elif time_until.seconds > 3600:
                hours = time_until.seconds // 3600
                time_str = f"in {hours} hours"
            else:
                minutes = time_until.seconds // 60
                time_str = f"in {minutes} minutes"

            duration = format_duration(start_dt, end_dt)

            print(
                f"[cyan]{reservation['id']:3}[/cyan] │ [bold]{reservation['resource']['name']}[/bold]"  # noqa : E501
            )
            print(f"     │ {format_datetime(start_dt)} ({time_str})")
            print(f"     │ Duration: {duration}")
            print()

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to fetch reservations: {e}")
        raise typer.Exit(1)


# Main entry point
if __name__ == "__main__":
    app()
