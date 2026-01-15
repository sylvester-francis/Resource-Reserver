# Resources

Resources are the items people reserve (rooms, equipment, vehicles, and more).

## View and search

- Use the resource list to browse by name or tags
- Use filters for status and availability
- Tag filtering uses AND logic: selecting multiple tags shows only resources with ALL selected tags
- The API also supports advanced search and saved searches

## Reserve a resource

- Any authenticated user can make a reservation
- You can reserve resources that are currently in use, as long as your desired time slot is available
- Click the "Reserve" button on any available resource to book a time slot

## Cancel a reservation

- You can cancel your own reservations from the Reservations tab
- Click the "Cancel" button on any active reservation that hasn't started yet
- Admins can cancel any user's reservation if needed

## Admin: Create a resource

> **Note:** Creating resources requires admin privileges.

- Provide a name (required) and optional description
- Add tags for categorization
- Set default availability (available or unavailable)

## Admin: Edit a resource

> **Note:** Editing resources requires admin privileges.

- Click the edit (pencil) icon on any resource
- Update the name, description, or tags
- Resources that are currently in use cannot be edited

## Admin: Import from CSV

> **Note:** CSV import requires admin privileges.

You can upload a CSV file to create resources in bulk.

Required columns:

- `name`

Optional columns:

- `tags` (comma-separated)
- `available` (true or false)

Sample files are available in `data/csv/resources.csv` and `data/csv/demo-resources.csv`.

## Admin: Manage Tags

> **Note:** Tag management requires admin privileges.

Admins can manage tags globally from the "Manage Tags" button in the Resources tab:

- **View all tags** with the count of resources using each tag
- **Rename a tag** - updates the tag on all resources that have it
- **Delete a tag** - removes the tag from all resources

Tag names are automatically trimmed of whitespace. Duplicate tag names (case-insensitive) are not allowed.

## Availability and status

- View schedule and availability for a specific resource
- Mark resources unavailable for maintenance and reset them later (admin only)

## Business hours and blackout dates

Administrators can define business hours and blackout dates to control when resources can be booked. See the Admin Guide for details.
