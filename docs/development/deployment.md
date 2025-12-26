# Deployment

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

## Production Configuration

1. Set `SECRET_KEY` to a secure random value
1. Use PostgreSQL for the database
1. Enable Redis caching
1. Configure SMTP for email
1. Set up HTTPS

## Health Checks

```bash
# Liveness probe
curl http://localhost:8000/live

# Readiness probe
curl http://localhost:8000/ready

# Detailed health
curl http://localhost:8000/health
```

## Scaling

The application supports horizontal scaling:

- Backend: Stateless, scale with load balancer
- Database: Use read replicas for scale
- Cache: Redis cluster for high availability
