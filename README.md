# Resource Reservation System

## Overview

The Resource Reservation System is a robust, scalable API service designed to manage and schedule shared resources within an organization. This system provides a structured approach to resource allocation, enabling users to book, manage, and track the usage of various resources while maintaining a clear audit trail of all transactions.

## Key Features

- **User Authentication & Authorization**: Secure access control with JWT-based authentication
- **Resource Management**: Create, list, and search available resources
- **Intelligent Booking System**: Make, modify, and cancel reservations with conflict prevention
- **Comprehensive History**: Track all reservation changes and maintain a complete audit log
- **Bulk Operations**: Import multiple resources via CSV upload
- **RESTful API**: Clean, well-documented endpoints following REST principles
- **CORS Support**: Ready for web application integration

## Technical Architecture

### Backend Stack
- **Framework**: FastAPI (Python 3.7+)
- **Database**: SQLite (Production-ready for PostgreSQL/MySQL)
- **Authentication**: JWT (JSON Web Tokens)
- **API Documentation**: Auto-generated OpenAPI/Swagger UI

### Data Models

1. **Users**
   - Secure authentication
   - Reservation history

2. **Resources**
   - Unique identification
   - Availability status
   - Tag-based categorization

3. **Reservations**
   - Time-bound bookings
   - Status tracking (active/cancelled)
   - Duration calculation

4. **Audit Log**
   - Complete history of changes
   - User actions tracking
   - Timestamped records

## API Endpoints

### Authentication
- `POST /register` - Register a new user account
- `POST /token` - Obtain access token (login)

### Resources
- `POST /resources` - Create a new resource
- `GET /resources` - List all resources
- `GET /resources/search` - Search resources with filters
- `POST /resources/upload` - Upload multiple resources via CSV

### Reservations
- `POST /reservations` - Create a new reservation
- `GET /reservations/my` - View user's reservations
- `POST /reservations/{reservation_id}/cancel` - Cancel a reservation
- `GET /reservations/{reservation_id}/history` - View reservation history

### System
- `GET /health` - Health check endpoint

## Command Line Interface (CLI)

The system includes a powerful CLI built with Typer, providing an intuitive command-line interface for interacting with the Resource Reservation System. The CLI offers tab completion, rich output formatting, and interactive prompts.

### Key CLI Features

- **Interactive Authentication**: Secure login/logout with token management
- **Resource Management**: List, search, and manage resources
- **Reservation Handling**: Create, view, and cancel reservations
- **Interactive Search**: Find available resources with flexible time-based filtering
- **Rich Output**: Color-coded and formatted terminal output
- **Context-Aware Help**: Comprehensive help system with examples

### Common CLI Commands

#### Authentication
```bash
# Register a new user
python -m cli.main auth register

# Login
python -m cli.main auth login

# Logout
python -m cli.main auth logout

# Check authentication status
python -m cli.main auth status
```

#### Resource Management
```bash
# List all resources (with details)
python -m cli.main resources list --details

# Search for available resources
python -m cli.main resources search --query "conference" --from "2025-06-07 09:00" --until "2025-06-07 17:00"

# Create a new resource
python -m cli.main resources create "Conference Room A" --tags "meeting,conference"

# Upload resources from CSV
python -m cli.main resources upload resources.csv --preview
```

#### Reservation Management
```bash
# Create a new reservation
python -m cli.main reservations create 1 "2025-06-07 14:00" "2h"

# List your reservations (with options)
python -m cli.main reservations list --upcoming --detailed --include-cancelled

# Cancel a reservation
python -m cli.main reservations cancel 123 --reason "Meeting cancelled" --force

# View reservation history
python -m cli.main reservations show-history 123 --detailed
```

#### System
```bash
# Check system status
python -m cli.main system status

# Show current configuration
python -m cli.main system show-config
```

#### Quick Actions
```bash
# Quick reserve with duration
python -m cli.main quick-reserve 1 "2025-06-07 14:00" "2h"

# Find and reserve interactively
python -m cli.main find-and-reserve "2h" --query "conference" --from "tomorrow 9am"

# Show upcoming reservations (shortcut)
python -m cli.main upcoming
```

### CLI Installation

The CLI is included with the main package. After setting up the project:

1. Install the package in development mode:
   ```bash
   pip install -e .
   ```

2. Make the CLI executable:
   ```bash
   chmod +x cli/main.py
   ```

3. (Optional) Create an alias in your shell config (e.g., `~/.zshrc` or `~/.bashrc`):
   ```bash
   alias reserve="python -m cli.main"
   ```
   Then use it like: `reserve resources list`

## Getting Started

### Prerequisites
- Python 3.7+
- pip (Python package manager)
- SQLite (included with Python)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sylvester-francis/Resource-Reserver.git
   cd Resource-Reserver
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
DATABASE_URL=sqlite:///./reservations.db

# Authentication
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Configuration
API_URL=http://localhost:8000
```

### Development Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
2. Install development dependencies (if any):
   ```bash
   pip install -r requirements-dev.txt  # If you have dev requirements
   ```

3. Run tests:
   ```bash
   pytest  # If you have tests
   ```

4. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Testing

To run the test suite (if available):

```bash
pytest tests/
```

For test coverage:

```bash
pytest --cov=app tests/
```

### Environment Variables

- `DATABASE_URL`: Connection string for the database (defaults to SQLite)
- `SECRET_KEY`: Secret key for JWT token generation (change in production!)
- `ALGORITHM`: Algorithm for JWT (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time in minutes (default: 30)
- `API_URL`: Base URL for the API (used by the CLI)

For production, make sure to:
1. Change the `SECRET_KEY` to a strong, random value
2. Use a production database like PostgreSQL
3. Set appropriate token expiration times

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   python -m app.database
   ```

### Running the Application

Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Interactive API documentation is automatically available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Security Considerations

- Password hashing using bcrypt
- JWT token-based authentication
- Secure password requirements
- Input validation
- CORS protection

## Deployment

For production deployment, consider:
1. Using a production-grade ASGI server (e.g., Uvicorn with Gunicorn)
2. Setting up a PostgreSQL database
3. Configuring proper HTTPS/TLS
4. Setting up monitoring and logging

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Note

*This project is a proof of concept designed to demonstrate a resource reservation system. While it includes features suitable for small teams, it should be thoroughly reviewed and enhanced before being used in production environments.*

## Support

For support, please open an issue on the GitHub repository.

---
