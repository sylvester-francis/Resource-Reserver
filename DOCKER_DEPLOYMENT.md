# Docker Deployment Guide

This guide covers all Docker deployment scenarios for the Resource Reserver application with the Express.js + Alpine.js frontend architecture.

## Docker Images Overview

The project includes multiple Docker configurations:

1. **Dockerfile.backend** - FastAPI backend service
2. **Dockerfile.frontend** - Express.js frontend service  
3. **Dockerfile.dev** - Development environment with hot reload
4. **docker-compose.yml** - Multi-service orchestration

## Production Deployment

### Multi-Service Architecture

The production deployment uses separate containers for frontend and backend services with Docker Compose orchestration.

```bash
# Start production services
docker-compose up -d

# Or start specific services
docker-compose up -d backend frontend

# Check service status
docker-compose ps
```

### Production Features
- ✅ Separated frontend (Express.js) and backend (FastAPI) services
- ✅ No build process required - direct deployment
- ✅ Independent service scaling
- ✅ Non-root user security
- ✅ Health checks included
- ✅ Session management with cookies

## Development Deployment

### Development Environment

Run both frontend and backend services in development mode with hot reload.

```bash
# Start all development services
docker-compose --profile dev up -d

# Or manually start each service
docker-compose up -d backend
docker-compose up -d frontend

# Monitor logs
docker-compose logs -f frontend backend
```

### Development Features
- ✅ Express.js frontend with nodemon auto-restart
- ✅ FastAPI backend with uvicorn reload
- ✅ Volume mounts for live editing
- ✅ Frontend on port 3000, Backend on port 8000
- ✅ Immediate code changes reflected
- ✅ No build process required

## CI/CD Deployment

### GitHub Actions Integration

The CI pipeline tests both frontend and backend services and builds Docker containers.

```yaml
# Frontend quality checks
- name: Set up Node.js
  uses: actions/setup-node@v4
- name: Install frontend dependencies
  run: cd frontend && npm ci
- name: Test frontend
  run: cd frontend && npm test

# Backend quality checks
- name: Set up Python
  uses: actions/setup-python@v5
- name: Run backend tests
  run: pytest

# Docker build and test
- name: Build Docker services
  run: docker-compose build
```

### CI Features
- ✅ Separated frontend and backend testing
- ✅ No complex build process required
- ✅ Multi-service Docker testing
- ✅ Session management testing

## Docker Compose Configurations

### Production Services

```yaml
services:
  # FastAPI Backend Service
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=sqlite:///./data/resource_reserver.db
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  # Express.js Frontend Service
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
```

### Development Services

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
    volumes:
      - .:/app
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - API_BASE_URL=http://backend:8000
    volumes:
      - ./frontend:/app
    command: npm run dev
    depends_on:
      - backend
    profiles:
      - dev
```

## Build Process Details

### Frontend Architecture

1. **Express.js Server**: Handles routing, authentication, and API proxying
2. **EJS Templates**: Server-side rendered HTML templates
3. **Alpine.js**: Client-side reactivity and DOM manipulation
4. **Static Assets**: CSS and JavaScript served directly

```bash
# Frontend development
cd frontend
npm install
npm start  # Starts Express.js server on port 3000
```

### Backend Integration

The Express.js frontend communicates with the FastAPI backend via HTTP API calls:

```javascript
// API proxy in Express.js server
app.post('/api/resources', requireAuth, async (req, res) => {
  const result = await apiCall('/resources', {
    method: 'POST',
    data: req.body
  }, req.token);
  res.json({ success: true, data: result });
});
```

### Service Verification

```bash
# Test backend service
curl -f http://localhost:8000/health

# Test frontend service  
curl -f http://localhost:3000

# Test end-to-end flow
curl -f http://localhost:3000/login
```

## Environment Variables

### Development Environment

```bash
# Backend configuration (.env in root)
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/resource_reserver_dev.db
SECRET_KEY=dev-secret-key

# Frontend configuration (frontend/.env)
NODE_ENV=development
PORT=3000
API_BASE_URL=http://localhost:8000
```

### Production Environment

```bash
# Backend configuration
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/database
SECRET_KEY=your-secure-secret-key-here

# Frontend configuration
NODE_ENV=production
PORT=3000
API_BASE_URL=http://backend:8000
```

## Troubleshooting

### Common Issues

#### Frontend Service Issues
```bash
# Check frontend dependencies
cd frontend
npm install

# Restart frontend service
docker-compose restart frontend

# Check frontend logs
docker-compose logs frontend
```

#### Backend Service Issues
```bash
# Check backend dependencies
pip install -r requirements.txt

# Restart backend service
docker-compose restart backend

# Check backend logs
docker-compose logs backend
```

#### Service Communication Issues
```bash
# Check all services
docker-compose ps

# Test backend from frontend container
docker-compose exec frontend curl http://backend:8000/health

# Check network connectivity
docker network ls
docker network inspect resource-reserver_default
```

### Health Checks

#### Container Health
```bash
# Check container health
docker ps
docker logs <container-id>

# Test health endpoint
curl -f http://localhost:8000/health
```

#### Frontend Assets
```bash
# Verify frontend service is running
curl -f http://localhost:3000/
curl -f http://localhost:3000/login

# Check static assets
curl -f http://localhost:3000/css/styles.css
curl -f http://localhost:3000/js/app.js
```

## Performance Optimization

### Production Optimizations

1. **Service Separation**: Independent frontend and backend scaling
2. **No Build Process**: Direct deployment without compilation
3. **Session Management**: Efficient cookie-based authentication
4. **Health Checks**: Container orchestration support

### Development Optimizations

1. **Volume Mounts**: Live code editing
2. **Hot Reload**: Auto-restart on file changes
3. **Service Independence**: Frontend and backend can be developed separately
4. **Simplified Architecture**: No complex build tools or compilation

## Security Considerations

### Production Security

1. **Non-root User**: Container runs as `appuser`
2. **Minimal Base Image**: Python slim image
3. **No Development Tools**: Production-only dependencies
4. **Environment Variables**: Secure configuration

### Development Security

1. **Volume Restrictions**: Exclude sensitive directories
2. **Development Dependencies**: Isolated from production
3. **Local Binding**: Development servers bound to localhost
4. **Debug Information**: Enhanced logging for development

## Scaling and Deployment

### Horizontal Scaling

```yaml
services:
  api:
    build: .
    deploy:
      replicas: 3
    ports:
      - "8000-8002:8000"
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - api
```

### Database Integration

```yaml
services:
  api:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/resource_reserver
    depends_on:
      - db
      
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: resource_reserver
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

This comprehensive Docker deployment setup ensures the Express.js + Alpine.js frontend architecture is properly deployed and integrated across all deployment scenarios while maintaining optimal performance, security, and developer experience with no build complexity.