# Customer Success Platform - Incident Response Runbook

## Table of Contents
1. [Overview](#overview)
2. [Incident Severity Levels](#incident-severity-levels)
3. [Incident Response Process](#incident-response-process)
4. [Common Incidents](#common-incidents)
5. [Troubleshooting Guides](#troubleshooting-guides)
6. [Emergency Procedures](#emergency-procedures)
7. [Escalation Matrix](#escalation-matrix)
8. [Post-Incident Review](#post-incident-review)

---

## Overview

This runbook provides step-by-step procedures for responding to incidents in the Customer Success Platform. It is designed for on-call engineers and operations teams.

### Quick Reference

| Issue | Page | Severity |
|-------|------|----------|
| API Down | [API Service Outage](#api-service-outage) | SEV-1 |
| Database Connection Issues | [Database Issues](#database-connection-issues) | SEV-1 |
| High Error Rate | [High Error Rate](#high-error-rate) | SEV-2 |
| Kafka Consumer Lag | [Kafka Consumer Lag](#kafka-consumer-lag) | SEV-2 |
| Slow Response Times | [Performance Degradation](#performance-degradation) | SEV-3 |
| Worker Not Processing | [Worker Issues](#worker-not-processing-messages) | SEV-2 |

### On-Call Contacts

- **Primary On-Call**: PagerDuty rotation
- **Platform Lead**: platform-lead@example.com
- **Database Admin**: dba@example.com
- **Security Team**: security@example.com
- **Executive Escalation**: cto@example.com

---

## Incident Severity Levels

### SEV-1: Critical (P1)
**Impact**: Complete service outage or data loss
**Response Time**: Immediate (< 15 minutes)
**Examples**:
- API completely down
- Database unavailable
- Data corruption
- Security breach

**Actions**:
- Page entire on-call team
- Create incident channel (#incident-YYYYMMDD-HHMM)
- Start incident bridge
- Notify leadership immediately

### SEV-2: High (P2)
**Impact**: Major functionality degraded
**Response Time**: < 30 minutes
**Examples**:
- High error rate (> 5%)
- Significant performance degradation
- One channel completely down
- Kafka consumer lag > 10,000 messages

**Actions**:
- Page primary on-call
- Create incident channel
- Notify stakeholders within 1 hour

### SEV-3: Medium (P3)
**Impact**: Minor functionality affected
**Response Time**: < 2 hours
**Examples**:
- Intermittent errors
- Slow response times
- Non-critical feature broken

**Actions**:
- Notify on-call via Slack
- Create ticket
- Fix during business hours

### SEV-4: Low (P4)
**Impact**: Minimal user impact
**Response Time**: Next business day
**Examples**:
- Cosmetic issues
- Logging errors
- Documentation updates

**Actions**:
- Create ticket
- Schedule fix

---

## Incident Response Process

### 1. Detection & Alert

**When you receive an alert**:
1. Acknowledge the alert in PagerDuty
2. Check monitoring dashboards
3. Determine severity level
4. Create incident channel if SEV-1 or SEV-2

### 2. Initial Assessment (First 5 Minutes)

```bash
# Quick health check
kubectl get pods -n customer-success
kubectl get svc -n customer-success
curl https://api.customer-success.example.com/health

# Check recent logs
kubectl logs -f deployment/customer-success-api -n customer-success --tail=100
kubectl logs -f deployment/customer-success-worker -n customer-success --tail=100

# Check metrics
# Open Grafana dashboard: https://grafana.example.com/d/customer-success
```

**Questions to answer**:
- Is the service up or down?
- What percentage of requests are failing?
- When did the issue start?
- Is it affecting all users or specific segments?
- Are there any recent deployments?

### 3. Communication

**Incident Channel Template**:
```
🚨 INCIDENT: [Brief Description]
Severity: SEV-X
Started: YYYY-MM-DD HH:MM UTC
Incident Commander: @username

Current Status:
- [What we know]
- [What we're investigating]
- [Current impact]

Next Update: [Time]
```

**Update Frequency**:
- SEV-1: Every 15 minutes
- SEV-2: Every 30 minutes
- SEV-3: Every 2 hours

### 4. Investigation & Mitigation

Follow the specific troubleshooting guide for the issue type (see below).

### 5. Resolution & Verification

```bash
# Verify health
curl https://api.customer-success.example.com/health

# Check error rates
# Monitor for 15 minutes to ensure stability

# Run smoke tests
pytest tests/test_multichannel_e2e.py::TestHealthCheck -v
```

### 6. Post-Incident

1. Mark incident as resolved
2. Schedule post-incident review within 48 hours
3. Update runbook with learnings
4. Create action items for prevention

---

## Common Incidents

### API Service Outage

**Symptoms**:
- Health check failing
- All API requests returning 5xx errors
- No pods running

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -n customer-success -l component=api

# Check recent events
kubectl get events -n customer-success --sort-by='.lastTimestamp' | head -20

# Check deployment status
kubectl describe deployment customer-success-api -n customer-success

# Check logs
kubectl logs deployment/customer-success-api -n customer-success --tail=200
```

**Common Causes & Solutions**:

#### 1. Image Pull Error
```bash
# Check image
kubectl describe pod <pod-name> -n customer-success | grep -A 5 "Events:"

# Solution: Fix image tag or registry credentials
kubectl set image deployment/customer-success-api \
  api=your-registry/customer-success/api:v1.0.0 \
  -n customer-success
```

#### 2. CrashLoopBackOff
```bash
# Check logs for crash reason
kubectl logs <pod-name> -n customer-success --previous

# Common causes:
# - Missing environment variables
# - Database connection failure
# - Invalid configuration

# Solution: Fix configuration and restart
kubectl rollout restart deployment/customer-success-api -n customer-success
```

#### 3. Resource Limits Exceeded
```bash
# Check resource usage
kubectl top pods -n customer-success

# Solution: Increase resource limits
kubectl edit deployment customer-success-api -n customer-success
# Update resources.limits.memory and resources.limits.cpu
```

#### 4. Liveness Probe Failing
```bash
# Check probe configuration
kubectl describe pod <pod-name> -n customer-success | grep -A 10 "Liveness:"

# Solution: Increase timeout or fix health endpoint
kubectl edit deployment customer-success-api -n customer-success
```

**Emergency Rollback**:
```bash
# Rollback to previous version
kubectl rollout undo deployment/customer-success-api -n customer-success

# Check rollout status
kubectl rollout status deployment/customer-success-api -n customer-success
```

---

### Database Connection Issues

**Symptoms**:
- API returning database connection errors
- Timeouts on database queries
- Connection pool exhausted

**Diagnosis**:
```bash
# Check database pod
kubectl get pods -n customer-success -l app=postgresql

# Check database logs
kubectl logs postgres-postgresql-0 -n customer-success --tail=100

# Test connection from API pod
kubectl exec -it <api-pod> -n customer-success -- \
  psql -h postgres-service -U postgres -d customer_success -c "SELECT 1;"

# Check connection pool
kubectl exec -it <api-pod> -n customer-success -- \
  python -c "import asyncpg; print('Connection test')"
```

**Common Causes & Solutions**:

#### 1. Database Pod Down
```bash
# Restart database
kubectl delete pod postgres-postgresql-0 -n customer-success

# Wait for pod to be ready
kubectl wait --for=condition=ready pod/postgres-postgresql-0 -n customer-success --timeout=300s
```

#### 2. Connection Pool Exhausted
```bash
# Check active connections
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"

# Increase pool size in ConfigMap
kubectl edit configmap customer-success-config -n customer-success
# Update DB_POOL_SIZE

# Restart API pods
kubectl rollout restart deployment/customer-success-api -n customer-success
```

#### 3. Database Disk Full
```bash
# Check disk usage
kubectl exec postgres-postgresql-0 -n customer-success -- df -h

# Solution: Expand PVC or clean up old data
kubectl edit pvc postgres-data -n customer-success
# Increase storage size

# Clean up old data
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success -c "DELETE FROM messages WHERE created_at < NOW() - INTERVAL '90 days';"
```

#### 4. Wrong Credentials
```bash
# Verify secret
kubectl get secret customer-success-secrets -n customer-success -o jsonpath='{.data.DB_PASSWORD}' | base64 -d

# Update secret if needed
kubectl create secret generic customer-success-secrets \
  --from-literal=DB_PASSWORD=<new-password> \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods
kubectl rollout restart deployment/customer-success-api -n customer-success
```

---

### High Error Rate

**Symptoms**:
- Error rate > 5%
- Increased 5xx responses
- Alerts from monitoring

**Diagnosis**:
```bash
# Check error logs
kubectl logs deployment/customer-success-api -n customer-success | grep ERROR | tail -50

# Check metrics
# Open Grafana: Error Rate dashboard

# Check recent deployments
kubectl rollout history deployment/customer-success-api -n customer-success

# Check external dependencies
curl https://api.openai.com/v1/models
curl https://api.twilio.com/2010-04-01/Accounts.json
```

**Common Causes & Solutions**:

#### 1. OpenAI API Issues
```bash
# Check OpenAI status
curl https://status.openai.com/api/v2/status.json

# Solution: Implement retry logic or use fallback
# Temporary: Increase timeout in ConfigMap
kubectl edit configmap customer-success-config -n customer-success
```

#### 2. Rate Limiting
```bash
# Check rate limit headers in logs
kubectl logs deployment/customer-success-api -n customer-success | grep "rate limit"

# Solution: Implement backoff or increase limits
# Contact OpenAI/Twilio for limit increase
```

#### 3. Bad Deployment
```bash
# Rollback immediately
kubectl rollout undo deployment/customer-success-api -n customer-success

# Verify error rate drops
# Monitor for 10 minutes
```

#### 4. Memory Leak
```bash
# Check memory usage
kubectl top pods -n customer-success

# Restart pods with high memory
kubectl delete pod <pod-name> -n customer-success

# If persistent, rollback and investigate
```

---

### Kafka Consumer Lag

**Symptoms**:
- Consumer lag > 10,000 messages
- Messages not being processed
- Alerts from Kafka monitoring

**Diagnosis**:
```bash
# Check consumer lag
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group message-processor

# Check worker pods
kubectl get pods -n customer-success -l component=worker

# Check worker logs
kubectl logs deployment/customer-success-worker -n customer-success --tail=100
```

**Common Causes & Solutions**:

#### 1. Workers Down
```bash
# Restart workers
kubectl rollout restart deployment/customer-success-worker -n customer-success

# Scale up workers temporarily
kubectl scale deployment/customer-success-worker --replicas=8 -n customer-success
```

#### 2. Slow Processing
```bash
# Check processing time in logs
kubectl logs deployment/customer-success-worker -n customer-success | grep "processing_time"

# Solution: Optimize agent or scale up
kubectl scale deployment/customer-success-worker --replicas=6 -n customer-success
```

#### 3. Kafka Broker Issues
```bash
# Check Kafka brokers
kubectl get pods -n customer-success -l app.kubernetes.io/name=kafka

# Restart Kafka if needed
kubectl delete pod customer-success-kafka-kafka-0 -n customer-success
```

#### 4. Dead Letter Queue Full
```bash
# Check DLQ
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic dead-letter-queue \
  --from-beginning \
  --max-messages 10

# Investigate failed messages and fix root cause
```

---

### Worker Not Processing Messages

**Symptoms**:
- Messages in Kafka but not being processed
- No worker logs
- Consumer group not active

**Diagnosis**:
```bash
# Check worker pods
kubectl get pods -n customer-success -l component=worker

# Check worker logs
kubectl logs deployment/customer-success-worker -n customer-success --tail=200

# Check consumer group
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --list
```

**Solutions**:

#### 1. Worker Crashed
```bash
# Check crash reason
kubectl logs <worker-pod> -n customer-success --previous

# Restart workers
kubectl rollout restart deployment/customer-success-worker -n customer-success
```

#### 2. Configuration Error
```bash
# Check environment variables
kubectl exec <worker-pod> -n customer-success -- env | grep KAFKA

# Fix ConfigMap
kubectl edit configmap customer-success-config -n customer-success

# Restart workers
kubectl rollout restart deployment/customer-success-worker -n customer-success
```

#### 3. Consumer Group Stuck
```bash
# Reset consumer group offsets
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- \
  bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group message-processor \
  --reset-offsets \
  --to-latest \
  --topic customer-messages \
  --execute
```

---

### Performance Degradation

**Symptoms**:
- Response times > 2 seconds (p95)
- Slow API responses
- Timeouts

**Diagnosis**:
```bash
# Check response times
# Open Grafana: API Performance dashboard

# Check resource usage
kubectl top pods -n customer-success

# Check database performance
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check for slow queries
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds';"
```

**Solutions**:

#### 1. High CPU Usage
```bash
# Scale up API pods
kubectl scale deployment/customer-success-api --replicas=8 -n customer-success

# Or increase CPU limits
kubectl edit deployment customer-success-api -n customer-success
```

#### 2. Database Slow Queries
```bash
# Kill slow queries
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -c "SELECT pg_terminate_backend(<pid>);"

# Add missing indexes (if identified)
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success -c "CREATE INDEX CONCURRENTLY idx_messages_conversation_sent ON messages(conversation_id, sent_at);"
```

#### 3. Memory Pressure
```bash
# Restart pods to clear memory
kubectl rollout restart deployment/customer-success-api -n customer-success

# Increase memory limits if needed
kubectl edit deployment customer-success-api -n customer-success
```

#### 4. External API Slow
```bash
# Check OpenAI response times in logs
kubectl logs deployment/customer-success-api -n customer-success | grep "openai"

# Implement caching or increase timeout
```

---

## Emergency Procedures

### Complete System Shutdown

**When to use**: Security breach, data corruption, or critical bug

```bash
# 1. Stop all traffic
kubectl scale deployment/customer-success-api --replicas=0 -n customer-success

# 2. Stop workers
kubectl scale deployment/customer-success-worker --replicas=0 -n customer-success

# 3. Update ingress to show maintenance page
kubectl patch ingress customer-success-ingress -n customer-success \
  --type=json \
  -p='[{"op": "add", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1default-backend", "value": "maintenance-page"}]'

# 4. Notify all stakeholders
# Post in #incidents and #customer-success

# 5. Investigate and fix issue

# 6. Restore service (reverse above steps)
```

### Emergency Rollback

```bash
# Rollback API
kubectl rollout undo deployment/customer-success-api -n customer-success

# Rollback Worker
kubectl rollout undo deployment/customer-success-worker -n customer-success

# Verify rollback
kubectl rollout status deployment/customer-success-api -n customer-success
kubectl rollout status deployment/customer-success-worker -n customer-success

# Test health
curl https://api.customer-success.example.com/health
```

### Database Emergency Recovery

```bash
# 1. Stop all applications
kubectl scale deployment/customer-success-api --replicas=0 -n customer-success
kubectl scale deployment/customer-success-worker --replicas=0 -n customer-success

# 2. Backup current state
kubectl exec postgres-postgresql-0 -n customer-success -- \
  pg_dump -U postgres customer_success | gzip > emergency-backup-$(date +%Y%m%d-%H%M%S).sql.gz

# 3. Restore from backup
gunzip < backup-YYYYMMDD.sql.gz | \
  kubectl exec -i postgres-postgresql-0 -n customer-success -- \
  psql -U postgres customer_success

# 4. Verify data integrity
kubectl exec postgres-postgresql-0 -n customer-success -- \
  psql -U postgres -d customer_success -c "SELECT COUNT(*) FROM customers;"

# 5. Restart applications
kubectl scale deployment/customer-success-api --replicas=3 -n customer-success
kubectl scale deployment/customer-success-worker --replicas=2 -n customer-success
```

---

## Escalation Matrix

### Level 1: On-Call Engineer
**Handles**: SEV-3, SEV-4, initial response to all incidents
**Escalate to Level 2 if**:
- Unable to resolve within 30 minutes
- SEV-1 or SEV-2 incident
- Requires database changes
- Security concern

### Level 2: Platform Lead
**Handles**: SEV-2, complex technical issues
**Escalate to Level 3 if**:
- SEV-1 incident
- Data loss or corruption
- Security breach
- Requires architectural changes

### Level 3: Engineering Leadership
**Handles**: SEV-1, critical decisions
**Escalate to Level 4 if**:
- Customer data breach
- Legal implications
- Extended outage (> 4 hours)

### Level 4: Executive Team
**Handles**: Business impact, customer communication, legal issues

---

## Post-Incident Review

### Timeline (Within 48 Hours)

1. **Schedule Review Meeting** (1 hour)
   - Invite: Incident Commander, On-Call, Platform Lead, Stakeholders

2. **Prepare Incident Report**
   - Timeline of events
   - Root cause analysis
   - Impact assessment
   - Action items

3. **Conduct Review**
   - What happened?
   - What went well?
   - What could be improved?
   - What are we going to do about it?

### Incident Report Template

```markdown
# Incident Report: [Brief Description]

## Summary
- **Incident ID**: INC-YYYYMMDD-NNN
- **Severity**: SEV-X
- **Duration**: X hours Y minutes
- **Impact**: [Description]
- **Root Cause**: [Description]

## Timeline
- HH:MM - [Event]
- HH:MM - [Event]
- HH:MM - [Resolution]

## Root Cause Analysis
[Detailed explanation]

## Impact
- Users affected: X
- Requests failed: Y
- Revenue impact: $Z

## What Went Well
- [Item]

## What Could Be Improved
- [Item]

## Action Items
- [ ] [Action] - Owner: @username - Due: YYYY-MM-DD
- [ ] [Action] - Owner: @username - Due: YYYY-MM-DD

## Lessons Learned
[Key takeaways]
```

---

## Appendix

### Useful Commands Cheat Sheet

```bash
# Quick health check
kubectl get pods -n customer-success && curl https://api.customer-success.example.com/health

# Tail all logs
kubectl logs -f deployment/customer-success-api -n customer-success --all-containers=true

# Restart everything
kubectl rollout restart deployment/customer-success-api deployment/customer-success-worker -n customer-success

# Check resource usage
kubectl top pods -n customer-success && kubectl top nodes

# Get recent events
kubectl get events -n customer-success --sort-by='.lastTimestamp' | head -20

# Port forward for debugging
kubectl port-forward svc/customer-success-api 8000:80 -n customer-success

# Execute SQL query
kubectl exec postgres-postgresql-0 -n customer-success -- psql -U postgres -d customer_success -c "SELECT COUNT(*) FROM messages WHERE created_at > NOW() - INTERVAL '1 hour';"

# Check Kafka consumer lag
kubectl exec -it customer-success-kafka-kafka-0 -n customer-success -- bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group message-processor
```

### Monitoring Dashboards

- **API Performance**: https://grafana.example.com/d/api-performance
- **Worker Performance**: https://grafana.example.com/d/worker-performance
- **Database Performance**: https://grafana.example.com/d/database-performance
- **Kafka Performance**: https://grafana.example.com/d/kafka-performance
- **Business Metrics**: https://grafana.example.com/d/business-metrics

### External Status Pages

- **OpenAI**: https://status.openai.com
- **Twilio**: https://status.twilio.com
- **Google Workspace**: https://www.google.com/appsstatus

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-03-15  
**Maintained By**: Platform Team  
**Review Frequency**: Quarterly or after each SEV-1/SEV-2 incident
