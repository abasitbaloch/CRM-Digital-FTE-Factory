# Quick Start Guide

Get the Customer Success Platform running in 5 minutes.

## Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ installed
- OpenAI API key

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/customer-success-platform.git
cd customer-success-platform

# Run setup script (Linux/Mac)
./setup.sh

# Or manually:
cp .env.example .env
pip install -r production/requirements.txt
```

## Step 2: Configure Environment

Edit `.env` and add your API keys:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (for full functionality)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
```

## Step 3: Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Wait for services to be ready (30 seconds)
sleep 30

# Check health
curl http://localhost:8000/health
```

## Step 4: Test the API

### Submit a Support Request

```bash
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "subject": "Test Request",
    "message": "This is a test support request",
    "category": "technical"
  }'
```

### Check Ticket Status

```bash
# Use the ticket_id from the response above
curl http://localhost:8000/support/ticket/TKT_000001
```

### View API Documentation

Open in browser: http://localhost:8000/docs

## Step 5: Run Tests

```bash
# Run E2E tests
pytest production/tests/test_multichannel_e2e.py -v

# Run load tests
locust -f production/tests/load_test.py --host=http://localhost:8000
```

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Check service status
docker-compose ps

# Access database
docker exec -it customer-success-postgres psql -U postgres -d customer_success
```

## Troubleshooting

### Services not starting?

```bash
# Check Docker logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d
```

### API returning errors?

```bash
# Check API logs
docker-compose logs api

# Verify environment variables
docker-compose exec api env | grep OPENAI
```

### Database connection issues?

```bash
# Check PostgreSQL
docker-compose logs postgres

# Test connection
docker exec -it customer-success-postgres psql -U postgres -c "SELECT 1;"
```

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Read Documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
3. **Review Architecture**: See [README.md](README.md) for system overview
4. **Incident Response**: See [RUNBOOK.md](RUNBOOK.md) for troubleshooting

## Production Deployment

For production deployment to Kubernetes:

```bash
# Deploy to Kubernetes
make k8s-deploy

# Check status
kubectl get pods -n customer-success

# View logs
kubectl logs -f deployment/customer-success-api -n customer-success
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production deployment guide.

## Support

- **Documentation**: See docs/ directory
- **Issues**: GitHub Issues
- **Email**: platform-team@example.com

---

**You're ready to go! 🚀**
