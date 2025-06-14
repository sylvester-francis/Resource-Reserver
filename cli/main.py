from datetime import UTC, datetime
from getpass import getpass
from pathlib import Path

import requests
import typer
from rich import print
from rich.console import Console
from rich.table import Table

from cli.client import APIClient
from cli.config import config
from cli.utils import (
    confirm_action,
    format_datetime,
    format_duration,
    parse_aware,
    parse_datetime,
    parse_duration,
    prompt_for_optional,
)

# Initialize CLI app and API client
app = typer.Typer(
    help="Resource Reservation System CLI - Professional interface for resource management",  # noqa : E501
    rich_markup_mode="rich",
)
client = APIClient()
console = Console()

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
        raise typer.Exit(1) from e


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
    except requests.exceptions.HTTPError as e:
        print("❌ Invalid username or password")
        raise typer.Exit(1) from e


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
            # Enhanced status display
            base_status = "🟢 Enabled" if resource["available"] else "🔴 Disabled"

            # Show detailed status if available
            if "status" in resource:
                status_icons = {
                    "available": "🟢",
                    "in_use": "🟡",
                    "unavailable": "🔴"
                }
                status_icon = status_icons.get(resource["status"], "❓")
                status_text = resource["status"].replace("_", " ").title()
                current_status = f"{status_icon} {status_text}"
            else:
                # Fallback to old logic
                current_status = (
                    "🟢 Available"
                    if resource.get("current_availability", resource["available"])
                    else "🔴 Unavailable"
                )

            print(f"[cyan]{resource['id']:3}[/cyan] │ [bold]{resource['name']}[/bold]")
            print(f"     │ Status: {current_status}")

            if show_details:
                print(f"     │ Base: {base_status}")
                if resource.get("tags"):
                    print(f"     │ Tags: {', '.join(resource['tags'])}")

            print()

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to fetch resources: {e}")
        raise typer.Exit(1) from e


@resource_app.command("search")
def search_resources(
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),  # noqa : E501
    available_from: str | None = typer.Option(
        None, "--from", help="Available from (YYYY-MM-DD HH:MM)"
    ),
    available_until: str | None = typer.Option(
        None, "--until", help="Available until (YYYY-MM-DD HH:MM)"
    ),
    available_only: bool = typer.Option(
        True, "--available-only/--all", help="Show only available resources"
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
            raise typer.Exit(1) from e

    try:
        resources = client.search_resources(query, start_time, end_time, available_only)  # noqa : E501

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
        raise typer.Exit(1) from e


@resource_app.command("availability")
def resource_availability(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to check ahead"),  # noqa : E501
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed schedule"),  # noqa : E501
):
    """Get availability schedule for a resource."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    try:
        availability = client.get_resource_availability(resource_id, days)

        print(f"\n📅 [bold]Availability for {availability['resource_name']}[/bold]")  # noqa : E501
        print(f"🆔 Resource ID: {availability['resource_id']}")
        print(
            f"🕐 Current time: {format_datetime(datetime.fromisoformat(availability['current_time'].replace('Z', '')))}"  # noqa : E501
        )

        current_status = (
            "🟢 Available"
            if availability["is_currently_available"]
            else "🔴 Unavailable"
        )
        print(f"📊 Current status: {current_status}")

        base_status = "🟢 Enabled" if availability["base_available"] else "🔴 Disabled"  # noqa : E501
        print(f"⚙️  Base setting: {base_status}")

        reservations = availability.get("reservations", [])
        if reservations:
            print(f"\n📋 [bold]Upcoming Reservations ({len(reservations)})[/bold]")  # noqa : E501
            print("─" * 60)

            for i, res in enumerate(reservations, 1):
                start = datetime.fromisoformat(res["start_time"].replace("Z", ""))  # noqa : E501
                end = datetime.fromisoformat(res["end_time"].replace("Z", ""))
                duration = format_duration(start, end)

                print(f"{i:2}. {format_datetime(start)} - {format_datetime(end)}")  # noqa : E501
                print(f"    Duration: {duration} | Status: {res['status']}")
                if detailed:
                    print(
                        f"    Reservation ID: {res['id']} | User ID: {res['user_id']}"  # noqa : E501
                    )
                print()
        else:
            print("\n🎉 No upcoming reservations - fully available!")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Resource not found")
        else:
            print(f"❌ Failed to get availability: {e}")
        raise typer.Exit(1) from e


@resource_app.command("enable")
def enable_resource(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),  # noqa : E501
):
    """Enable a resource (for maintenance mode)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    if not force:
        if not confirm_action(f"Enable resource {resource_id}?"):
            print("Operation cancelled")
            return

    try:
        result = client.update_resource_availability(resource_id, True)
        print(
            f"✅ [bold green]Resource {resource_id} enabled successfully[/bold green]"  # noqa : E501
        )
        print(f"🏢 Resource: {result['resource']['name']}")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Resource not found")
        else:
            print(f"❌ Failed to enable resource: {e}")
        raise typer.Exit(1) from e


@resource_app.command("disable")
def disable_resource(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),  # noqa : E501
):
    """Disable a resource (for maintenance mode)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    if not force:
        if not confirm_action(
            f"Disable resource {resource_id}? This will prevent new reservations."  # noqa : E501
        ):
            print("Operation cancelled")
            return

    try:
        result = client.update_resource_availability(resource_id, False)
        print(f"✅ [bold orange1]Resource {resource_id} disabled[/bold orange1]")  # noqa : E501
        print(f"🏢 Resource: {result['resource']['name']}")
        print("ℹ️  Resource is now in maintenance mode")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Resource not found")
        else:
            print(f"❌ Failed to disable resource: {e}")
        raise typer.Exit(1) from e


@resource_app.command("status")
def resource_status(
    resource_id: int = typer.Argument(..., help="Resource ID"),
):
    """Get detailed status information for a resource."""
    try:
        status_info = client.get_resource_status(resource_id)

        print(f"\n📊 [bold]Status for {status_info['resource_name']}[/bold]")
        print(f"🆔 Resource ID: {status_info['resource_id']}")
        current_time = datetime.fromisoformat(
            status_info['current_time'].replace('Z', '')
        )
        print(f"🕐 Current time: {format_datetime(current_time)}")

        # Base availability
        base_status = "🟢 Enabled" if status_info["base_available"] else "🔴 Disabled"
        print(f"⚙️  Base setting: {base_status}")

        # Current status
        status_icons = {
            "available": "🟢",
            "in_use": "🟡",
            "unavailable": "🔴"
        }
        status_icon = status_icons.get(status_info["status"], "❓")
        status_text = status_info["status"].replace("_", " ").title()
        print(f"📊 Current status: {status_icon} {status_text}")

        # Additional status info
        reservation_status = (
            "✅ Yes" if status_info['is_available_for_reservation'] else "❌ No"
        )
        print(f"🎯 Available for reservation: {reservation_status}")
        in_use_status = (
            "✅ Yes" if status_info['is_currently_in_use'] else "❌ No"
        )
        print(f"🔄 Currently in use: {in_use_status}")

        # Unavailable details
        if status_info["is_unavailable"] and "unavailable_since" in status_info:
            unavailable_since = format_datetime(
                datetime.fromisoformat(
                    status_info["unavailable_since"].replace("Z", "")
                )
            )
            print("\n🔧 [bold]Maintenance Details:[/bold]")
            print(f"📅 Unavailable since: {unavailable_since}")
            reset_hours = status_info['hours_until_auto_reset']
            print(f"⏰ Auto-reset in: {reset_hours:.1f} hours")
            config_hours = status_info['auto_reset_hours']
            print(f"⚙️  Auto-reset configured: {config_hours} hours")
            if status_info.get("will_auto_reset"):
                print("✅ Will automatically reset to available")
            else:
                print("⚠️  Auto-reset period has passed")

        # Current reservation info
        if "current_reservation" in status_info:
            res = status_info["current_reservation"]
            start = format_datetime(
                datetime.fromisoformat(res["start_time"].replace("Z", ""))
            )
            end = format_datetime(
                datetime.fromisoformat(res["end_time"].replace("Z", ""))
            )
            print("\n🎯 [bold]Current Reservation:[/bold]")
            print(f"📋 ID: {res['id']}")
            print(f"👤 User ID: {res['user_id']}")
            print(f"📅 Time: {start} to {end}")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Resource not found")
        else:
            print(f"❌ Failed to get resource status: {e}")
        raise typer.Exit(1) from e


@resource_app.command("maintenance")
def set_maintenance(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    auto_reset_hours: int = typer.Option(
        8, "--hours", "-h", help="Auto-reset after hours (1-168)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Set resource as unavailable for maintenance with auto-reset."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    if auto_reset_hours < 1 or auto_reset_hours > 168:
        print("❌ Auto-reset hours must be between 1 and 168 (1 week)")
        raise typer.Exit(1)

    if not force:
        if not confirm_action(
            f"Set resource {resource_id} to maintenance mode "
            f"(auto-reset in {auto_reset_hours} hours)?"
        ):
            print("Operation cancelled")
            return

    try:
        result = client.set_resource_unavailable(
            resource_id, auto_reset_hours
        )
        print(
            f"🔧 [bold orange1]Resource {resource_id} set to maintenance mode"
            "[/bold orange1]"
        )
        print(f"🏢 Resource: {result['resource']['name']}")
        print(f"⏰ Auto-reset in: {auto_reset_hours} hours")
        print("ℹ️  Resource is now unavailable for new reservations")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Resource not found")
        else:
            print(f"❌ Failed to set maintenance mode: {e}")
        raise typer.Exit(1) from e


@resource_app.command("reset")
def reset_resource(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Reset resource to available status (from any status)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    if not force:
        if not confirm_action(
            f"Reset resource {resource_id} to available status?"
        ):
            print("Operation cancelled")
            return

    try:
        result = client.reset_resource_to_available(resource_id)
        print(
            f"✅ [bold green]Resource {resource_id} reset to available"
            "[/bold green]"
        )
        print(f"🏢 Resource: {result['resource']['name']}")
        print("ℹ️  Resource is now available for reservations")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            print("❌ Resource not found")
        else:
            print(f"❌ Failed to reset resource: {e}")
        raise typer.Exit(1) from e


@resource_app.command("create")
def create_resource(
    name: str = typer.Argument(..., help="Resource name"),
    tags: str | None = typer.Option("", "--tags", "-t", help="Comma-separated tags"),  # noqa : E501
    available: bool = typer.Option(
        True, "--available/--unavailable", help="Resource availability"
    ),
):
    """Create a new resource."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []  # noqa : E501

    try:
        resource = client.create_resource(name, tag_list, available)
        print(f"✅ [bold green]Created resource:[/bold green] {resource['name']}")  # noqa : E501
        print(f"📋 ID: {resource['id']}")
        if tag_list:
            print(f"🏷️  Tags: {', '.join(tag_list)}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to create resource: {e}")
        raise typer.Exit(1) from e


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
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

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

            with open(csv_file) as f:
                reader = csv.DictReader(f)
                print(f"\n📄 [bold]Preview of {csv_file.name}:[/bold]")
                print("─" * 50)

                for i, row in enumerate(reader):
                    if i >= 5:  # Show first 5 rows
                        print("... (showing first 5 rows)")
                        break
                    print(f"Row {i + 1}: {dict(row)}")

                if not typer.confirm("\nProceed with upload?", default=True):
                    print("Upload cancelled")
                    return
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            raise typer.Exit(1) from e

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
        raise typer.Exit(1) from e


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

        # Show background task status if available
        if "background_tasks" in health:
            tasks = health["background_tasks"]
            for task_name, task_status in tasks.items():
                status_emoji = {
                    "running": "🟢",
                    "completed": "✅",
                    "failed": "❌",
                    "cancelled": "⏹️",
                    "not_started": "⏸️",
                }.get(task_status, "❓")
                print(f"🔧 {task_name}: {status_emoji} {task_status}")

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


@system_app.command("summary")
def availability_summary():
    """Get system-wide availability summary."""
    try:
        summary = client.get_availability_summary()

        print("\n📊 [bold]System Availability Summary[/bold]")
        print("═" * 50)

        # Create a nice table
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", style="yellow", justify="right")

        total = summary["total_resources"]
        available = summary["available_now"]
        unavailable = summary["unavailable_now"]
        in_use = summary["currently_in_use"]

        # Calculate percentages
        avail_pct = (available / total * 100) if total > 0 else 0
        unavail_pct = (unavailable / total * 100) if total > 0 else 0
        usage_pct = (in_use / total * 100) if total > 0 else 0

        table.add_row("Total Resources", str(total), "100%")
        table.add_row("Available Now", str(available), f"{avail_pct:.1f}%")
        table.add_row("Unavailable", str(unavailable), f"{unavail_pct:.1f}%")
        table.add_row("Currently In Use", str(in_use), f"{usage_pct:.1f}%")

        console.print(table)

        # Show timestamp
        timestamp = datetime.fromisoformat(summary["timestamp"].replace("Z", ""))  # noqa : E501
        print(f"\n🕐 Last updated: {format_datetime(timestamp)}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to get summary: {e}")
        raise typer.Exit(1) from e


@system_app.command("cleanup")
def manual_cleanup():
    """Manually trigger cleanup of expired reservations."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    if not confirm_action("Trigger manual cleanup of expired reservations?"):
        print("Cleanup cancelled")
        return

    try:
        result = client.manual_cleanup_expired()
        print("✅ [bold green]Cleanup completed![/bold green]")
        print(f"🧹 Cleaned up: {result['expired_count']} expired reservations")

        if result["expired_count"] == 0:
            print("🎉 No expired reservations found - system is clean!")

        timestamp = datetime.fromisoformat(result["timestamp"].replace("Z", ""))  # noqa : E501
        print(f"🕐 Completed at: {format_datetime(timestamp)}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Cleanup failed: {e}")
        raise typer.Exit(1) from e


@system_app.command("config")
def show_config():
    """Show current configuration."""
    print("⚙️  [bold]Current Configuration[/bold]")
    print("─" * 40)
    print(f"API URL: {config.api_url}")
    print(f"Config Directory: {config.config_dir}")
    print(f"Token File: {config.token_file}")
    print(f"Authenticated: {'Yes' if config.load_token() else 'No'}")


# Reservation commands (keeping existing ones but adding new features)
reservation_app = typer.Typer(help="Reservation management commands")
app.add_typer(reservation_app, name="reservations")


@reservation_app.command("create")
def create_reservation(
    resource_id: int = typer.Argument(..., help="Resource ID to reserve"),
    start: str = typer.Argument(..., help="Start time (YYYY-MM-DD HH:MM)"),
    end: str | None = typer.Argument(
        None, help="End time (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)"
    ),
):
    """Create a new reservation."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

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
                except ValueError as e:
                    print(
                        "❌ End time must be a datetime (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)"  # noqa : E501
                    )
                    raise typer.Exit(1) from e
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
                except ValueError as e:
                    print("❌ Invalid end time or duration format")
                    raise typer.Exit(1) from e

        if end_time <= start_time:
            print("❌ End time must be after start time")
            raise typer.Exit(1)

    except ValueError as e:
        print(f"❌ {e}")
        raise typer.Exit(1) from e

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
        raise typer.Exit(1) from e


@reservation_app.command("list")
def list_my_reservations(
    include_cancelled: bool = typer.Option(
        False,
        "--include-cancelled",
        "-c",
        help="Include cancelled reservations",
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
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    try:
        reservations = client.get_my_reservations(include_cancelled)

        if not reservations:
            print("📅 No reservations found")
            print("💡 Create one with: [cyan]cli reservations create[/cyan]")
            return

        # Filter upcoming if requested
        if upcoming_only:
            now = datetime.now(UTC)
            reservations = [
                r for r in reservations if parse_aware(r["start_time"]) > now
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
        raise typer.Exit(1) from e


@reservation_app.command("cancel")
def cancel_reservation(
    reservation_id: int = typer.Argument(..., help="Reservation ID to cancel"),
    reason: str | None = typer.Option(
        None, "--reason", "-r", help="Cancellation reason"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),  # noqa : E501
):
    """Cancel a reservation."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

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
        result = client.cancel_reservation(reservation_id, reason)  # noqa : F841
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
        raise typer.Exit(1) from e


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
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

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
        raise typer.Exit(1) from e


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
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    try:
        start_time = parse_datetime(start)
        duration_delta = parse_duration(duration)
        end_time = start_time + duration_delta

    except ValueError as e:
        print(f"❌ {e}")
        raise typer.Exit(1) from e

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
        raise typer.Exit(1) from e


@app.command("upcoming")
def show_upcoming_reservations():
    """Show upcoming reservations (shortcut)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        print("❌ Please login first: [cyan]cli auth login[/cyan]")
        raise typer.Exit(1) from e

    try:
        reservations = client.get_my_reservations()
        now = datetime.now(UTC)

        # Filter to upcoming active reservations
        upcoming = [
            r
            for r in reservations
            if r["status"] == "active" and parse_aware(r["start_time"]) > now
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
            start_dt = datetime.fromisoformat(reservation["start_time"]).replace(  # noqa : E501
                tzinfo=UTC
            )
            end_dt = datetime.fromisoformat(reservation["end_time"]).replace(tzinfo=UTC)

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
        raise typer.Exit(1) from e


# Main entry point
if __name__ == "__main__":
    app()
