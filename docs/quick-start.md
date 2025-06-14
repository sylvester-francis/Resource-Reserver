# Quick Start Guide

## 🚀 Get Resource Reserver Running in 5 Minutes

### Prerequisites

- Docker and Docker Compose installed
- 2GB RAM available
- Ports 3000 and 8000 available

### Step 1: Clone and Start

```bash
git clone <your-repo-url>
cd Resource-Reserver

# Start the entire system
docker-compose up -d

# Check status
docker-compose ps
```

### Step 2: Access the Application

1. **Open your browser**: Navigate to `http://localhost:3000`
2. **Create an account**: Click "Register" and create your first user
3. **Log in**: Use your credentials to access the dashboard

### Step 3: Create Your First Resource

1. Click **"+ Add Resource"** button
2. Enter resource details:
   - **Name**: "Conference Room A"
   - **Tags**: "meeting, video-call, whiteboard" (optional)
   - **Status**: Available ✓
3. Click **"Create Resource"**

### Step 4: Make Your First Reservation

1. Find your resource in the list
2. Click **"Reserve"** button
3. Select date and time:
   - **Start**: Tomorrow at 9:00 AM
   - **End**: Tomorrow at 10:00 AM
4. Click **"Create Reservation"**

### Step 5: Monitor System Health

1. Click **"System Status"** in the top menu
2. Verify all services are healthy
3. Check resource utilization statistics

## Next Steps

- **Bulk Import**: Upload resources via CSV (see [Bulk Operations Guide](bulk-operations.md))
- **API Integration**: Connect your existing systems (see [API Documentation](api-reference.md))
- **Advanced Configuration**: Customize deployment settings (see [Deployment Guide](deployment.md))

## Quick Commands

```bash
# View logs
docker-compose logs -f

# Stop system
docker-compose down

# Update system
docker-compose pull && docker-compose up -d

# Backup data
docker-compose exec backend python -c "import shutil; shutil.copy('/app/data/resource_reserver.db', '/app/data/backup.db')"
```

## Troubleshooting

**Problem**: Can't access <http://localhost:3000>  
**Solution**: Check if ports are available: `netstat -an | grep 3000`

**Problem**: Login fails  
**Solution**: Verify backend is running: `docker-compose logs backend`

**Problem**: Resources not showing  
**Solution**: Check database connection in System Status

Need help? See our [Troubleshooting Guide](troubleshooting.md) or check the logs.
