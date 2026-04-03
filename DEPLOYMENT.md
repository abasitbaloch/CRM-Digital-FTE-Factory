# Customer Success Platform - Deployment & Operations Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Environment Setup](#environment-setup)
4. [Database Setup](#database-setup)
5. [Kafka Setup](#kafka-setup)
6. [Application Deployment](#application-deployment)
7. [Kubernetes Deployment](#kubernetes-deployment)
8. [Configuration Management](#configuration-management)
9. [Monitoring & Observability](#monitoring--observability)
10. [Scaling Guidelines](#scaling-guidelines)
11. [Backup & Recovery](#backup--recovery)
12. [Security Considerations](#security-considerations)

---

## Prerequisites

### Required Software
- **Kubernetes**: v1.24+
- **PostgreSQL**: v14+ with pgvector extension
- **Kafka**: v3.0+
- **Docker**: v20.10+
- **Python**: 3.11+
- **kubectl**: Latest stable version
- **Helm**: v3.0+ (optional, for package management)

### Required Accounts & Credentials
- OpenAI API key (GPT-4 access)
- Twilio account (for WhatsApp)
- Google Cloud service account (for Gmail)
- Container registry access (Docker Hub, GCR, ECR, etc.)

### Infrastructure Requirements
- **Minimum**: 3 nodes, 8 vCPU, 32GB RAM total
- **Recommended**: 5 nodes, 16 vCPU, 64GB RAM total
- **Storage**: 100GB+ for database, 50GB+ for Kafka
- **Network**: Load balancer with SSL termination

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                         │
│                     (Ingress Controller)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
    ┌────▼─────┐                   ┌────▼─────┐
    │   API    │                   │   API    │
    │  Pods    │                   │  Pods    │
    │ (3-10)   │                   │ (3-10)   │
    └────┬─────┘                   └────┬─────┘
         │                               │
         └───────────────┬───────────────┘
                         │
              ┌──────────▼──────────┐
              │       Kafka         │
              │   (Message Queue)   │
              └──────────┬──────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
    ┌────▼─────┐                   ┌────▼─────┐
    │  Worker  │                   │  Worker  │
    │  Pods    │                   │  Pods    │
    │  (2-8)   │                   │  (2-8)   │
    └────┬─────┘                   └────┬─────┘
         │                               │
         └───────────────┬───────────────┘
                         │
              ┌──────────▼──────────┐
              │    PostgreSQL       │
              │   (with pgvector)   │
              └─────────────────────┘
```

### Components
- **API Service**: FastAPI application handling webhooks and REST endpoints
- **Worker Service**: Message processor consuming from Kafka
- **PostgreSQL**: Primary data store with vector search
- **Kafka**: Event streaming and message queue
- **Ingress**: NGINX ingress controller with TLS

---

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/customer-success-platform.git
cd customer-success-platform
```

### 2. Create Environment Files

Create `.env.production`:
```bash
# Database
DB_HOST=postgres-service.customer-success.svc.cluster.local
DB_PORT=5432
DB_NAME=customer_success
DB_USER=postgres
DB_PASSWORD=<secure-password>

# OpenAI
OPENAI_API_KEY=sk-<your-key>
AGENT_MODEL=gpt-4-turbo-preview

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka-service.customer-success.svc.cluster.local:9092

# Twilio
TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Gmail
GMAIL_SERVICE_ACCOUNT_FILE=/secrets/gmail-service-account.json
GMAIL_DELEGATED_EMAIL=support@example.com

# API
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

### 3. Build Docker Images

```bash
# Build API image
docker build -t customer-success/api:latest -f Dockerfile.api .

# Build Worker image
docker build -t customer-success/worker:latest -f Dockerfile.worker .

# Tag and push to registry
docker tag customer-success/api:latest your-registry/customer-success/api:v1.0.0
docker push your-registry/customer-success/api:v1.0.0

docker tag customer-success/worker:latest your-registry/customer-success/worker:v1.0.0
docker push your-registry/customer-success/worker:v1.0.0
```

---

## Database Setup

### 1. Install PostgreSQL with pgvector

```bash
# Using Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgres bitnami/postgresql \
  --namespace customer-success \
  --set auth.postgresPassword=<secure-password> \
  --set primary.persistence.size=100Gi \
  --set image.tag=14
```

### 2. Enable pgvector Extension

```bash
# Connect to database
kubectl exec -it postgres-postgresql-0 -n customer-success -- psql -U postgres

# Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 3. Initialize Schema

```bash
# Apply schema
kubectl exec -i postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success < production/database/schema.sql
```

### 4. Verify Installation

```bash
# Check tables
kubectl exec -it postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success -c "\dt"

# Check extensions
kubectl exec -it postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success -c "\dx"
```

---

## Kafka Setup

### 1. Install Kafka

```bash
# Using Strimzi operator
kubectl create namespace kafka
kubectl create -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka

# Create Kafka cluster
cat <<EOF | kubectl apply -f -
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: customer-success-kafka
  namespace: customer-success
spec:
  kafka:
    version: 3.5.0
    replicas: 3
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
    storage:
      type: persistent-claim
      size: 50Gi
  zookeeper:
    replicas: 3
    storage:
      type: persistent-claim
      size: 10Gi
EOF
```

### 2. Create Topics

```bash
# Create topics
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic customer-messages \
  --partitions 6 \
  --replication-factor 3

kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic agent-metrics \
  --partitions 3 \
  --replication-factor 3

kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic escalations \
  --partitions 3 \
  --replication-factor 3
```

### 3. Verify Topics

```bash
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

---

## Application Deployment

### Local Development

```bash
# Install dependencies
pip install -r production/requirements.txt

# Run database migrations
python -m production.database.migrate

# Start API server
uvicorn production.api.main:app --reload --host 0.0.0.0 --port 8000

# Start worker (in separate terminal)
python -m production.workers.message_processor
```

### Docker Compose (Testing)

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api
docker-compose logs -f worker

# Stop services
docker-compose down
```

---

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl apply -f production/k8s/namespace.yaml
```

### 2. Create Secrets

```bash
# Update secrets with actual values
kubectl apply -f production/k8s/secrets.yaml

# Verify secrets
kubectl get secrets -n customer-success
```

### 3. Apply ConfigMap

```bash
kubectl apply -f production/k8s/configmap.yaml
```

### 4. Deploy Applications

```bash
# Deploy API
kubectl apply -f production/k8s/deployment-api.yaml

# Deploy Workers
kubectl apply -f production/k8s/deployment-worker.yaml

# Create Services
kubectl apply -f production/k8s/service.yaml

# Create Ingress
kubectl apply -f production/k8s/ingress.yaml

# Apply HPA
kubectl apply -f production/k8s/hpa.yaml
```

### 5. Verify Deployment

```bash
# Check pods
kubectl get pods -n customer-success

# Check services
kubectl get svc -n customer-success

# Check ingress
kubectl get ingress -n customer-success

# Check logs
kubectl logs -f deployment/customer-success-api -n customer-success
kubectl logs -f deployment/customer-success-worker -n customer-success
```

### 6. Test Deployment

```bash
# Port forward for testing
kubectl port-forward svc/customer-success-api 8000:80 -n customer-success

# Test health endpoint
curl http://localhost:8000/health

# Test API
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test",
    "message": "Testing deployment"
  }'
```

---

## Configuration Management

### Environment Variables

All configuration is managed through:
1. **ConfigMap**: Non-sensitive configuration
2. **Secrets**: Sensitive credentials
3. **Environment variables**: Runtime configuration

### Updating Configuration

```bash
# Update ConfigMap
kubectl edit configmap customer-success-config -n customer-success

# Restart pods to pick up changes
kubectl rollout restart deployment/customer-success-api -n customer-success
kubectl rollout restart deployment/customer-success-worker -n customer-success
```

### Feature Flags

Feature flags are stored in ConfigMap:
```yaml
ENABLE_METRICS: "true"
ENABLE_TRACING: "false"
ENABLE_EXPERIMENTAL_FEATURES: "false"
```

---

## Monitoring & Observability

### Metrics

**Prometheus Integration**:
```bash
# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# ServiceMonitor for API
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: customer-success-api
  namespace: customer-success
spec:
  selector:
    matchLabels:
      app: customer-success
      component: api
  endpoints:
  - port: http
    path: /metrics
EOF
```

**Key Metrics to Monitor**:
- Request rate (requests/sec)
- Response time (p50, p95, p99)
- Error rate (%)
- Agent processing time
- Kafka consumer lag
- Database connection pool usage
- Memory and CPU usage

### Logging

**Centralized Logging with ELK**:
```bash
# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

# Install Kibana
helm install kibana elastic/kibana --namespace logging

# Install Filebeat
helm install filebeat elastic/filebeat --namespace logging
```

**Log Levels**:
- `DEBUG`: Development only
- `INFO`: Normal operations (default)
- `WARNING`: Potential issues
- `ERROR`: Errors requiring attention
- `CRITICAL`: System failures

### Tracing

**Jaeger Integration**:
```bash
# Install Jaeger
kubectl create namespace observability
kubectl apply -f https://raw.githubusercontent.com/jaegertracing/jaeger-operator/main/deploy/crds/jaegertracing.io_jaegers_crd.yaml
kubectl apply -f https://raw.githubusercontent.com/jaegertracing/jaeger-operator/main/deploy/service_account.yaml
kubectl apply -f https://raw.githubusercontent.com/jaegertracing/jaeger-operator/main/deploy/role.yaml
kubectl apply -f https://raw.githubusercontent.com/jaegertracing/jaeger-operator/main/deploy/role_binding.yaml
kubectl apply -f https://raw.githubusercontent.com/jaegertracing/jaeger-operator/main/deploy/operator.yaml
```

### Dashboards

**Grafana Dashboards**:
1. **API Performance**: Request rates, latency, errors
2. **Worker Performance**: Message processing, queue depth
3. **Database Performance**: Query time, connections, cache hit rate
4. **Kafka Performance**: Consumer lag, throughput
5. **Business Metrics**: Tickets created, escalations, resolution time

---

## Scaling Guidelines

### Horizontal Scaling

**API Pods**:
- **Light load** (< 100 req/s): 3 pods
- **Medium load** (100-500 req/s): 5-7 pods
- **Heavy load** (> 500 req/s): 8-10 pods

**Worker Pods**:
- **Light load** (< 50 msg/s): 2 pods
- **Medium load** (50-200 msg/s): 4-6 pods
- **Heavy load** (> 200 msg/s): 6-8 pods

### Vertical Scaling

**Resource Adjustments**:
```yaml
# API pods
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"

# Worker pods
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

### Database Scaling

**Read Replicas**:
```bash
# Add read replica
kubectl scale statefulset postgres-postgresql --replicas=2 -n customer-success
```

**Connection Pooling**:
- Use PgBouncer for connection pooling
- Recommended pool size: 20-50 connections per pod

### Kafka Scaling

**Add Partitions**:
```bash
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-topics.sh --alter \
  --bootstrap-server localhost:9092 \
  --topic customer-messages \
  --partitions 12
```

---

## Backup & Recovery

### Database Backups

**Automated Backups**:
```bash
# Daily backup cron job
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: customer-success
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:14
            command:
            - /bin/sh
            - -c
            - pg_dump -h postgres-postgresql -U postgres customer_success | gzip > /backup/backup-\$(date +%Y%m%d).sql.gz
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: postgres-backup-pvc
          restartPolicy: OnFailure
EOF
```

**Manual Backup**:
```bash
kubectl exec postgres-postgresql-0 -n customer-success -- \
  pg_dump -U postgres customer_success | gzip > backup-$(date +%Y%m%d).sql.gz
```

**Restore**:
```bash
gunzip < backup-20240315.sql.gz | \
  kubectl exec -i postgres-postgresql-0 -n customer-success -- \
  psql -U postgres customer_success
```

### Kafka Backups

**Topic Snapshots**:
```bash
# Export topic data
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic customer-messages \
  --from-beginning \
  --max-messages 10000 > messages-backup.json
```

### Disaster Recovery

**Recovery Time Objective (RTO)**: 1 hour
**Recovery Point Objective (RPO)**: 24 hours

**Recovery Steps**:
1. Restore database from latest backup
2. Recreate Kafka topics
3. Redeploy applications
4. Verify health checks
5. Resume traffic

---

## Security Considerations

### Network Security
- Use network policies to restrict pod communication
- Enable TLS for all external communication
- Use private subnets for database and Kafka

### Secrets Management
- Use Kubernetes secrets with encryption at rest
- Rotate secrets regularly (90 days)
- Use external secret managers (AWS Secrets Manager, HashiCorp Vault)

### API Security
- Rate limiting: 100 req/min per IP
- Authentication for admin endpoints
- CORS configuration for allowed origins
- Input validation on all endpoints

### Database Security
- Use strong passwords (16+ characters)
- Enable SSL connections
- Restrict network access
- Regular security updates

### Compliance
- GDPR: Data deletion requests handled via escalations
- SOC 2: Audit logs enabled
- HIPAA: Encryption at rest and in transit (if applicable)

---

## Maintenance

### Regular Tasks

**Daily**:
- Check error logs
- Monitor alert dashboard
- Review escalations

**Weekly**:
- Review performance metrics
- Check disk usage
- Update dependencies (security patches)

**Monthly**:
- Review and optimize database queries
- Clean up old data (messages > 90 days)
- Review and update documentation
- Conduct security audit

### Upgrades

**Rolling Update**:
```bash
# Update API
kubectl set image deployment/customer-success-api \
  api=your-registry/customer-success/api:v1.1.0 \
  -n customer-success

# Monitor rollout
kubectl rollout status deployment/customer-success-api -n customer-success

# Rollback if needed
kubectl rollout undo deployment/customer-success-api -n customer-success
```

---

## Support & Troubleshooting

### Common Issues

See [RUNBOOK.md](./RUNBOOK.md) for detailed troubleshooting procedures.

### Getting Help

- **Documentation**: https://docs.example.com
- **Slack**: #customer-success-platform
- **On-call**: PagerDuty rotation
- **Email**: platform-team@example.com

---

## Appendix

### Useful Commands

```bash
# Get all resources
kubectl get all -n customer-success

# Describe pod
kubectl describe pod <pod-name> -n customer-success

# Get logs
kubectl logs -f <pod-name> -n customer-success

# Execute command in pod
kubectl exec -it <pod-name> -n customer-success -- /bin/bash

# Port forward
kubectl port-forward svc/customer-success-api 8000:80 -n customer-success

# Scale deployment
kubectl scale deployment/customer-success-api --replicas=5 -n customer-success

# Delete pod (will be recreated)
kubectl delete pod <pod-name> -n customer-success
```

### Resource Limits

| Component | Min CPU | Max CPU | Min Memory | Max Memory |
|-----------|---------|---------|------------|------------|
| API Pod   | 500m    | 2000m   | 512Mi      | 2Gi        |
| Worker Pod| 1000m   | 4000m   | 1Gi        | 4Gi        |
| PostgreSQL| 2000m   | 4000m   | 4Gi        | 8Gi        |
| Kafka     | 1000m   | 2000m   | 2Gi        | 4Gi        |

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-03-15  
**Maintained By**: Platform Team
