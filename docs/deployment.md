# Deployment Guide

## Production Deployment Options

### Docker Compose (Recommended)

#### Basic Production Setup

```bash
# Clone repository
git clone <your-repo-url>
cd Resource-Reserver

# Create production environment file
cat > .env << EOF
SECRET_KEY=your-very-secure-secret-key-here
POSTGRES_PASSWORD=your-secure-database-password
ENVIRONMENT=production
NODE_ENV=production
EOF

# Start with PostgreSQL
docker-compose --profile postgres up -d
```

#### Environment Configuration

Create `.env` file in project root:

```bash
# Security
SECRET_KEY=generate-a-secure-32-character-key
JWT_SECRET_KEY=another-secure-key-for-jwt-tokens

# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/resource_reserver
POSTGRES_PASSWORD=secure-database-password

# Application
ENVIRONMENT=production
NODE_ENV=production
API_BASE_URL=http://backend:8000

# Network
FRONTEND_PORT=3000
BACKEND_PORT=8000
```

#### SSL/HTTPS Setup with Nginx

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - frontend
    networks:
      - resource-reserver-network
```

### Kubernetes Deployment

#### Basic Kubernetes Manifests

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: resource-reserver
---
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: resource-reserver
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: resource-reserver-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: secret-key
```

### Cloud Platform Deployments

#### AWS ECS with Fargate

```json
{
  "family": "resource-reserver",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-account.dkr.ecr.region.amazonaws.com/resource-reserver-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://..."
        }
      ]
    }
  ]
}
```

#### Google Cloud Run

```yaml
# cloudrun-backend.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: resource-reserver-backend
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containers:
      - image: gcr.io/your-project/resource-reserver-backend
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              key: database-url
              name: app-secrets
        ports:
        - containerPort: 8000
```

### Database Options

#### PostgreSQL (Recommended for Production)

```bash
# Update docker-compose.yml environment
DATABASE_URL=postgresql://postgres:password@postgres:5432/resource_reserver

# Start with PostgreSQL
docker-compose --profile postgres up -d
```

#### Managed Database Services

**AWS RDS PostgreSQL**:
```bash
DATABASE_URL=postgresql://username:password@rds-endpoint.region.rds.amazonaws.com:5432/resource_reserver
```

**Google Cloud SQL**:
```bash
DATABASE_URL=postgresql://username:password@google-cloud-sql-ip:5432/resource_reserver
```

### Performance Optimization

#### Backend Scaling

```yaml
# docker-compose.override.yml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

#### Frontend Optimization

```dockerfile
# Dockerfile.frontend.prod
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

### Monitoring and Logging

#### Health Check Endpoints

- **Backend Health**: `GET /health`
- **Frontend Health**: `GET /` (should return 200)
- **Database Health**: Included in backend health check

#### Log Collection

```yaml
# docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### Prometheus Metrics (Optional)

```python
# Add to requirements.txt
prometheus-client==0.16.0

# Add to main.py
from prometheus_client import Counter, Histogram, generate_latest
request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
```

### Security Considerations

#### Environment Variables

Never commit sensitive data:
```bash
# .gitignore
.env
*.db
/data/
/logs/
```

#### Network Security

```yaml
# docker-compose.yml
networks:
  resource-reserver-network:
    driver: bridge
    internal: true  # Only for internal services
```

#### SSL/TLS Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;
    
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Backup and Recovery

#### Database Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U postgres resource_reserver > backup_$DATE.sql
```

#### Volume Backup

```bash
# Backup persistent data
docker run --rm -v resource-reserver_backend_data:/data -v $(pwd):/backup ubuntu tar czf /backup/data_backup.tar.gz /data
```

### Scaling Guidelines

#### Horizontal Scaling

- **Backend**: Can run multiple instances behind load balancer
- **Frontend**: Stateless, can scale infinitely
- **Database**: Use read replicas for read-heavy workloads

#### Vertical Scaling

- **Memory**: 512MB minimum, 2GB recommended for 1000+ resources
- **CPU**: 1 core minimum, 2+ cores for high concurrency
- **Storage**: 10GB minimum, grows with reservation history

### Troubleshooting Production Issues

#### Common Problems

**High Memory Usage**:
```bash
# Check container resources
docker stats

# Limit memory
docker-compose up -d --scale backend=2
```

**Database Connection Issues**:
```bash
# Check database connectivity
docker-compose exec backend python -c "from app.database import engine; engine.connect()"
```

**SSL Certificate Issues**:
```bash
# Verify certificates
openssl x509 -in certificate.crt -text -noout
```

Need more help? See our [troubleshooting guide](troubleshooting.md) or [API documentation](api-reference.md).