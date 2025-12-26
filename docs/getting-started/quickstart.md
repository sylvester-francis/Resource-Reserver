# Quick Start Guide

Get up and running with Resource Reserver in 5 minutes.

## Creating Your First Resource

1. Log in as an admin user
1. Click **"Add Resource"** on the dashboard
1. Fill in the resource details:
   - **Name**: Conference Room A
   - **Description**: Main conference room with projector
   - **Capacity**: 12
1. Click **Save**

## Making a Reservation

1. From the dashboard, find the resource you want to book
1. Click **"Reserve"**
1. Select your date and time:
   - Choose a date from the calendar
   - Select an available time slot
1. Add optional notes
1. Click **"Confirm Reservation"**

!!! success "Confirmation" You'll receive a confirmation email with your reservation details.

## Viewing Your Reservations

Your upcoming reservations appear on the dashboard under **"My Reservations"**.

You can:

- **View details** - Click on a reservation to see full information
- **Cancel** - Click the cancel button if you need to free up the slot
- **Export** - Download an `.ics` file for your calendar

## Joining a Waitlist

If a resource is fully booked:

1. Click **"Join Waitlist"** instead of Reserve
1. Enter your preferred time window
1. You'll be notified when a slot becomes available

## Setting Up Calendar Sync

To sync your reservations with Google Calendar, Outlook, or Apple Calendar:

1. Go to **Settings** > **Calendar**
1. Click **"Get Subscription URL"**
1. Copy the URL
1. Add it as a subscription calendar in your preferred app

## CLI Access

Resource Reserver includes a command-line interface:

```bash
# Login
resource-reserver login

# List resources
resource-reserver resources list

# Make a reservation
resource-reserver reservations create \
  --resource "Conference Room A" \
  --date 2024-01-15 \
  --start 09:00 \
  --end 10:00

# View your reservations
resource-reserver reservations list --mine
```

## Next Steps

- [Resources Guide](../user-guide/resources.md) - Learn about resource management
- [Reservations Guide](../user-guide/reservations.md) - Advanced booking options
- [API Reference](../api/overview.md) - Build integrations
