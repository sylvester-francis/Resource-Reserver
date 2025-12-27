# Resources

Resources are the items people reserve (rooms, equipment, vehicles, and more).

## View and search

- Use the resource list to browse by name or tags
- Use filters for status and availability
- The API also supports advanced search and saved searches

## Create a resource

- Provide a name and optional tags
- Set default availability (available or unavailable)

## Import from CSV

You can upload a CSV file to create resources in bulk.

Required columns:

- `name`

Optional columns:

- `tags` (comma-separated)
- `available` (true or false)

Sample files are available in `data/csv/resources.csv` and `data/csv/demo-resources.csv`.

## Availability and status

- View schedule and availability for a specific resource
- Mark resources unavailable for maintenance and reset them later

## Business hours and blackout dates

Administrators can define business hours and blackout dates to control when resources can be booked. See the Admin Guide for details.
