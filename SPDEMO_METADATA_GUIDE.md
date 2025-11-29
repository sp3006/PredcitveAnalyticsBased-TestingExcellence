# Metadata Collection Guidelines for AI Predictions

## Overview

This guide explains what metadata to collect, how to collect it, and where to store it for AI-powered job failure predictions.

---

## 1. Required Metadata Categories

### 1.1 Job Execution History

**What to Collect:**
```json
{
  "job_id": "unique-id",
  "job_name": "job-name",
  "execution_date": "2025-11-29T02:00:00Z",
  "status": "SUCCESS|FAILED|RUNNING",
  "duration_minutes": 45,
  "failure_reason": "OOMKilled|MountFailure|etc",
  "error_details": {
    "type": "error-type",
    "message": "error-message",
    "exit_code": 137
  },
  "resources_used": {
    "peak_memory_gb": 12.5,
    "avg_cpu_cores": 2.8,
    "peak_cpu_cores": 3.9,
    "storage_used_gb": 85
  },
  "input_data": {
    "row_count": 4500000,
    "size_gb": 48,
    "duplicate_rate": 0.02,
    "source_tables": ["table1", "table2"]
  },
  "output_data": {
    "row_count": 4410000,
    "size_gb": 12
  }
}
```

**How to Collect:**
```bash
# From Kubernetes
kubectl get jobs -n abinitio-prod -o json > jobs.json

# From CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/eks/abinitio \
  --filter-pattern "job_execution" \
  --start-time $(date -d '30 days ago' +%s)000 > logs.json

# From Prometheus metrics
curl http://prometheus:9090/api/v1/query \
  -d 'query=container_memory_usage_bytes{pod=~"abinitio.*"}' > metrics.json
```

**Storage:** S3 + DynamoDB (see Section 3)

**Retention:**
- S3: 2 years (with lifecycle policy)
- DynamoDB: 90 days (hot data)

### 1.2 EKS Cluster State

**What to Collect:**
```json
{
  "cluster_name": "bi-abi-apps-prod",
  "timestamp": "2025-11-29T10:00:00Z",
  "node_groups": [
    {
      "name": "data-processing-ng",
      "instance_type": "r5.4xlarge",
      "desired_capacity": 3,
      "available_cpu": 20,
      "available_memory_gi": 280
    }
  ],
  "resource_quotas": {
    "abinitio-prod": {
      "cpu_limit": "40",
      "memory_limit": "320Gi",
      "cpu_used": "15",
      "memory_used": "100Gi"
    }
  },
  "csi_drivers": ["efs.csi.aws.com", "ebs.csi.aws.com"],
  "pending_pvcs": []
}
```

**How to Collect:**
```bash
# Cluster info
aws eks describe-cluster --name bi-abi-apps-prod > cluster.json

# Node groups
aws eks list-nodegroups --cluster-name bi-abi-apps-prod
aws eks describe-nodegroup --cluster-name bi-abi-apps-prod --nodegroup-name ng-1

# Resource availability
kubectl top nodes --no-headers > nodes_usage.txt

# CSI drivers
kubectl get csidriver -o json > csi_drivers.json

# Resource quotas
kubectl get resourcequota -n abinitio-prod -o json > quotas.json
```

**Storage:** DynamoDB (time-series data)

**Frequency:** Every 5 minutes

### 1.3 Storage Configuration (EFS, FSx, S3)

**What to Collect:**
```json
{
  "efs_filesystems": [
    {
      "filesystem_id": "fs-0abc123",
      "name": "abinitio-data",
      "size_gb": 500,
      "performance_mode": "generalPurpose",
      "throughput_mode": "bursting",
      "encrypted": true,
      "mount_targets": 3,
      "security_groups": ["sg-efs-123"]
    }
  ],
  "s3_buckets": [
    {
      "name": "abinitio-source-data",
      "region": "us-east-1",
      "encrypted": true,
      "versioning": true,
      "lifecycle_rules": [...]
    }
  ]
}
```

**How to Collect:**
```bash
# EFS
aws efs describe-file-systems > efs.json
aws efs describe-mount-targets --file-system-id fs-0abc123 > mount_targets.json

# S3
aws s3api list-buckets > buckets.json
aws s3api get-bucket-encryption --bucket abinitio-source-data > encryption.json
aws s3api get-bucket-versioning --bucket abinitio-source-data > versioning.json

# Security Groups
aws ec2 describe-security-groups --group-ids sg-efs-123 > sg.json
```

**Storage:** S3 (configuration snapshots)

**Frequency:** Daily or on change

### 1.4 IAM/IRSA Configuration

**What to Collect:**
```json
{
  "service_accounts": {
    "abinitio-batch-sa": {
      "namespace": "abinitio-prod",
      "iam_role_arn": "arn:aws:iam::123456789012:role/eks-abinitio-batch-role",
      "policies": [
        {
          "name": "S3Access",
          "actions": ["s3:GetObject", "s3:PutObject"],
          "resources": ["arn:aws:s3:::abinitio-source-data/*"]
        }
      ]
    }
  },
  "trust_relationships": [...],
  "access_denied_errors": 3
}
```

**How to Collect:**
```bash
# ServiceAccount
kubectl get sa abinitio-batch-sa -n abinitio-prod -o json > sa.json

# IAM Role
aws iam get-role --role-name eks-abinitio-batch-role > role.json

# Attached Policies
aws iam list-attached-role-policies --role-name eks-abinitio-batch-role > policies.json

# Policy Documents
aws iam get-policy-version \
  --policy-arn arn:aws:iam::123456789012:policy/S3Access \
  --version-id v1 > policy.json

# Access Denied Errors from CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AccessDenied \
  --max-results 100 > access_denied.json
```

**Storage:** DynamoDB + S3 (configuration + events)

**Frequency:**
- Configuration: Daily
- Access denied events: Real-time streaming

### 1.5 Graph Metadata

**What to Collect:**
```json
{
  "graph_name": "customer_daily_agg",
  "graph_file": "customer_daily_agg.mp",
  "components": [
    {"type": "input", "name": "read_data"},
    {"type": "sort", "name": "sort_by_key"},
    {"type": "join", "name": "join_lookup"},
    {"type": "aggregate", "name": "summarize"},
    {"type": "output", "name": "write_results"}
  ],
  "complexity_metrics": {
    "num_components": 8,
    "num_sorts": 2,
    "num_joins": 1,
    "num_aggregations": 1,
    "parallelism": 2,
    "max_partition_count": 4
  },
  "estimated_row_count": 5000000,
  "avg_row_size_bytes": 2048
}
```

**How to Collect:**
```bash
# From Ab Initio metadata repository
# Parse .mp files or query metadata database
python parse_graph_metadata.py --graph customer_daily_agg.mp > graph_meta.json

# From job configuration
cat job_config.yaml | yq eval '.graph_metadata' - > graph_meta.json
```

**Storage:** S3 (metadata repository)

**Frequency:** On graph changes

### 1.6 Data Quality Metrics

**What to Collect:**
```json
{
  "source_table": "staging.customer_transactions",
  "timestamp": "2025-11-29T02:00:00Z",
  "row_count": 5000000,
  "duplicate_count": 125000,
  "duplicate_rate": 0.025,
  "null_rates": {
    "customer_id": 0.001,
    "transaction_date": 0.0,
    "amount": 0.005
  },
  "outliers": {
    "amount_outliers": 150,
    "date_outliers": 25
  },
  "completeness": 0.98,
  "accuracy": 0.95
}
```

**How to Collect:**
```sql
-- From Teradata/source database
SELECT
  COUNT(*) as total_rows,
  COUNT(*) - COUNT(DISTINCT txn_id) as duplicate_count,
  SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) as null_customers
FROM staging.customer_transactions
WHERE txn_date = CURRENT_DATE - 1;
```

```bash
# Store results
python collect_data_quality.py \
  --table staging.customer_transactions \
  --output dq_metrics.json
```

**Storage:** DynamoDB (time-series)

**Frequency:** Before each job execution

---

## 2. Collection Architecture

### 2.1 Automated Collection Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                  Metadata Collection Pipeline               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │ Scheduled│          │Real-time │          │Event-    │
  │ (Cron)   │          │(Stream)  │          │Driven    │
  └──────────┘          └──────────┘          └──────────┘
        │                     │                     │
        ▼                     ▼                     ▼
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │Cluster   │          │CloudWatch│          │Kubernetes│
  │State     │          │Logs      │          │Events    │
  │(5 min)   │          │(Stream)  │          │(Webhook) │
  └──────────┘          └──────────┘          └──────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                      ┌─────────────┐
                      │  Lambda     │
                      │  Processor  │
                      └─────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │DynamoDB  │          │   S3     │          │ RDS      │
  │(Hot data)│          │(Archive) │          │(Analytics│
  └──────────┘          └──────────┘          └──────────┘
```

### 2.2 Collection Scripts

**Scheduled Collection (Every 5 minutes)**:
```bash
#!/bin/bash
# /opt/metadata-collector/collect_cluster_state.sh

python3 /opt/metadata-collector/SPDEMO_collect_metadata.py \
  --cluster bi-abi-apps-prod \
  --region us-east-1 \
  --output /tmp/cluster_state_$(date +%Y%m%d_%H%M%S).json

# Upload to S3
aws s3 cp /tmp/cluster_state_*.json \
  s3://abinitio-metadata/cluster-state/$(date +%Y/%m/%d)/ \
  --storage-class STANDARD_IA
```

**Event-Driven Collection (Job completion)**:
```python
# Lambda function triggered by CloudWatch Events
def lambda_handler(event, context):
    job_name = event['detail']['jobName']
    status = event['detail']['status']

    # Collect job execution data
    execution_data = collect_job_execution(job_name)

    # Store in DynamoDB
    dynamodb.put_item(
        TableName='job-executions',
        Item=execution_data
    )

    # If failed, collect detailed error info
    if status == 'FAILED':
        error_details = collect_error_details(job_name)
        store_error_details(error_details)
```

### 2.3 Cron Schedule

```crontab
# Cluster state - every 5 minutes
*/5 * * * * /opt/metadata-collector/collect_cluster_state.sh

# Storage config - daily at 1 AM
0 1 * * * /opt/metadata-collector/collect_storage_config.sh

# IAM config - daily at 2 AM
0 2 * * * /opt/metadata-collector/collect_iam_config.sh

# Data quality - before each job (via job dependency)
# Handled by job orchestrator
```

---

## 3. Storage Architecture

### 3.1 Storage Options by Data Type

| Data Type | Primary Storage | Archive | Query Interface |
|-----------|----------------|---------|-----------------|
| **Job Execution History** | DynamoDB (90d) | S3 (2y) | Athena |
| **Cluster State** | DynamoDB (7d) | S3 (1y) | Athena |
| **Storage Config** | S3 | S3 Glacier (5y) | S3 Select |
| **IAM Config** | DynamoDB + S3 | S3 (5y) | Athena |
| **Graph Metadata** | S3 | - | S3 Select |
| **Data Quality** | DynamoDB (30d) | S3 (1y) | Athena |

### 3.2 DynamoDB Schema

**Table: job-executions**
```
Partition Key: job_name (String)
Sort Key: execution_timestamp (Number - Unix timestamp)

Attributes:
- job_id (String)
- status (String) - GSI
- duration_minutes (Number)
- peak_memory_gb (Number)
- storage_used_gb (Number)
- failure_reason (String)
- input_row_count (Number)
- ttl (Number) - Auto-delete after 90 days

GSI: status-timestamp-index
  Partition Key: status
  Sort Key: execution_timestamp
```

**Table: cluster-state**
```
Partition Key: cluster_name (String)
Sort Key: timestamp (Number)

Attributes:
- available_cpu (Number)
- available_memory_gi (Number)
- node_count (Number)
- pending_pods (Number)
- ttl (Number) - Auto-delete after 7 days
```

### 3.3 S3 Bucket Structure

```
s3://abinitio-metadata/
├── job-executions/
│   ├── 2025/
│   │   ├── 11/
│   │   │   ├── 29/
│   │   │   │   ├── job-001.json
│   │   │   │   ├── job-002.json
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── cluster-state/
│   ├── 2025/
│   │   ├── 11/
│   │   │   └── 29/
│   │   │       ├── state_20251129_100000.json
│   │   │       ├── state_20251129_100500.json
│   │   │       └── ...
│   │   └── ...
│   └── ...
├── storage-config/
│   ├── efs/
│   │   └── current.json
│   └── s3/
│       └── current.json
├── iam-config/
│   ├── roles/
│   │   └── eks-abinitio-batch-role.json
│   └── policies/
│       └── S3Access.json
└── graph-metadata/
    ├── customer_daily_agg.json
    ├── sales_analytics.json
    └── ...
```

### 3.4 S3 Lifecycle Policies

```json
{
  "Rules": [
    {
      "Id": "ArchiveOldExecutions",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "job-executions/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 730
      }
    },
    {
      "Id": "DeleteOldClusterState",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "cluster-state/"
      },
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

---

## 4. Data Quality & Validation

### 4.1 Validation Rules

```python
def validate_job_execution_data(data):
    """Validate collected job execution data"""

    required_fields = [
        'job_name', 'execution_date', 'status',
        'duration_minutes', 'resources_used'
    ]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Validate status
    valid_statuses = ['SUCCESS', 'FAILED', 'RUNNING']
    if data['status'] not in valid_statuses:
        raise ValueError(f"Invalid status: {data['status']}")

    # Validate resource usage
    if data['resources_used']['peak_memory_gb'] < 0:
        raise ValueError("Invalid memory usage")

    # Validate timestamps
    exec_date = datetime.fromisoformat(data['execution_date'])
    if exec_date > datetime.utcnow():
        raise ValueError("Execution date in future")

    return True
```

### 4.2 Data Completeness Monitoring

```sql
-- Athena query to check data completeness
SELECT
  DATE_TRUNC('day', from_iso8601_timestamp(execution_date)) as day,
  COUNT(*) as total_executions,
  COUNT(CASE WHEN resources_used.peak_memory_gb IS NULL THEN 1 END) as missing_memory,
  COUNT(CASE WHEN resources_used.peak_memory_gb IS NULL THEN 1 END) * 100.0 / COUNT(*) as pct_missing
FROM job_executions
WHERE execution_date >= CURRENT_DATE - INTERVAL '30' DAY
GROUP BY 1
HAVING pct_missing > 5  -- Alert if > 5% missing
ORDER BY 1 DESC;
```

---

## 5. Security & Compliance

### 5.1 Data Encryption

- **At Rest**: All S3 buckets with SSE-KMS
- **In Transit**: TLS 1.2+ for all API calls
- **DynamoDB**: Encryption enabled with AWS-managed keys

### 5.2 Access Control

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowMetadataCollectorWrite",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MetadataCollectorRole"
      },
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::abinitio-metadata/*"
    },
    {
      "Sid": "AllowAIPredictorRead",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/AIPredictorRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::abinitio-metadata",
        "arn:aws:s3:::abinitio-metadata/*"
      ]
    }
  ]
}
```

### 5.3 Data Retention & GDPR Compliance

- **PII Removal**: Sanitize user information before storage
- **Right to Deletion**: Lambda function to delete specific job data
- **Data Minimization**: Only collect necessary fields
- **Audit Logging**: CloudTrail for all S3/DynamoDB access

---

## 6. Cost Optimization

### 6.1 Estimated Costs (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| **DynamoDB** | 1M writes/day, 100GB storage | $150 |
| **S3** | 500GB Standard, 2TB Glacier | $30 |
| **Athena** | 1TB scanned/month | $5 |
| **Lambda** | 1M invocations/month | $0.20 |
| **CloudWatch Logs** | 100GB ingestion | $50 |
| **Total** | | **~$235/month** |

### 6.2 Cost Reduction Tips

1. **Use DynamoDB on-demand** for variable workloads
2. **Enable S3 Intelligent-Tiering** for automatic archival
3. **Partition S3 data** by date for efficient Athena queries
4. **Set DynamoDB TTL** to auto-delete old data
5. **Use CloudWatch Logs insights** instead of exporting all logs

---

## 7. Monitoring & Alerts

### 7.1 Collection Health Metrics

```yaml
# CloudWatch Alarms
- AlarmName: MetadataCollectionFailures
  MetricName: CollectionErrors
  Threshold: 5
  EvaluationPeriods: 2
  ComparisonOperator: GreaterThanThreshold

- AlarmName: DataCompletenessLow
  MetricName: DataCompleteness
  Threshold: 95
  ComparisonOperator: LessThanThreshold

- AlarmName: StorageCostHigh
  MetricName: EstimatedCharges
  Threshold: 300
  ComparisonOperator: GreaterThanThreshold
```

### 7.2 Data Quality Dashboard

Track:
- Collection success rate
- Data completeness percentage
- Storage growth rate
- Query performance (Athena)
- Cost trends

---

## Summary Checklist

- [ ] Collect job execution history (success/failure, resources)
- [ ] Collect EKS cluster state every 5 minutes
- [ ] Collect storage configuration (EFS, S3) daily
- [ ] Collect IAM/IRSA configuration daily
- [ ] Collect graph metadata on changes
- [ ] Collect data quality metrics before each job
- [ ] Store hot data in DynamoDB (7-90 days TTL)
- [ ] Archive to S3 with lifecycle policies
- [ ] Enable encryption (SSE-KMS) on all storage
- [ ] Set up CloudWatch alarms for collection health
- [ ] Monitor costs and optimize storage tiers
- [ ] Validate data quality and completeness
- [ ] Implement access controls (IAM policies)
- [ ] Schedule automated collection (cron/Lambda)
- [ ] Test disaster recovery procedures

---

**Next Steps**: See `SPDEMO_STORAGE_ARCHITECTURE.md` for detailed cloud storage design.
