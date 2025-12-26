# Resource Reserver

**Intelligent resource scheduling and reservation management**

Resource Reserver is a modern, full-stack application for managing resource reservations. Whether you're booking meeting rooms, equipment, or any shared resources, Resource Reserver provides an intuitive interface and powerful features to streamline the process.

## Key Features

- **Resource Management** - Create and manage resources with custom attributes, capacity limits, and business hours
- **Smart Reservations** - Book resources with conflict detection and validation
- **Waitlist System** - Join waitlists for busy resources and get notified when slots open
- **Calendar Integration** - Export reservations to your favorite calendar app via iCal
- **Real-time Updates** - WebSocket-powered live updates across all clients
- **Email Notifications** - Automatic reminders and confirmation emails
- **Analytics Dashboard** - Track utilization and popular resources
- **Role-based Access** - Flexible permission system for users and admins
- **API First** - Full REST API with versioning and webhooks
- **PWA Support** - Install as a mobile app with offline capabilities
- **Multi-language** - Support for English, Spanish, and French

## Quick Links

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } **Getting Started**

  ______________________________________________________________________

  Install and configure Resource Reserver in minutes

  [:octicons-arrow-right-24: Installation](getting-started/installation.md)

- :material-book-open-variant:{ .lg .middle } **User Guide**

  ______________________________________________________________________

  Learn how to use all features effectively

  [:octicons-arrow-right-24: Dashboard](user-guide/dashboard.md)

- :material-api:{ .lg .middle } **API Reference**

  ______________________________________________________________________

  Integrate with our comprehensive REST API

  [:octicons-arrow-right-24: API Overview](api/overview.md)

- :material-cog:{ .lg .middle } **Admin Guide**

  ______________________________________________________________________

  Configure and manage the system

  [:octicons-arrow-right-24: User Management](admin/users.md)

</div>

## Architecture

Resource Reserver uses a modern tech stack:

| Component | Technology          |
| --------- | ------------------- |
| Backend   | FastAPI (Python)    |
| Frontend  | Next.js 14 (React)  |
| Database  | PostgreSQL / SQLite |
| Cache     | Redis               |
| Auth      | JWT tokens          |
| Real-time | WebSockets          |

## License

Resource Reserver is open source software licensed under the MIT license.
