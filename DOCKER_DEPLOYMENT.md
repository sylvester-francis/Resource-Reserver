# Docker Deployment Guide

This guide covers all Docker deployment scenarios for the Resource Reserver application with the modernized TypeScript frontend.

## Docker Images Overview

The project includes three Docker configurations:

1. **Dockerfile** - Production multi-stage build with frontend compilation
2. **Dockerfile.dev** - Development environment with Node.js and hot reload
3. **Dockerfile.ci** - CI-specific build expecting pre-built frontend assets

## Production Deployment

### Multi-stage Production Build

The production Dockerfile uses a multi-stage build to compile the TypeScript frontend and create an optimized Python backend container.

```bash
# Build and run production container
docker build -t resource-reserver .
docker run -d -p 8000:8000 resource-reserver

# Or use docker-compose (recommended)
docker compose up -d api
```

### Production Features
- ✅ TypeScript compilation in frontend stage
- ✅ Optimized build with tree shaking
- ✅ Multi-stage build for smaller final image
- ✅ Non-root user security
- ✅ Health checks included
- ✅ All frontend assets bundled

## Development Deployment

### Development Container with Hot Reload

The development Dockerfile includes both Node.js and Python for full development workflow.

```bash
# Build and run development container
docker build -f Dockerfile.dev -t resource-reserver-dev .
docker run -d -p 8000:8000 -p 3000:3000 -v $(pwd):/app resource-reserver-dev

# Or use docker-compose profiles (recommended)
docker compose --profile dev up -d api-dev
```

### Development Features
- ✅ Node.js 18 and Python 3.11
- ✅ Frontend and backend hot reload
- ✅ Volume mounts for live editing
- ✅ Frontend dev server on port 3000
- ✅ Backend dev server on port 8000
- ✅ All development tools included

## CI/CD Deployment

### GitHub Actions Integration

The CI pipeline builds the frontend separately and uses the CI-specific Dockerfile.

```yaml
# Frontend build stage
- name: Build frontend
  run: npm run build

# Docker build with pre-built assets
- name: Build Docker image
  uses: docker/build-push-action@v5
  with:
    file: ./Dockerfile.ci
```

### CI Features
- ✅ Parallel frontend and backend builds
- ✅ Pre-built frontend assets
- ✅ Faster CI build times
- ✅ Comprehensive testing integration

## Docker Compose Configurations

### Production Service

```yaml
services:
  api:
    build: 
      context: .
      dockerfile: Dockerfile  # Multi-stage production build
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@db:5432/resource_reserver
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Development Service

```yaml
services:
  api-dev:
    build: 
      context: .
      dockerfile: Dockerfile.dev  # Development with Node.js
    ports:
      - "8001:8000"  # Backend
      - "3001:3000"  # Frontend dev server
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=sqlite:///./data/resource_reserver_dev.db
    volumes:
      - .:/app
      - /app/venv
      - /app/node_modules
    profiles:
      - dev
```

## Build Process Details

### Frontend Build Process

1. **TypeScript Compilation**: `tsc` compiles TypeScript to JavaScript
2. **Vite Bundling**: Vite bundles modules with optimizations
3. **Asset Output**: Compiled assets go to `web/dist/`
4. **Size Optimization**: Tree shaking and minification applied

```bash
# Manual frontend build
npm install
npm run typecheck  # TypeScript compilation check
npm run build      # Full build with bundling
```

### Backend Integration

The FastAPI backend serves the compiled frontend assets from `/static/dist/`:

```python
# Static file serving in FastAPI
app.mount("/static", StaticFiles(directory="web"), name="static")
```

### Build Verification

```bash
# Verify build artifacts
ls -la web/dist/
# Expected output:
# css/main.css     (~0.67 kB)
# js/main.js       (~34.52 kB)

# Test build locally
npm run build && uvicorn app.main:app --reload
```

## Environment Variables

### Development Environment

```bash
# Backend configuration
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/resource_reserver_dev.db
CLI_CONFIG_DIR=/tmp/.reservation-cli

# Frontend development (optional)
NODE_ENV=development
VITE_API_BASE_URL=http://localhost:8000
```

### Production Environment

```bash
# Backend configuration
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/database
SECRET_KEY=your-secret-key-here
PORT=8000

# Frontend (compiled, no runtime config needed)
NODE_ENV=production
```

## Troubleshooting

### Common Issues

#### Frontend Build Fails
```bash
# Clear cache and rebuild
npm run clean
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### Docker Build Fails
```bash
# Check Docker daemon
docker info

# Clear Docker cache
docker system prune -a

# Rebuild with no cache
docker build --no-cache -t resource-reserver .
```

#### Development Hot Reload Not Working
```bash
# Check volume mounts
docker compose --profile dev up -d api-dev
docker compose exec api-dev ls -la /app

# Verify ports
docker compose ps
curl http://localhost:8001/health  # Backend
curl http://localhost:3001         # Frontend dev server (if applicable)
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
# Verify frontend assets are served
curl -f http://localhost:8000/static/dist/js/main.js
curl -f http://localhost:8000/static/dist/css/main.css
curl -f http://localhost:8000/  # Should load the app
```

## Performance Optimization

### Production Optimizations

1. **Multi-stage Build**: Reduces final image size
2. **Frontend Bundling**: Tree shaking and minification
3. **Static Asset Serving**: Efficient file serving
4. **Health Checks**: Container orchestration support

### Development Optimizations

1. **Volume Mounts**: Live code editing
2. **Hot Reload**: Instant feedback
3. **Parallel Servers**: Frontend and backend development
4. **Cache Mounting**: Faster rebuilds

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

This comprehensive Docker deployment setup ensures the modernized TypeScript frontend is properly built and integrated across all deployment scenarios while maintaining optimal performance and security.