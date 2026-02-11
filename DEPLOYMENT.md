# StormOps v1 Deployment Guide

## Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Infrastructure                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐                                        │
│  │  Earth-2 API     │                                        │
│  │  (NVIDIA DGX)    │                                        │
│  └────────┬─────────┘                                        │
│           │                                                   │
│  ┌────────▼──────────────────────────────────────────┐      │
│  │  Lambda: earth2_ingestion                         │      │
│  │  (Pulls hail fields, densifies to DFW grid)      │      │
│  └────────┬───────────────────────────────────────────┘      │
│           │                                                   │
│  ┌────────▼──────────────────────────────────────────┐      │
│  │  RDS PostgreSQL + PostGIS                         │      │
│  │  (Parcels, impact_scores, leads, routes)         │      │
│  └────────┬───────────────────────────────────────────┘      │
│           │                                                   │
│  ┌────────▼──────────────────────────────────────────┐      │
│  │  Lambda: proposal_engine                          │      │
│  │  (Generates lead gen, route, SMS Proposals)      │      │
│  └────────┬───────────────────────────────────────────┘      │
│           │                                                   │
│  ┌────────▼──────────────────────────────────────────┐      │
│  │  Lambda: route_optimizer                          │      │
│  │  (Builds TSP-optimized routes)                   │      │
│  └────────┬───────────────────────────────────────────┘      │
│           │                                                   │
│  ┌────────▼──────────────────────────────────────────┐      │
│  │  Lambda: crm_integration                          │      │
│  │  (Pushes leads, routes to ServiceTitan)          │      │
│  └────────┬───────────────────────────────────────────┘      │
│           │                                                   │
│  ┌────────▼──────────────────────────────────────────┐      │
│  │  ECS: stormops_ui (Streamlit)                     │      │
│  │  (Dashboard for operators)                        │      │
│  └────────────────────────────────────────────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐       │
│  │  CloudWatch: Logs, Metrics, Alarms               │       │
│  └──────────────────────────────────────────────────┘       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## AWS Services

### RDS PostgreSQL
- **Instance:** db.r5.2xlarge (8 vCPU, 64 GB RAM)
- **Storage:** 500 GB gp3 (3000 IOPS)
- **Backup:** Daily snapshots, 30-day retention
- **Multi-AZ:** Yes (for HA)

### Lambda Functions
- **earth2_ingestion:** 3 GB memory, 15-min timeout, triggered every 15 min
- **proposal_engine:** 1 GB memory, 5-min timeout, triggered on demand
- **route_optimizer:** 2 GB memory, 10-min timeout, triggered on demand
- **crm_integration:** 1 GB memory, 5-min timeout, triggered on demand

### ECS (Streamlit UI)
- **Task:** 2 GB memory, 1 vCPU
- **Replicas:** 2 (for HA)
- **Load Balancer:** ALB with auto-scaling

### CloudWatch
- **Logs:** All Lambda and ECS logs
- **Metrics:** Latency, error rate, throughput
- **Alarms:** SLA breaches, database errors, forecast alerts

---

## Deployment Steps

### 1. Set Up RDS PostgreSQL

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier stormops-prod \
  --db-instance-class db.r5.2xlarge \
  --engine postgres \
  --master-username postgres \
  --master-user-password <password> \
  --allocated-storage 500 \
  --storage-type gp3 \
  --multi-az \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxx

# Wait for instance to be available
aws rds wait db-instance-available --db-instance-identifier stormops-prod

# Connect and load schema
psql -h stormops-prod.xxxxx.us-east-1.rds.amazonaws.com -U postgres -d stormops -f stormops_schema.sql
```

### 2. Deploy Lambda Functions

```bash
# Package earth2_ingestion
zip -r earth2_ingestion.zip earth2_ingestion.py sii_scorer.py

# Create Lambda function
aws lambda create-function \
  --function-name stormops-earth2-ingestion \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler earth2_ingestion.lambda_handler \
  --zip-file fileb://earth2_ingestion.zip \
  --timeout 900 \
  --memory-size 3008 \
  --environment Variables={DB_HOST=stormops-prod.xxxxx.rds.amazonaws.com,DB_NAME=stormops,DB_USER=postgres,DB_PASSWORD=<password>}

# Set up CloudWatch trigger (every 15 minutes)
aws events put-rule \
  --name stormops-earth2-ingestion-schedule \
  --schedule-expression "rate(15 minutes)"

aws events put-targets \
  --rule stormops-earth2-ingestion-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:stormops-earth2-ingestion"
```

### 3. Deploy ECS (Streamlit UI)

```bash
# Create ECR repository
aws ecr create-repository --repository-name stormops-ui

# Build Docker image
docker build -t stormops-ui:latest .
docker tag stormops-ui:latest ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/stormops-ui:latest
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/stormops-ui:latest

# Create ECS task definition
aws ecs register-task-definition \
  --family stormops-ui \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 1024 \
  --memory 2048 \
  --container-definitions file://task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster stormops-prod \
  --service-name stormops-ui \
  --task-definition stormops-ui \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/stormops-ui/xxxxx,containerName=stormops-ui,containerPort=8501
```

### 4. Set Up CloudWatch Alarms

```bash
# SLA breach alarm
aws cloudwatch put-metric-alarm \
  --alarm-name stormops-sla-breach \
  --alarm-description "Alert if SLA breaches exceed 10" \
  --metric-name SLABreaches \
  --namespace StormOps \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:stormops-alerts

# Database error alarm
aws cloudwatch put-metric-alarm \
  --alarm-name stormops-db-error \
  --alarm-description "Alert if database errors exceed 5" \
  --metric-name DatabaseErrors \
  --namespace StormOps \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:stormops-alerts
```

---

## Monitoring

### CloudWatch Dashboard

```bash
aws cloudwatch put-dashboard \
  --dashboard-name StormOps \
  --dashboard-body file://dashboard.json
```

### Key Metrics

- **Lead Generation Latency:** < 2 minutes
- **Route Building Latency:** < 5 minutes
- **CRM Sync Success Rate:** > 99%
- **SLA Compliance:** > 95% (first contact within 15 min)
- **Database CPU:** < 70%
- **Database Connections:** < 80

---

## Scaling

### Horizontal Scaling

- **Lambda:** Auto-scales based on concurrent executions
- **ECS:** Auto-scales based on CPU/memory utilization
- **RDS:** Read replicas for read-heavy workloads

### Vertical Scaling

- **RDS:** Upgrade to db.r5.4xlarge if CPU > 80%
- **Lambda:** Increase memory if duration > 80% of timeout
- **ECS:** Increase task CPU/memory if utilization > 80%

---

## Disaster Recovery

### Backup Strategy

- **RDS:** Automated daily snapshots, 30-day retention
- **Lambda:** Code stored in CodeCommit with versioning
- **ECS:** Task definitions versioned in ECR

### Recovery Procedures

1. **Database Failure:** Restore from latest RDS snapshot (< 5 min)
2. **Lambda Failure:** Automatic retry with exponential backoff
3. **ECS Failure:** Auto-scaling group replaces failed tasks

---

## Cost Estimation

| Service | Monthly Cost |
|---------|--------------|
| RDS PostgreSQL (db.r5.2xlarge) | $2,500 |
| Lambda (earth2_ingestion) | $200 |
| Lambda (proposal_engine) | $50 |
| Lambda (route_optimizer) | $100 |
| Lambda (crm_integration) | $50 |
| ECS (Streamlit UI, 2 tasks) | $300 |
| CloudWatch (logs, metrics) | $100 |
| **Total** | **~$3,300/month** |

---

## Security

### Network

- **VPC:** Private subnets for RDS, Lambda
- **Security Groups:** Restrict inbound to required ports
- **NAT Gateway:** For outbound internet access

### Authentication

- **RDS:** IAM database authentication
- **Lambda:** IAM roles with least privilege
- **ECS:** IAM task roles

### Encryption

- **RDS:** Encrypted at rest (KMS) and in transit (SSL)
- **Lambda:** Environment variables encrypted with KMS
- **ECS:** Secrets stored in AWS Secrets Manager

---

## Maintenance

### Weekly

- Review CloudWatch logs for errors
- Check database performance metrics
- Verify backup completion

### Monthly

- Update Lambda function code
- Review and optimize database queries
- Test disaster recovery procedures

### Quarterly

- Upgrade PostgreSQL minor version
- Review and update security groups
- Capacity planning review
