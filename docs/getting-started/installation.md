# Installation

This guide covers how to install and run Resource Reserver.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (or SQLite for development)
- Redis 7+ (optional, for caching)

## Quick Start with Docker

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver

# Start all services
docker-compose up -d

# Access the application
open http://localhost:3000
```

## Manual Installation

### Backend Setup

1. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

1. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

1. **Initialize the database**

   ```bash
   # For development (SQLite)
   python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"

   # For production (PostgreSQL with Alembic)
   alembic upgrade head
   ```

1. **Start the backend server**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Install dependencies**

   ```bash
   cd frontend-next
   npm install
   ```

1. **Configure environment**

   ```bash
   cp .env.example .env.local
   # Set NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

1. **Start the development server**

   ```bash
   npm run dev
   ```

1. **Access the application**

   Open [http://localhost:3000](http://localhost:3000) in your browser.

## First-time Setup

When you first access the application, you'll be prompted to create an admin account:

1. Navigate to `/setup`
1. Enter your admin username and password
1. Click "Create Admin Account"
1. Log in with your new credentials

## Verifying Installation

Check that all services are running:

```bash
# Backend health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "database": "connected", "cache": "connected"}
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Learn the basics
- [Configuration](configuration.md) - Customize your installation
- [User Guide](../user-guide/dashboard.md) - Start using the application
