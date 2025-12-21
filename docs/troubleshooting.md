# Troubleshooting Guide

## Common Issues and Solutions

### Installation & Setup Issues

#### Docker Issues

**Problem**: `docker-compose up` fails with "port already in use"

```bash
Error: bind: address already in use
```

**Solution**:

```bash
# Check what's using the ports
netstat -an | grep :3000
netstat -an | grep :8000

# Stop conflicting services
sudo lsof -ti:3000 | xargs kill -9
sudo lsof -ti:8000 | xargs kill -9

# Or use different ports
export FRONTEND_PORT=3001
export BACKEND_PORT=8001
docker-compose up -d
```

**Problem**: Docker containers fail to start

```bash
ERROR: Couldn't connect to Docker daemon
```

**Solution**:

```bash
# Start Docker service
sudo systemctl start docker

# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker is running
docker --version
docker-compose --version
```

**Problem**: "No space left on device" error

**Solution**:

```bash
# Clean up Docker
docker system prune -a
docker volume prune

# Check disk space
df -h

# Remove unused containers and images
docker container prune
docker image prune -a
```

#### Database Issues

**Problem**: Database connection fails

```bash
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

**Solution**:

```bash
# Check if data directory exists
ls -la data/

# Create data directory if missing
mkdir -p data
chmod 755 data

# Restart backend service
docker-compose restart backend
```

**Problem**: PostgreSQL won't start

```bash
FATAL: password authentication failed for user "postgres"
```

**Solution**:

```bash
# Check environment variables
cat .env | grep POSTGRES

# Reset PostgreSQL data
docker-compose down
docker volume rm resource-reserver_postgres_data
docker-compose --profile postgres up -d
```

### Application Issues

#### Authentication Problems

**Problem**: Login fails with correct credentials

```bash
401 Unauthorized: Incorrect username or password
```

**Solution**:

```bash
# Check if user exists in database
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import User
db = SessionLocal()
users = db.query(User).all()
for user in users:
    print(f'Username: {user.username}')
"

# Create new user if needed
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}'
```

**Problem**: Session expires immediately

```bash
Your session has expired. Please log in again.
```

**Solution**:

```bash
# Check system time
date

# Verify JWT secret is set
docker-compose exec backend env | grep SECRET_KEY

# Clear browser cookies and try again
# Or use incognito/private mode
```

**Problem**: Login fails in Safari but works in Chrome/Brave (macOS Sequoia, M-series chips)

```bash
Login successful in Brave/Chrome but fails in Safari
Cookies not being set or retained
Session immediately expires after login
```

**Root Cause**: Safari requires explicit `sameSite` attribute for cookies. This is more strictly enforced on macOS Sequoia with Apple Silicon (M1/M2/M3/M4), especially when using Podman or alternative container runtimes.

**Solution**:

```bash
# This issue has been fixed in version 2.0.1+
# Verify your frontend/server.js includes sameSite attribute

# If using older version, update the cookie configuration:
# frontend/server.js line 118-126 should include:
# sameSite: 'Lax'  // Required for Safari compatibility

# Restart frontend service
docker-compose restart frontend

# Clear Safari cookies:
# Safari \u003e Settings \u003e Privacy \u003e Manage Website Data
# Remove all localhost entries

# Restart Safari and try logging in again
```

**Verification**:

```bash
# Check cookie in Safari Developer Tools
# Safari \u003e Develop \u003e Show Web Inspector \u003e Storage \u003e Cookies

# Verify auth_token cookie has:
# - Name: auth_token
# - SameSite: Lax
# - HttpOnly: true
# - Secure: false (for localhost), true (for production https)

# Test login
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser\u0026password=testpass" \
  -c cookies.txt -v

# Check cookies.txt for sameSite attribute
cat cookies.txt
```

**Platform-Specific Notes**:

- **macOS Sequoia (15.x)**: Safari 18+ has stricter cookie policies
- **Apple Silicon (M1/M2/M3/M4)**: No specific issues, affects all Macs equally
- **Podman vs Docker**: Both work the same after fix
- **Other Browsers**: Chrome, Brave, Firefox, Edge all work without sameSite (but it's best practice to include it)

#### Resource Management Issues

**Problem**: Resources don't appear in the list

**Solution**:

```bash
# Check backend logs
docker-compose logs backend

# Test direct API call
curl http://localhost:8000/resources

# Check database directly
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import Resource
db = SessionLocal()
resources = db.query(Resource).all()
print(f'Found {len(resources)} resources')
for r in resources:
    print(f'- {r.name} (available: {r.available})')
"
```

**Problem**: Can't create resources - "already exists" error

**Solution**:

```bash
# Check for duplicate names
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import Resource
db = SessionLocal()
resources = db.query(Resource).all()
names = [r.name for r in resources]
duplicates = [name for name in set(names) if names.count(name) > 1]
print(f'Duplicate names: {duplicates}')
"

# Clean up duplicates if needed
# Use unique names for new resources
```

#### Reservation Issues

**Problem**: Can't create reservations - time conflict

**Solution**:

```bash
# Check existing reservations for resource
curl "http://localhost:8000/resources/1/availability?days_ahead=1"

# Use a different time slot
# Check resource is not disabled
```

**Problem**: Reservations don't show up

**Solution**:

```bash
# Check reservation status
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import Reservation
from datetime import datetime
db = SessionLocal()
reservations = db.query(Reservation).all()
for r in reservations:
    print(f'ID: {r.id}, Status: {r.status}, Resource: {r.resource_id}')
    print(f'  Start: {r.start_time}, End: {r.end_time}')
"

# Refresh the page
# Check browser console for errors
```

### Frontend Issues

#### Page Loading Problems

**Problem**: Frontend shows blank page

**Solution**:

```bash
# Check frontend logs
docker-compose logs frontend

# Check browser console (F12 > Console)
# Look for JavaScript errors

# Verify frontend is running
curl http://localhost:3000

# Check if backend is accessible from frontend
docker-compose exec frontend curl http://backend:8000/health
```

**Problem**: "API Error" messages

**Solution**:

```bash
# Check backend health
curl http://localhost:8000/health

# Check network between frontend and backend
docker-compose exec frontend ping backend

# Verify API_BASE_URL setting
docker-compose exec frontend env | grep API_BASE_URL

# Check backend logs for errors
docker-compose logs backend | tail -50
```

#### Search and Filtering Issues

**Problem**: Search doesn't work

**Solution**:

```bash
# Test search API directly
curl "http://localhost:8000/resources/search?q=test"

# Check browser network tab (F12 > Network)
# Clear browser cache
# Try different search terms
```

**Problem**: Status filters not working

**Solution**:

```bash
# Check resource availability calculation
curl "http://localhost:8000/resources/availability/summary"

# Refresh resources data
# Clear browser local storage
```

### Performance Issues

#### Slow Loading

**Problem**: Dashboard takes long to load

**Solution**:

```bash
# Check container resources
docker stats

# Optimize database
docker-compose exec backend python -c "
from app.database import SessionLocal
db = SessionLocal()
db.execute('VACUUM')
db.execute('ANALYZE')
"

# Check for memory leaks
docker-compose restart backend frontend
```

**Problem**: High CPU usage

**Solution**:

```bash
# Monitor processes
docker-compose exec backend top

# Check for infinite loops in logs
docker-compose logs backend | grep -i error

# Limit container resources
echo "
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
" > docker-compose.override.yml

docker-compose up -d
```

### Network Issues

#### Port Conflicts

**Problem**: "Address already in use" errors

**Solution**:

```bash
# Use different ports
cat > docker-compose.override.yml << EOF
services:
  frontend:
    ports:
      - "3001:3000"
  backend:
    ports:
      - "8001:8000"
EOF

# Update environment
export API_BASE_URL=http://localhost:8001

docker-compose up -d
```

#### Connectivity Issues

**Problem**: Can't reach the application from other devices

**Solution**:

```bash
# Bind to all interfaces
cat > docker-compose.override.yml << EOF
services:
  frontend:
    ports:
      - "0.0.0.0:3000:3000"
  backend:
    ports:
      - "0.0.0.0:8000:8000"
EOF

# Check firewall
sudo ufw allow 3000
sudo ufw allow 8000

# Update CORS settings if needed
```

### Data Issues

#### Lost Data

**Problem**: All resources/reservations disappeared

**Solution**:

```bash
# Check if database file exists
ls -la data/

# Check database integrity
docker-compose exec backend python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('PRAGMA integrity_check'))
    print(result.fetchone())
"

# Restore from backup if available
cp data/backup.db data/resource_reserver.db
docker-compose restart backend
```

#### Corrupt Database

**Problem**: Database corruption errors

**Solution**:

```bash
# Backup current database
cp data/resource_reserver.db data/resource_reserver.db.corrupt

# Try to repair
docker-compose exec backend python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('PRAGMA journal_mode=DELETE'))
    conn.execute(text('VACUUM'))
    conn.commit()
"

# If repair fails, recreate database
rm data/resource_reserver.db
docker-compose restart backend
# Note: This will lose all data
```

### Getting Help

#### Log Collection

```bash
# Collect all logs for support
mkdir logs
docker-compose logs backend > logs/backend.log
docker-compose logs frontend > logs/frontend.log
docker-compose logs postgres > logs/postgres.log 2>/dev/null || echo "PostgreSQL not running"

# System information
docker-compose ps > logs/services.log
docker version > logs/docker.log
df -h > logs/disk.log
free -h > logs/memory.log

# Compress logs
tar -czf support-logs-$(date +%Y%m%d).tar.gz logs/
```

#### Debug Mode

```bash
# Enable debug logging
cat > docker-compose.override.yml << EOF
services:
  backend:
    environment:
      - LOG_LEVEL=DEBUG
  frontend:
    environment:
      - DEBUG=*
EOF

docker-compose up -d
```

#### Health Check Script

```bash
#!/bin/bash
# health-check.sh
echo "=== Resource Reserver Health Check ==="

echo "1. Docker services:"
docker-compose ps

echo -e "\n2. Port accessibility:"
curl -s http://localhost:3000 > /dev/null && echo "[OK] Frontend (3000) accessible" || echo "[ERROR] Frontend (3000) not accessible"
curl -s http://localhost:8000/health > /dev/null && echo "[OK] Backend (8000) accessible" || echo "[ERROR] Backend (8000) not accessible"

echo -e "\n3. Backend health:"
curl -s http://localhost:8000/health | jq .

echo -e "\n4. Database check:"
docker-compose exec -T backend python -c "
from app.database import SessionLocal
from app.models import Resource
try:
    db = SessionLocal()
    count = db.query(Resource).count()
    print(f'[OK] Database accessible, {count} resources')
except Exception as e:
    print(f'[ERROR] Database error: {e}')
"

echo -e "\n5. Disk space:"
df -h | grep -E "(Filesystem|/dev/)"

echo -e "\n6. Memory usage:"
free -h
```

#### Contact Support

If issues persist:

1. Run the health check script above

1. Collect logs using the log collection script

1. Include your:

   - Operating system and version
   - Docker and Docker Compose versions
   - Any custom configuration
   - Steps to reproduce the issue

1. Create an issue in the project repository with all the collected information

### Quick Fixes Checklist

- [ ] Restart services: `docker-compose restart`
- [ ] Check logs: `docker-compose logs -f`
- [ ] Verify ports: `netstat -an | grep -E "(3000|8000)"`
- [ ] Test connectivity: `curl http://localhost:8000/health`
- [ ] Clear browser cache and cookies
- [ ] Check disk space: `df -h`
- [ ] Verify Docker is running: `docker ps`
- [ ] Check environment variables: `cat .env`
- [ ] Test database: Access `/api/resources` directly
- [ ] Restart Docker daemon if needed: `sudo systemctl restart docker`
