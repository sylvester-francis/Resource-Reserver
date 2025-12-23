from datetime import UTC, datetime
from getpass import getpass
from pathlib import Path

import requests
import typer

from cli.auth_commands import mfa_app, oauth_app, role_app
from cli.client import (
    APIClient,
    is_lockout_error,
    is_password_policy_error,
    parse_lockout_time,
)
from cli.config import config
from cli.setup_commands import setup_app
from cli.ui import console, error, hint, info, render_table, section, success, warning
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
    help="Resource Reservation System CLI - Professional interface for resource management",
    rich_markup_mode="rich",
)
client = APIClient()

# Authentication commands
auth_app = typer.Typer(help="Authentication commands")
app.add_typer(auth_app, name="auth")

# Add new auth feature command groups
app.add_typer(mfa_app, name="mfa")
app.add_typer(role_app, name="roles")
app.add_typer(oauth_app, name="oauth")
app.add_typer(setup_app, name="setup")


@app.command("commands")
def list_commands():
    """List available CLI commands and key options."""
    section("Resource Reserver Commands")

    # Top-level groups
    groups = [
        ("auth", "Authentication (register, login, logout, status, refresh)"),
        (
            "resources",
            "Resource management (list, search, availability, status, enable/disable, maintenance, upload)",
        ),
        ("reservations", "Reservation management (create, list, cancel, history)"),
        ("waitlist", "Waitlist management (join, list, status, accept, leave)"),
        ("system", "System utilities (status, summary, cleanup, config)"),
        ("mfa", "MFA setup and backup code management"),
        ("roles", "Role administration"),
        ("oauth", "OAuth client management"),
        ("setup", "Local CLI setup utilities"),
        ("reserve", "Shortcut for reservations create with duration"),
        ("upcoming", "Shortcut to list upcoming reservations"),
    ]

    render_table(["Command", "Description"], groups, title="Top-level")

    hint("Common list commands and their options:")

    list_options = [
        (
            "resources list",
            "--details/-d, --limit/-l, --cursor/-c, --all, --sort/-s, --order/-o",
        ),
        (
            "reservations list",
            "--upcoming/-u, --include-cancelled/-c, --detailed/-d, "
            "--limit/-l, --cursor, --all, --sort/-s, --order/-o",
        ),
        (
            "waitlist list",
            "--include-completed/-c, --limit/-l, --cursor, --sort/-s, --order/-o",
        ),
    ]

    render_table(["Command", "Options"], list_options, title="List Commands")
    hint("Run `cli <command> --help` for full details.")


@auth_app.command("register")
def register():
    """Register a new user account."""
    section("Create a new account")
    username = typer.prompt("Username")

    while True:
        password = getpass("Password: ")
        confirm_password = getpass("Confirm password: ")

        if password == confirm_password:
            break
        warning("Passwords do not match. Please try again.")

    try:
        user = client.register(username, password)
        success(f"Successfully registered user {user['username']}")
        hint("Next: run `cli auth login` to sign in.")
    except requests.exceptions.ConnectionError as exc:
        error("Unable to reach the API. Is the server running?")
        hint(f"Tried: {config.api_url}")
        raise typer.Exit(1) from exc
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if "already" in error_msg.lower():
            error("Username already exists. Please choose a different username.")
        elif is_password_policy_error(error_msg):
            error("Password does not meet requirements:")
            # Split on semicolon to show each requirement
            for msg in error_msg.split(";"):
                msg = msg.strip()
                if msg:
                    hint(f"- {msg}")
            hint("Expected: 8+ chars, upper/lower, digit, special character.")
        else:
            error(f"Registration failed: {e}")
        raise typer.Exit(1) from e


@auth_app.command("login")
def login():
    """Login to your account."""
    section("Login to your account")
    username = typer.prompt("Username")
    password = getpass("Password: ")

    try:
        token_data = client.login(username, password)
        # Save both access token and refresh token
        config.save_token(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
        )
        success(f"Welcome back, {username}.")
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if is_lockout_error(error_msg):
            lockout_time = parse_lockout_time(error_msg)
            error("Account temporarily locked.")
            if lockout_time:
                minutes = lockout_time // 60
                if minutes > 0:
                    warning(f"Please try again in {minutes} minute(s).")
                else:
                    warning(f"Please try again in {lockout_time} second(s).")
            else:
                warning("Please try again later.")
        else:
            error("Invalid username or password.")
        raise typer.Exit(1) from e


@auth_app.command("logout")
def logout():
    """Logout from your account."""
    try:
        # Try to logout from server (revoke refresh tokens)
        client.logout()
        success("Successfully logged out. All sessions revoked.")
    except Exception:
        # If server logout fails, still clear local token
        config.clear_token()
        success("Successfully logged out.")
        hint("Local tokens cleared; server revoke may not have completed.")


@auth_app.command("status")
def auth_status():
    """Check authentication status."""
    token = config.load_token()
    if token:
        success("You are logged in.")

        # Check token expiry
        if config.is_token_expired():
            refresh_token = config.load_refresh_token()
            if refresh_token:
                warning("Access token expired, attempting refresh...")
                try:
                    client.refresh_access_token(refresh_token)
                    success("Token refreshed successfully.")
                except Exception as exc:
                    error("Failed to refresh token. Please login again.")
                    raise typer.Exit(1) from exc
            else:
                warning("Token expired. Please login again.")

        try:
            # Test the token by making a request
            user_info = client.get_current_user()
            info("Connection to API: OK")
            info(f"User: {user_info.get('username', 'unknown')}")
            if user_info.get("mfa_enabled"):
                info("MFA: enabled")
        except Exception:
            warning("Token may be expired. Please login again.")
    else:
        error("You are not logged in.")
        hint("Use `cli auth login` to sign in.")


@auth_app.command("refresh")
def refresh_token():
    """Manually refresh the access token."""
    refresh = config.load_refresh_token()
    if not refresh:
        error("No refresh token available. Please login again.")
        raise typer.Exit(1)

    try:
        client.refresh_access_token(refresh)
        success("Token refreshed successfully.")
    except requests.exceptions.HTTPError as e:
        error(f"Failed to refresh token: {e}")
        hint("Please login again with: cli auth login")
        raise typer.Exit(1) from e


# Resource commands
resource_app = typer.Typer(help="Resource management commands")
app.add_typer(resource_app, name="resources")


@resource_app.command("list")
def list_resources(
    show_details: bool = typer.Option(
        False, "--details", "-d", help="Show detailed information"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of items per page"),
    cursor: str | None = typer.Option(None, "--cursor", "-c", help="Pagination cursor"),
    fetch_all: bool = typer.Option(False, "--all", "-a", help="Fetch all resources"),
    sort_by: str = typer.Option(
        "name", "--sort", "-s", help="Sort by: id, name, status"
    ),
    sort_order: str = typer.Option(
        "asc", "--order", "-o", help="Sort order: asc, desc"
    ),
):
    """List all available resources."""
    try:
        # Fetch all pages if requested
        if fetch_all:
            if not confirm_action(
                "Fetch all resources? This may take a while for large datasets."
            ):
                warning("Operation cancelled.")
                return
            all_resources = []
            current_cursor = None
            page = 1
            while True:
                result = client.list_resources(
                    cursor=current_cursor,
                    limit=100,  # Max per page
                    sort_by=sort_by,
                    sort_order=sort_order,
                )
                all_resources.extend(result.get("data", []))
                info(f"Fetched page {page} ({len(all_resources)} total)")
                if not result.get("has_more"):
                    break
                current_cursor = result.get("next_cursor")
                page += 1
            resources = all_resources
            next_cursor = None
            has_more = False
            total_count = len(all_resources)
        else:
            result = client.list_resources(
                cursor=cursor,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                include_total=True,
            )
            resources = result.get("data", [])
            next_cursor = result.get("next_cursor")
            has_more = result.get("has_more", False)
            total_count = result.get("total_count")

        if not resources:
            info("No resources found.")
            return

        subtitle = (
            f"showing {len(resources)} of {total_count}"
            if total_count
            else f"{len(resources)} item(s)"
        )
        section("Resources", subtitle=subtitle)

        rows = []
        for resource in resources:
            # Show detailed status if available
            if "status" in resource:
                status_text = resource["status"].replace("_", " ").title()
                current_status = status_text
            else:
                # Fallback to old logic
                current_status = (
                    "Available"
                    if resource.get("current_availability", resource["available"])
                    else "Unavailable"
                )

            tags = ", ".join(resource.get("tags", [])) if resource.get("tags") else "-"
            base_text = "Enabled" if resource["available"] else "Disabled"

            if show_details:
                rows.append(
                    (
                        resource["id"],
                        resource["name"],
                        current_status,
                        base_text,
                        tags,
                    )
                )
            else:
                rows.append((resource["id"], resource["name"], current_status, tags))

        columns = ["ID", "Name", "Status", "Tags"]
        if show_details:
            columns.insert(3, "Base")
            render_table(columns, rows, title="Resources")
            hint("Tags: shown in the table above.")
        else:
            render_table(columns, rows, title="Resources")

        # Show pagination info
        if has_more and next_cursor:
            hint(f"More results available. Use --cursor '{next_cursor}' for next page.")

    except requests.exceptions.ConnectionError as exc:
        error("Unable to reach the API. Is the server running?")
        hint(f"Tried: {config.api_url}")
        raise typer.Exit(1) from exc
    except requests.exceptions.HTTPError as e:
        error(f"Failed to fetch resources: {e}")
        raise typer.Exit(1) from e


@resource_app.command("search")
def search_resources(
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
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
    limit: int = typer.Option(20, "--limit", "-l", help="Number of items per page"),
    cursor: str | None = typer.Option(None, "--cursor", "-c", help="Pagination cursor"),
    sort_by: str = typer.Option(
        "name", "--sort", "-s", help="Sort by: id, name, status"
    ),
    sort_order: str = typer.Option(
        "asc", "--order", "-o", help="Sort order: asc, desc"
    ),
):
    """Search for resources with advanced filtering."""
    section("Search resources")

    # Interactive mode
    if interactive:
        info("Interactive mode: press Enter to skip optional values.")
        query = prompt_for_optional("Search query (press Enter to skip)")

        if typer.confirm("Check availability for specific time period?", default=False):
            available_from = typer.prompt("Available from (YYYY-MM-DD HH:MM)")
            available_until = typer.prompt("Available until (YYYY-MM-DD HH:MM)")

    # Parse datetime inputs
    start_time = None
    end_time = None

    if available_from or available_until:
        if not (available_from and available_until):
            error("Both --from and --until must be specified for time filtering.")
            raise typer.Exit(1)

        try:
            start_time = parse_datetime(available_from)
            end_time = parse_datetime(available_until)

            if end_time <= start_time:
                error("End time must be after start time.")
                raise typer.Exit(1)

        except ValueError as e:
            error(str(e))
            raise typer.Exit(1) from e

    try:
        result = client.search_resources(
            query=query,
            available_from=start_time,
            available_until=end_time,
            available_only=available_only,
            cursor=cursor,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            include_total=True,
        )
        resources = result.get("data", [])
        next_cursor = result.get("next_cursor")
        has_more = result.get("has_more", False)
        total_count = result.get("total_count")

        if not resources:
            if start_time and end_time:
                info(
                    f"No resources available from {format_datetime(start_time)} to {format_datetime(end_time)}."
                )
            else:
                info("No resources found matching your search.")
            return

        # Display results
        if start_time and end_time:
            duration = format_duration(start_time, end_time)
            subtitle = f"available window: {format_datetime(start_time)} to {format_datetime(end_time)} ({duration})"
        else:
            subtitle = None

        result_count = (
            f"showing {len(resources)} of {total_count}"
            if total_count
            else f"{len(resources)} match(es)"
        )
        section(
            "Results",
            subtitle=result_count if not subtitle else f"{result_count} | {subtitle}",
        )

        rows = []
        for resource in resources:
            status_text = resource.get("status", "available").replace("_", " ").title()
            tags = ", ".join(resource.get("tags", [])) if resource.get("tags") else "-"
            rows.append((resource["id"], resource["name"], status_text, tags))

        render_table(["ID", "Name", "Status", "Tags"], rows, title="Resources")

        # Show pagination info
        if has_more and next_cursor:
            hint(f"More results available. Use --cursor '{next_cursor}' for next page.")

        # Offer to make a reservation if time period was specified
        if start_time and end_time and resources:
            if typer.confirm("Would you like to make a reservation?", default=False):
                resource_id = typer.prompt("Enter resource ID", type=int)

                # Validate resource ID
                if resource_id not in [r["id"] for r in resources]:
                    error("Invalid resource ID.")
                    return

                try:
                    reservation = client.create_reservation(
                        resource_id, start_time, end_time
                    )
                    selected_resource = next(
                        r for r in resources if r["id"] == resource_id
                    )

                    success("Reservation created.")
                    info(f"ID: {reservation['id']}")
                    info(f"Resource: {selected_resource['name']}")
                    info(
                        f"Time: {format_datetime(start_time)} to {format_datetime(end_time)}"
                    )

                except requests.exceptions.HTTPError as e:
                    error(f"Failed to create reservation: {e}")

    except requests.exceptions.HTTPError as e:
        error(f"Search failed: {e}")
        raise typer.Exit(1) from e


@resource_app.command("availability")
def resource_availability(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to check ahead"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed schedule"),
):
    """Get availability schedule for a resource."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        availability = client.get_resource_availability(resource_id, days)

        section(f"Availability for {availability['resource_name']}")
        info(f"Resource ID: {availability['resource_id']}")
        info(
            f"Current time: {format_datetime(datetime.fromisoformat(availability['current_time'].replace('Z', '')))}"
        )

        current_status = (
            "Available" if availability["is_currently_available"] else "Unavailable"
        )
        info(f"Current status: {current_status}")

        base_status = "Enabled" if availability["base_available"] else "Disabled"
        info(f"Base setting: {base_status}")

        reservations = availability.get("reservations", [])
        if reservations:
            section(f"Upcoming reservations ({len(reservations)})")

            for i, res in enumerate(reservations, 1):
                start = datetime.fromisoformat(res["start_time"].replace("Z", ""))
                end = datetime.fromisoformat(res["end_time"].replace("Z", ""))
                duration = format_duration(start, end)

                info(f"{i:2}. {format_datetime(start)} - {format_datetime(end)}")
                hint(f"    Duration: {duration} | Status: {res['status']}")
                if detailed:
                    hint(f"    Reservation ID: {res['id']} | User ID: {res['user_id']}")
                console.print()
        else:
            info("No upcoming reservations; resource is fully available.")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Resource not found.")
        else:
            error(f"Failed to get availability: {e}")
        raise typer.Exit(1) from e


@resource_app.command("enable")
def enable_resource(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Enable a resource (for maintenance mode)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    if not force:
        if not confirm_action(f"Enable resource {resource_id}?"):
            warning("Operation cancelled.")
            return

    try:
        result = client.update_resource_availability(resource_id, True)
        success(f"Resource {resource_id} enabled successfully.")
        info(f"Resource name: {result['resource']['name']}")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Resource not found.")
        else:
            error(f"Failed to enable resource: {e}")
        raise typer.Exit(1) from e


@resource_app.command("disable")
def disable_resource(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Disable a resource (for maintenance mode)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    if not force:
        if not confirm_action(
            f"Disable resource {resource_id}? This will prevent new reservations."
        ):
            warning("Operation cancelled.")
            return

    try:
        result = client.update_resource_availability(resource_id, False)
        success(f"Resource {resource_id} disabled.")
        info(f"Resource: {result['resource']['name']}")
        hint("Resource is now in maintenance mode.")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Resource not found.")
        else:
            error(f"Failed to disable resource: {e}")
        raise typer.Exit(1) from e


@resource_app.command("status")
def resource_status(
    resource_id: int = typer.Argument(..., help="Resource ID"),
):
    """Get detailed status information for a resource."""
    try:
        status_info = client.get_resource_status(resource_id)

        section(f"Status for {status_info['resource_name']}")
        info(f"Resource ID: {status_info['resource_id']}")
        current_time = datetime.fromisoformat(
            status_info["current_time"].replace("Z", "")
        )
        info(f"Current time: {format_datetime(current_time)}")

        # Base availability
        base_status = "Enabled" if status_info["base_available"] else "Disabled"
        info(f"Base setting: {base_status}")

        # Current status
        status_text = status_info["status"].replace("_", " ").title()
        info(f"Current status: {status_text}")

        # Additional status info
        reservation_status = (
            "Yes" if status_info["is_available_for_reservation"] else "No"
        )
        info(f"Available for reservation: {reservation_status}")
        in_use_status = "Yes" if status_info["is_currently_in_use"] else "No"
        info(f"Currently in use: {in_use_status}")

        # Unavailable details
        if status_info["is_unavailable"] and "unavailable_since" in status_info:
            unavailable_since = format_datetime(
                datetime.fromisoformat(
                    status_info["unavailable_since"].replace("Z", "")
                )
            )
            section("Maintenance details")
            info(f"Unavailable since: {unavailable_since}")
            reset_hours = status_info["hours_until_auto_reset"]
            info(f"Auto-reset in: {reset_hours:.1f} hours")
            config_hours = status_info["auto_reset_hours"]
            info(f"Auto-reset configured: {config_hours} hours")
            if status_info.get("will_auto_reset"):
                success("Will automatically reset to available.")
            else:
                warning("Auto-reset period has passed.")

        # Current reservation info
        if "current_reservation" in status_info:
            res = status_info["current_reservation"]
            start = format_datetime(
                datetime.fromisoformat(res["start_time"].replace("Z", ""))
            )
            end = format_datetime(
                datetime.fromisoformat(res["end_time"].replace("Z", ""))
            )
            section("Current reservation")
            info(f"ID: {res['id']}")
            info(f"User ID: {res['user_id']}")
            info(f"Time: {start} to {end}")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Resource not found.")
        else:
            error(f"Failed to get resource status: {e}")
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
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    if auto_reset_hours < 1 or auto_reset_hours > 168:
        error("Auto-reset hours must be between 1 and 168 (1 week).")
        raise typer.Exit(1)

    if not force:
        if not confirm_action(
            f"Set resource {resource_id} to maintenance mode "
            f"(auto-reset in {auto_reset_hours} hours)?"
        ):
            warning("Operation cancelled.")
            return

    try:
        result = client.set_resource_unavailable(resource_id, auto_reset_hours)
        success(f"Resource {resource_id} set to maintenance mode.")
        info(f"Resource: {result['resource']['name']}")
        info(f"Auto-reset in: {auto_reset_hours} hours")
        hint("Resource is now unavailable for new reservations.")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Resource not found.")
        else:
            error(f"Failed to set maintenance mode: {e}")
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
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    if not force:
        if not confirm_action(f"Reset resource {resource_id} to available status?"):
            warning("Operation cancelled.")
            return

    try:
        result = client.reset_resource_to_available(resource_id)
        success(f"Resource {resource_id} reset to available.")
        info(f"Resource: {result['resource']['name']}")
        hint("Resource is now available for reservations.")
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Resource not found.")
        else:
            error(f"Failed to reset resource: {e}")
        raise typer.Exit(1) from e


@resource_app.command("create")
def create_resource(
    name: str = typer.Argument(..., help="Resource name"),
    tags: str | None = typer.Option("", "--tags", "-t", help="Comma-separated tags"),
    available: bool = typer.Option(
        True, "--available/--unavailable", help="Resource availability"
    ),
):
    """Create a new resource."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

    try:
        resource = client.create_resource(name, tag_list, available)
        success(f"Created resource: {resource['name']}")
        info(f"ID: {resource['id']}")
        if tag_list:
            info(f"Tags: {', '.join(tag_list)}")
    except requests.exceptions.HTTPError as e:
        error(f"Failed to create resource: {e}")
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
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    # Validate file exists
    csv_file = Path(file_path)
    if not csv_file.exists():
        error(f"File not found: {file_path}")
        raise typer.Exit(1)

    if not csv_file.suffix.lower() == ".csv":
        error("File must be a CSV file.")
        raise typer.Exit(1)

    # Preview option
    if preview:
        try:
            import csv

            with open(csv_file) as f:
                reader = csv.DictReader(f)
                section(f"Preview of {csv_file.name}")

                for i, row in enumerate(reader):
                    if i >= 5:  # Show first 5 rows
                        hint("... (showing first 5 rows)")
                        break
                    info(f"Row {i + 1}: {dict(row)}")

                if not typer.confirm("\nProceed with upload?", default=True):
                    warning("Upload cancelled.")
                    return
        except Exception as e:
            error(f"Error reading file: {e}")
            raise typer.Exit(1) from e

    try:
        info(f"Uploading {csv_file.name}...")
        result = client.upload_resources_csv(str(csv_file))

        success("Upload completed.")
        info(f"Created: {result['created_count']} resources")

        if "errors" in result and result["errors"]:
            warning(f"Errors: {len(result['errors'])}")
            for err_msg in result["errors"][:3]:  # Show first 3 errors
                hint(f"- {err_msg}")
            if len(result["errors"]) > 3:
                hint(f"... and {len(result['errors']) - 3} more")

    except requests.exceptions.HTTPError as e:
        error(f"Upload failed: {e}")
        raise typer.Exit(1) from e


# System commands
system_app = typer.Typer(help="System and utility commands")
app.add_typer(system_app, name="system")


@system_app.command("status")
def system_status():
    """Check system status and connectivity."""
    section("System Status Check")

    # Check API connectivity
    try:
        health = client.health_check()
        success("API Connection: OK")
        info(f"API status: {health.get('status', 'unknown')}")
        info(f"Version: {health.get('version', 'unknown')}")

        if "timestamp" in health:
            api_time = datetime.fromisoformat(health["timestamp"].replace("Z", ""))
            info(f"API time: {format_datetime(api_time)}")

        # Show background task status if available
        if "background_tasks" in health:
            tasks = health["background_tasks"]
            for task_name, task_status in tasks.items():
                info(f"Task {task_name}: {task_status}")

    except requests.exceptions.HTTPError as e:
        error("API Connection: Failed.")
        hint(f"Error: {e}")
        return
    except Exception as e:
        error("API Connection: Error.")
        hint(f"Error: {e}")
        return

    # Check authentication
    token = config.load_token()
    if token:
        try:
            client.get_current_user()
            success("Authentication valid.")
        except requests.exceptions.HTTPError:
            warning("Authentication token expired. Use `cli auth login`.")
        except Exception:
            error("Authentication check failed.")
    else:
        warning("Not logged in. Use `cli auth login`.")

    # Check configuration
    info(f"API URL: {config.api_url}")
    info(f"Config Dir: {config.config_dir}")


@system_app.command("summary")
def availability_summary():
    """Get system-wide availability summary."""
    try:
        summary = client.get_availability_summary()

        section("System Availability Summary")

        total = summary["total_resources"]
        available = summary["available_now"]
        unavailable = summary["unavailable_now"]
        in_use = summary["currently_in_use"]

        # Calculate percentages
        avail_pct = (available / total * 100) if total > 0 else 0
        unavail_pct = (unavailable / total * 100) if total > 0 else 0
        usage_pct = (in_use / total * 100) if total > 0 else 0

        rows = [
            ("Total Resources", total, "100%"),
            ("Available Now", available, f"{avail_pct:.1f}%"),
            ("Unavailable", unavailable, f"{unavail_pct:.1f}%"),
            ("Currently In Use", in_use, f"{usage_pct:.1f}%"),
        ]

        render_table(
            ["Metric", "Count", "Percentage"],
            rows,
            title="Availability",
        )

        # Show timestamp
        timestamp = datetime.fromisoformat(summary["timestamp"].replace("Z", ""))
        hint(f"Last updated: {format_datetime(timestamp)}")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to get summary: {e}")
        raise typer.Exit(1) from e


@system_app.command("cleanup")
def manual_cleanup():
    """Manually trigger cleanup of expired reservations."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    if not confirm_action("Trigger manual cleanup of expired reservations?"):
        warning("Cleanup cancelled.")
        return

    try:
        result = client.manual_cleanup_expired()
        success("Cleanup completed.")
        info(f"Cleaned up: {result['expired_count']} expired reservations")

        if result["expired_count"] == 0:
            info("No expired reservations found.")

        timestamp = datetime.fromisoformat(result["timestamp"].replace("Z", ""))
        hint(f"Completed at: {format_datetime(timestamp)}")

    except requests.exceptions.HTTPError as e:
        error(f"Cleanup failed: {e}")
        raise typer.Exit(1) from e


@system_app.command("config")
def show_config():
    """Show current configuration."""
    section("Current Configuration")
    info(f"API URL: {config.api_url}")
    info(f"Base URL: {config.base_url}")
    info(f"API Version: {config.API_VERSION}")
    info(f"Config Directory: {config.config_dir}")
    info(f"Token File: {config.token_file}")
    info(f"Authenticated: {'Yes' if config.load_token() else 'No'}")
    if config.load_token():
        info(
            f"Refresh Token: {'Available' if config.load_refresh_token() else 'Not available'}"
        )
        if config.is_token_expired():
            warning("Token status: expired.")
        else:
            expiry = config.get_token_expiry_time()
            if expiry:
                info(f"Token Expires: {format_datetime(expiry)}")


# Reservation commands
reservation_app = typer.Typer(help="Reservation management commands")
app.add_typer(reservation_app, name="reservations")


@reservation_app.command("create")
def create_reservation(
    resource_id: int = typer.Argument(..., help="Resource ID to reserve"),
    start: str = typer.Argument(..., help="Start time (YYYY-MM-DD HH:MM)"),
    end: str | None = typer.Argument(
        None, help="End time (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)"
    ),
    recurrence: str | None = typer.Option(
        None, "--recurrence", "-r", help="Recurrence: daily, weekly, monthly"
    ),
    days: str | None = typer.Option(
        None,
        "--days",
        "-d",
        help="Days for weekly recurrence (e.g., 1,3,5 for Mon,Wed,Fri)",
    ),
    recurrence_end: str | None = typer.Option(
        None, "--recurrence-end", help="End date (YYYY-MM-DD) or count (e.g., 10)"
    ),
    recurrence_count: int | None = typer.Option(
        None, "--recurrence-count", "-n", help="Number of occurrences (default: 5)"
    ),
):
    """Create a new reservation (supports recurring reservations)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
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
                    error(
                        "End time must be a datetime (YYYY-MM-DD HH:MM) or duration (e.g., 2h, 30m)"
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
                    error("Invalid end time or duration format.")
                    raise typer.Exit(1) from e

        if end_time <= start_time:
            error("End time must be after start time.")
            raise typer.Exit(1)

    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e

    try:
        # Handle recurring reservation
        if recurrence:
            # Parse recurrence settings
            frequency = recurrence.lower()
            if frequency not in ["daily", "weekly", "monthly"]:
                error("Recurrence must be: daily, weekly, or monthly.")
                raise typer.Exit(1)

            # Parse days of week for weekly
            days_of_week = None
            if frequency == "weekly" and days:
                try:
                    days_of_week = [int(d.strip()) for d in days.split(",")]
                    for d in days_of_week:
                        if d < 0 or d > 6:
                            raise ValueError("Days must be 0-6")
                except ValueError as exc:
                    error("Days must be comma-separated numbers 0-6 (0=Mon, 6=Sun).")
                    raise typer.Exit(1) from exc

            # Parse recurrence end
            end_type = "after_count"
            end_date = None
            occurrence_count = recurrence_count or 5

            if recurrence_end:
                try:
                    # Try to parse as date
                    end_date = parse_datetime(recurrence_end + " 23:59")
                    end_type = "on_date"
                except ValueError:
                    # Try to parse as count
                    try:
                        occurrence_count = int(recurrence_end)
                        end_type = "after_count"
                    except ValueError as exc_count:
                        error(
                            "Recurrence end must be a date (YYYY-MM-DD) or number of occurrences."
                        )
                        raise typer.Exit(1) from exc_count

            # Create recurring reservation
            reservations = client.create_recurring_reservation(
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
                frequency=frequency,
                days_of_week=days_of_week,
                end_type=end_type,
                end_date=end_date,
                occurrence_count=occurrence_count,
            )

            success(f"Created {len(reservations)} recurring reservations.")
            info(f"Recurrence: {frequency}")
            if days_of_week:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                info(f"Days: {', '.join(day_names[d] for d in days_of_week)}")

            # Show first few reservations
            section("Created reservations (first 5)")
            for i, res in enumerate(reservations[:5], 1):
                res_start = datetime.fromisoformat(res["start_time"].replace("Z", ""))
                res_end = datetime.fromisoformat(res["end_time"].replace("Z", ""))
                info(
                    f"{i}. ID: {res['id']} | {format_datetime(res_start)} - {format_datetime(res_end)}"
                )

            if len(reservations) > 5:
                hint(f"... and {len(reservations) - 5} more")

        else:
            # Create single reservation
            reservation = client.create_reservation(resource_id, start_time, end_time)
            duration = format_duration(start_time, end_time)

            success("Reservation created successfully.")
            info(f"ID: {reservation['id']}")
            info(f"Resource: {reservation['resource']['name']}")
            info(f"Time: {format_datetime(start_time)} to {format_datetime(end_time)}")
            info(f"Duration: {duration}")

    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if "conflicts" in error_msg.lower():
            error("Time slot conflicts with existing reservation.")
            hint(
                "Use `cli resources search --from 'START' --until 'END'` to find available times."
            )
        elif "not found" in error_msg.lower():
            error("Resource not found.")
            hint("Use `cli resources list` to see available resources.")
        else:
            error(f"Failed to create reservation: {e}")
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
    limit: int = typer.Option(20, "--limit", "-l", help="Number of items per page"),
    cursor: str | None = typer.Option(None, "--cursor", help="Pagination cursor"),
    fetch_all: bool = typer.Option(False, "--all", "-a", help="Fetch all reservations"),
    sort_by: str = typer.Option(
        "start_time",
        "--sort",
        "-s",
        help="Sort by: id, start_time, end_time, created_at",
    ),
    sort_order: str = typer.Option(
        "desc", "--order", "-o", help="Sort order: asc, desc"
    ),
):
    """List your reservations."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        # Fetch all pages if requested
        if fetch_all:
            if not confirm_action("Fetch all reservations? This may take a while."):
                warning("Operation cancelled.")
                return
            all_reservations = []
            current_cursor = None
            page = 1
            while True:
                result = client.get_my_reservations(
                    include_cancelled=include_cancelled,
                    cursor=current_cursor,
                    limit=100,
                    sort_by=sort_by,
                    sort_order=sort_order,
                )
                all_reservations.extend(result.get("data", []))
                info(f"Fetched page {page} ({len(all_reservations)} total)")
                if not result.get("has_more"):
                    break
                current_cursor = result.get("next_cursor")
                page += 1
            reservations = all_reservations
            next_cursor = None
            has_more = False
            total_count = len(all_reservations)
        else:
            result = client.get_my_reservations(
                include_cancelled=include_cancelled,
                cursor=cursor,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                include_total=True,
            )
            reservations = result.get("data", [])
            next_cursor = result.get("next_cursor")
            has_more = result.get("has_more", False)
            total_count = result.get("total_count")

        if not reservations:
            info("No reservations found.")
            hint("Create one with: cli reservations create")
            return

        # Filter upcoming if requested
        if upcoming_only:
            now = datetime.now(UTC)
            reservations = [
                r for r in reservations if parse_aware(r["start_time"]) > now
            ]

        if not reservations:
            info("No upcoming reservations found.")
            return

        # Group by status
        active_reservations = [r for r in reservations if r["status"] == "active"]
        cancelled_reservations = [r for r in reservations if r["status"] == "cancelled"]

        if total_count:
            section(
                "Your Reservations",
                subtitle=f"showing {len(reservations)} of {total_count}",
            )
        else:
            section("Your Reservations", subtitle=f"{len(reservations)} total")

        # Show active reservations
        if active_reservations:
            section(f"Active ({len(active_reservations)})")

            for reservation in active_reservations:
                start = format_datetime(
                    datetime.fromisoformat(reservation["start_time"].replace("Z", ""))
                )
                end = format_datetime(
                    datetime.fromisoformat(reservation["end_time"].replace("Z", ""))
                )
                duration = format_duration(
                    datetime.fromisoformat(reservation["start_time"].replace("Z", "")),
                    datetime.fromisoformat(reservation["end_time"].replace("Z", "")),
                )

                info(
                    f"{reservation['id']:3} │ {reservation['resource']['name']} | {start} to {end} ({duration})"
                )

                # Show recurring info
                if reservation.get("is_recurring_instance"):
                    hint("    Part of recurring series")

                if detailed:
                    created = format_datetime(
                        datetime.fromisoformat(
                            reservation["created_at"].replace("Z", "")
                        )
                    )
                    hint(f"    Created: {created}")

        # Show cancelled reservations if requested
        if include_cancelled and cancelled_reservations:
            section(f"Cancelled ({len(cancelled_reservations)})")

            for reservation in cancelled_reservations:
                start = format_datetime(
                    datetime.fromisoformat(reservation["start_time"].replace("Z", ""))
                )
                end = format_datetime(
                    datetime.fromisoformat(reservation["end_time"].replace("Z", ""))
                )

                info(
                    f"{reservation['id']:3} │ {reservation['resource']['name']} | {start} to {end}"
                )

                if reservation.get("cancellation_reason"):
                    hint(f"    Reason: {reservation['cancellation_reason']}")

                if detailed and reservation.get("cancelled_at"):
                    cancelled = format_datetime(
                        datetime.fromisoformat(
                            reservation["cancelled_at"].replace("Z", "")
                        )
                    )
                    hint(f"    Cancelled: {cancelled}")

        # Show pagination info
        if has_more and next_cursor:
            hint(f"More results available. Use --cursor '{next_cursor}' for next page.")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to fetch reservations: {e}")
        raise typer.Exit(1) from e


@reservation_app.command("cancel")
def cancel_reservation(
    reservation_id: int = typer.Argument(..., help="Reservation ID to cancel"),
    reason: str | None = typer.Option(
        None, "--reason", "-r", help="Cancellation reason"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Cancel a reservation."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    # Get reservation details first for confirmation
    try:
        result = client.get_my_reservations()
        reservations = result.get("data", [])
        reservation = next((r for r in reservations if r["id"] == reservation_id), None)

        if not reservation:
            error(f"Reservation {reservation_id} not found or not owned by you.")
            raise typer.Exit(1)

        if reservation["status"] == "cancelled":
            warning(f"Reservation {reservation_id} is already cancelled.")
            raise typer.Exit(1)

    except requests.exceptions.HTTPError:
        # If we can't fetch details, proceed anyway (the API will handle validation)
        reservation = None

    # Show confirmation with details if available
    if not force:
        if reservation:
            start = format_datetime(
                datetime.fromisoformat(reservation["start_time"].replace("Z", ""))
            )
            end = format_datetime(
                datetime.fromisoformat(reservation["end_time"].replace("Z", ""))
            )

            section("Reservation details")
            info(f"ID: {reservation_id}")
            info(f"Resource: {reservation['resource']['name']}")
            info(f"Time: {start} to {end}")

        if not confirm_action(f"Cancel reservation {reservation_id}?"):
            warning("Cancellation aborted.")
            return

    # Prompt for reason if not provided
    if not reason:
        reason = prompt_for_optional("Cancellation reason (optional)")

    try:
        result = client.cancel_reservation(reservation_id, reason)
        success(f"Reservation {reservation_id} cancelled successfully.")

        if reason:
            info(f"Reason: {reason}")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Reservation not found.")
        elif "only cancel your own" in str(e).lower():
            error("You can only cancel your own reservations.")
        elif "already cancelled" in str(e).lower():
            warning("Reservation is already cancelled.")
        else:
            error(f"Failed to cancel reservation: {e}")
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
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        history = client.get_reservation_history(reservation_id)

        if not history:
            info(f"No history found for reservation {reservation_id}.")
            return

        section(f"History for Reservation {reservation_id}")

        for i, entry in enumerate(history):
            timestamp = format_datetime(
                datetime.fromisoformat(entry["timestamp"].replace("Z", ""))
            )
            action = entry["action"].title()
            details = entry.get("details", "")

            # Color code actions
            if entry["action"] == "created":
                action_colored = f"[green]{action}[/green]"
            elif entry["action"] == "cancelled":
                action_colored = f"[red]{action}[/red]"
            elif entry["action"] == "updated":
                action_colored = f"[yellow]{action}[/yellow]"
            else:
                action_colored = f"[blue]{action}[/blue]"

            console.print(f"{timestamp} │ {action_colored}")
            if details:
                console.print(f"{'':19} │ {details}")

            if i < len(history) - 1:  # Don't add separator after last entry
                console.print(f"{'':19} │")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Reservation not found.")
        elif "access denied" in str(e).lower():
            error(
                "Access denied - you can only view history for your own reservations."
            )
        else:
            error(f"Failed to fetch history: {e}")
        raise typer.Exit(1) from e


# Waitlist commands
waitlist_app = typer.Typer(help="Waitlist management commands")
app.add_typer(waitlist_app, name="waitlist")


@waitlist_app.command("join")
def join_waitlist(
    resource_id: int = typer.Option(..., "--resource", "-r", help="Resource ID"),
    start: str = typer.Option(
        ..., "--start", "-s", help="Desired start time (YYYY-MM-DD HH:MM)"
    ),
    end: str = typer.Option(
        ..., "--end", "-e", help="Desired end time (YYYY-MM-DD HH:MM)"
    ),
    flexible: bool = typer.Option(
        False, "--flexible", "-f", help="Accept nearby time slots"
    ),
):
    """Join the waitlist for a resource time slot."""
    try:
        config.get_auth_headers()
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        start_time = parse_datetime(start)
        end_time = parse_datetime(end)

        if end_time <= start_time:
            error("End time must be after start time.")
            raise typer.Exit(1)

    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e

    try:
        entry = client.join_waitlist(resource_id, start_time, end_time, flexible)

        success("Successfully joined waitlist.")
        info(f"Waitlist ID: {entry['id']}")
        info(f"Resource ID: {entry['resource_id']}")
        info(
            f"Desired time: {format_datetime(start_time)} to {format_datetime(end_time)}"
        )
        info(f"Position: #{entry['position']}")
        info(f"Flexible: {'Yes' if flexible else 'No'}")
        hint("You'll be notified when a slot becomes available.")

    except requests.exceptions.HTTPError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            error("Resource not found.")
        elif "already" in error_msg:
            warning("You're already on the waitlist for this time slot.")
        else:
            error(f"Failed to join waitlist: {e}")
        raise typer.Exit(1) from e


@waitlist_app.command("leave")
def leave_waitlist(
    waitlist_id: int = typer.Argument(..., help="Waitlist entry ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Leave the waitlist (cancel a waitlist entry)."""
    try:
        config.get_auth_headers()
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    if not force:
        if not confirm_action(f"Leave waitlist entry {waitlist_id}?"):
            warning("Operation cancelled.")
            return

    try:
        result = client.leave_waitlist(waitlist_id)
        success("Successfully left waitlist.")
        info(f"Waitlist ID: {result['waitlist_id']}")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Waitlist entry not found.")
        else:
            error(f"Failed to leave waitlist: {e}")
        raise typer.Exit(1) from e


@waitlist_app.command("list")
def list_waitlist_entries(
    include_completed: bool = typer.Option(
        False, "--include-completed", "-c", help="Include completed/expired entries"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of items per page"),
    cursor: str | None = typer.Option(None, "--cursor", help="Pagination cursor"),
    sort_by: str = typer.Option(
        "created_at", "--sort", "-s", help="Sort by: id, created_at, position"
    ),
    sort_order: str = typer.Option(
        "desc", "--order", "-o", help="Sort order: asc, desc"
    ),
):
    """List your waitlist entries."""
    try:
        config.get_auth_headers()
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        result = client.list_my_waitlist_entries(
            cursor=cursor,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            include_completed=include_completed,
            include_total=True,
        )
        entries = result.get("data", [])
        next_cursor = result.get("next_cursor")
        has_more = result.get("has_more", False)
        total_count = result.get("total_count")

        if not entries:
            info("No waitlist entries found.")
            hint("Join with: cli waitlist join --resource ID --start TIME --end TIME")
            return

        if total_count:
            section(
                "Your Waitlist Entries",
                subtitle=f"showing {len(entries)} of {total_count}",
            )
        else:
            section("Your Waitlist Entries", subtitle=f"{len(entries)} total")

        # Group by status
        waiting = [e for e in entries if e["status"] == "waiting"]
        offered = [e for e in entries if e["status"] == "offered"]
        other = [e for e in entries if e["status"] not in ["waiting", "offered"]]

        # Show offered first (action required)
        if offered:
            section(f"Offers available ({len(offered)})")
            for entry in offered:
                _display_waitlist_entry(entry, show_action=True)

        # Show waiting
        if waiting:
            section(f"Waiting ({len(waiting)})")
            for entry in waiting:
                _display_waitlist_entry(entry)

        # Show other statuses if included
        if include_completed and other:
            section(f"Completed/Expired ({len(other)})")
            for entry in other:
                _display_waitlist_entry(entry, dim=True)

        # Show pagination info
        if has_more and next_cursor:
            hint(f"More results available. Use --cursor '{next_cursor}' for next page.")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to fetch waitlist entries: {e}")
        raise typer.Exit(1) from e


def _display_waitlist_entry(entry: dict, show_action: bool = False, dim: bool = False):
    """Helper to display a waitlist entry."""
    start = format_datetime(
        datetime.fromisoformat(entry["desired_start"].replace("Z", ""))
    )
    end = format_datetime(datetime.fromisoformat(entry["desired_end"].replace("Z", "")))

    resource_name = entry.get("resource", {}).get(
        "name", f"Resource #{entry['resource_id']}"
    )

    line_prefix = "[dim]" if dim else ""
    line_suffix = "[/dim]" if dim else ""

    console.print(f"{line_prefix}{entry['id']:3} │ {resource_name}{line_suffix}")
    console.print(f"{line_prefix}    Desired: {start} to {end}{line_suffix}")
    console.print(
        f"{line_prefix}    Position: #{entry['position']} | Status: {entry['status']}{line_suffix}"
    )

    if entry.get("flexible_time"):
        console.print(f"{line_prefix}    Flexible timing enabled{line_suffix}")

    if show_action and entry["status"] == "offered":
        if entry.get("offer_expires_at"):
            expires = format_datetime(
                datetime.fromisoformat(entry["offer_expires_at"].replace("Z", ""))
            )
            console.print(f"    Offer expires: {expires}")
        console.print(f"    Accept with: cli waitlist accept {entry['id']}")


@waitlist_app.command("status")
def waitlist_status(
    waitlist_id: int = typer.Argument(..., help="Waitlist entry ID"),
):
    """Get detailed status of a waitlist entry."""
    try:
        config.get_auth_headers()
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        entry = client.get_waitlist_entry(waitlist_id)

        resource_name = entry.get("resource", {}).get(
            "name", f"Resource #{entry['resource_id']}"
        )

        section(f"Waitlist Entry #{entry['id']}")
        info(f"Resource: {resource_name}")

        start = format_datetime(
            datetime.fromisoformat(entry["desired_start"].replace("Z", ""))
        )
        end = format_datetime(
            datetime.fromisoformat(entry["desired_end"].replace("Z", ""))
        )
        info(f"Desired time: {start} to {end}")

        # Status with color
        status_colors = {
            "waiting": "[blue]Waiting[/blue]",
            "offered": "[yellow]Offer Available[/yellow]",
            "fulfilled": "[green]Fulfilled[/green]",
            "expired": "[red]Expired[/red]",
            "cancelled": "[dim]Cancelled[/dim]",
        }
        console.print(f"Status: {status_colors.get(entry['status'], entry['status'])}")
        info(f"Position: #{entry['position']}")
        info(f"Flexible: {'Yes' if entry['flexible_time'] else 'No'}")

        created = format_datetime(
            datetime.fromisoformat(entry["created_at"].replace("Z", ""))
        )
        info(f"Joined: {created}")

        if entry.get("offered_at"):
            offered = format_datetime(
                datetime.fromisoformat(entry["offered_at"].replace("Z", ""))
            )
            info(f"Offered at: {offered}")

        if entry.get("offer_expires_at"):
            expires = format_datetime(
                datetime.fromisoformat(entry["offer_expires_at"].replace("Z", ""))
            )
            info(f"Offer expires: {expires}")

        if entry["status"] == "offered":
            hint(f"Accept this offer with: cli waitlist accept {entry['id']}")

    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Waitlist entry not found.")
        else:
            error(f"Failed to get waitlist status: {e}")
        raise typer.Exit(1) from e


@waitlist_app.command("accept")
def accept_waitlist_offer(
    waitlist_id: int = typer.Argument(..., help="Waitlist entry ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Accept a waitlist offer and create a reservation."""
    try:
        config.get_auth_headers()
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    # Get entry details for confirmation
    try:
        entry = client.get_waitlist_entry(waitlist_id)
        if entry["status"] != "offered":
            error(f"No active offer for waitlist entry {waitlist_id}.")
            hint(f"Current status: {entry['status']}")
            raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        if "not found" in str(e).lower():
            error("Waitlist entry not found.")
        else:
            error(f"Failed to get waitlist entry: {e}")
        raise typer.Exit(1) from e

    if not force:
        resource_name = entry.get("resource", {}).get(
            "name", f"Resource #{entry['resource_id']}"
        )
        start = format_datetime(
            datetime.fromisoformat(entry["desired_start"].replace("Z", ""))
        )
        end = format_datetime(
            datetime.fromisoformat(entry["desired_end"].replace("Z", ""))
        )

        section("Accept waitlist offer")
        info(f"Resource: {resource_name}")
        info(f"Time: {start} to {end}")

        if not confirm_action("Accept this offer and create reservation?"):
            warning("Operation cancelled.")
            return

    try:
        reservation = client.accept_waitlist_offer(waitlist_id)

        success("Reservation created from waitlist offer.")
        info(f"Reservation ID: {reservation['id']}")
        info(f"Resource: {reservation['resource']['name']}")

        start = format_datetime(
            datetime.fromisoformat(reservation["start_time"].replace("Z", ""))
        )
        end = format_datetime(
            datetime.fromisoformat(reservation["end_time"].replace("Z", ""))
        )
        info(f"Time: {start} to {end}")

    except requests.exceptions.HTTPError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            error("Waitlist entry not found.")
        elif "expired" in error_msg:
            warning("This offer has expired.")
        elif "no active offer" in error_msg:
            error("No active offer for this waitlist entry.")
        elif "conflict" in error_msg:
            error("Time slot is no longer available.")
        else:
            error(f"Failed to accept offer: {e}")
        raise typer.Exit(1) from e


# Quick action commands (shortcuts)
@app.command("reserve")
def quick_reserve(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    start: str = typer.Argument(..., help="Start time (YYYY-MM-DD HH:MM)"),
    duration: str = typer.Argument(..., help="Duration (e.g., 2h, 30m, 1h30m)"),
):
    """Quick reserve command (shortcut for reservations create with duration)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        start_time = parse_datetime(start)
        duration_delta = parse_duration(duration)
        end_time = start_time + duration_delta

    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e

    try:
        reservation = client.create_reservation(resource_id, start_time, end_time)

        success("Quick reservation created.")
        info(f"ID: {reservation['id']}")
        info(f"Resource: {reservation['resource']['name']}")
        info(f"Time: {format_datetime(start_time)} to {format_datetime(end_time)}")
        info(f"Duration: {duration}")

    except requests.exceptions.HTTPError as e:
        if "conflicts" in str(e).lower():
            error("Time slot conflicts with existing reservation.")
        else:
            error(f"Failed to create reservation: {e}")
        raise typer.Exit(1) from e


@app.command("upcoming")
def show_upcoming_reservations():
    """Show upcoming reservations (shortcut)."""
    try:
        config.get_auth_headers()  # Check authentication
    except ValueError as e:
        error("Please login first: cli auth login")
        raise typer.Exit(1) from e

    try:
        result = client.get_my_reservations(sort_by="start_time", sort_order="asc")
        reservations = result.get("data", [])
        now = datetime.now(UTC)

        # Filter to upcoming active reservations
        upcoming = [
            r
            for r in reservations
            if r["status"] == "active" and parse_aware(r["start_time"]) > now
        ]

        if not upcoming:
            info("No upcoming reservations.")
            hint("Create one with: cli reserve or cli reservations create")
            return

        # Sort by start time
        upcoming.sort(key=lambda r: r["start_time"])

        section(f"Upcoming Reservations ({len(upcoming)})")

        for reservation in upcoming[:10]:  # Show first 10
            start_dt = datetime.fromisoformat(reservation["start_time"]).replace(
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

            info(
                f"{reservation['id']:3} │ {reservation['resource']['name']} | {format_datetime(start_dt)} ({time_str}) | Duration: {duration}"
            )

        if len(upcoming) > 10:
            hint(f"... and {len(upcoming) - 10} more")
            hint("Use `cli reservations list --upcoming` for full list")

    except requests.exceptions.HTTPError as e:
        error(f"Failed to fetch reservations: {e}")
        raise typer.Exit(1) from e


# Main entry point
if __name__ == "__main__":
    app()
