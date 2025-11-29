# Cloud Storage Architecture for AI Metadata

## Executive Summary

This document outlines the cloud storage architecture for collecting, storing, and analyzing metadata for AI-powered job failure predictions.

**Key Design Principles:**
- ✅ Cost-effective tiered storage
- ✅ High availability and durability
- ✅ Fast query performance
- ✅ Compliance and security
- ✅ Scalability for growth

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Data Collection Layer                      │
└─────────────────────────────────────────────────────────────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ EKS     │    │ AWS     │    │ Cloud   │    │ App     │
    │ Cluster │    │ Services│    │ Watch   │    │ Logs    │
    └─────────┘    └─────────┘    └─────────┘    └─────────┘
          │              │              │              │
          └──────────────┼──────────────┼──────────────┘
                         ▼              ▼
                  ┌─────────────────────────┐
                  │   Lambda Processors     │
                  │  - Validation           │
                  │  - Transformation       │
                  │  - Enrichment           │
                  └─────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│  DynamoDB     │    │   S3 Buckets   │    │   Athena     │
│  (Hot Data)   │    │   (Archive)    │    │   (Query)    │
│               │    │                │    │              │
│ - Jobs: 90d   │    │ - Jobs: 2y     │    │ - Analytics  │
│ - Cluster: 7d │    │ - Config: 5y   │    │ - ML Training│
│ - Metrics: 30d│    │ - Logs: 1y     │    │ - Reporting  │
└───────────────┘    └────────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                  ┌─────────────────────────┐
                  │  AI Prediction Engine   │
                  │  - Claude API           │
                  │  - XGBoost Models       │
                  │  - Feature Engineering  │
                  └─────────────────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │   Visualization Layer   │
                  │  - Grafana Dashboards   │
                  │  - JIRA Integration     │
                  │  - Slack Notifications  │
                  └─────────────────────────┘
```

---

## 2. Storage Layers

### 2.1 Hot Data Layer (DynamoDB)

**Purpose**: Fast access to recent data for real-time predictions

**Tables:**

#### Table 1: job-executions
```hcl
table_name = "abinitio-job-executions"
billing_mode = "PAY_PER_REQUEST"  # Auto-scales

partition_key = {
  name = "job_name"
  type = "S"  # String
}

sort_key = {
  name = "execution_timestamp"
  type = "N"  # Number (Unix timestamp)
}

attributes = {
  job_id              = "S"
  status              = "S"
  duration_minutes    = "N"
  peak_memory_gb      = "N"
  peak_cpu_cores      = "N"
  storage_used_gb     = "N"
  failure_reason      = "S"
  input_row_count     = "N"
  duplicate_rate      = "N"
  ttl                 = "N"  # Auto-delete after 90 days
}

global_secondary_indexes = [
  {
    name            = "status-timestamp-index"
    partition_key   = "status"
    sort_key        = "execution_timestamp"
    projection_type = "ALL"
  }
]

ttl = {
  enabled        = true
  attribute_name = "ttl"
}

point_in_time_recovery = {
  enabled = true
}

server_side_encryption = {
  enabled     = true
  kms_key_arn = "arn:aws:kms:us-east-1:123456789012:key/abc-123"
}
```

**Capacity Planning:**
- **Writes**: 100/second (peak)
- **Reads**: 500/second (peak)
- **Storage**: ~100GB (90 days retention)
- **Cost**: ~$150/month

#### Table 2: cluster-state
```hcl
table_name = "abinitio-cluster-state"

partition_key = {
  name = "cluster_name"
  type = "S"
}

sort_key = {
  name = "timestamp"
  type = "N"
}

attributes = {
  available_cpu       = "N"
  available_memory_gi = "N"
  node_count          = "N"
  pending_pods        = "N"
  pending_pvcs        = "LIST"  # List of pending PVC names
  ttl                 = "N"     # Auto-delete after 7 days
}

ttl = {
  enabled        = true
  attribute_name = "ttl"
}
```

**Capacity Planning:**
- **Writes**: 1/5 seconds = 12/minute
- **Storage**: ~5GB (7 days retention)
- **Cost**: ~$20/month

#### Table 3: data-quality-metrics
```hcl
table_name = "abinitio-data-quality"

partition_key = {
  name = "source_table"
  type = "S"
}

sort_key = {
  name = "check_timestamp"
  type = "N"
}

attributes = {
  row_count       = "N"
  duplicate_count = "N"
  duplicate_rate  = "N"
  null_rates      = "M"  # Map
  completeness    = "N"
  accuracy        = "N"
  ttl             = "N"  # 30 days
}
```

**Total DynamoDB Cost**: ~$200/month (on-demand)

---

### 2.2 Warm Data Layer (S3 Standard/Standard-IA)

**Purpose**: Medium-term storage with lifecycle transitions

**Bucket Structure:**

```
s3://abinitio-ai-metadata/
├── job-executions/
│   ├── year=2025/
│   │   └── month=11/
│   │       └── day=29/
│   │           ├── hour=00/
│   │           │   ├── job-001.parquet
│   │           │   └── job-002.parquet
│   │           └── hour=01/
│   │               └── ...
│   └── ...
├── cluster-state/
│   ├── year=2025/
│   │   └── month=11/
│   │       └── day=29/
│   │           ├── state_100000.json
│   │           ├── state_100500.json
│   │           └── ...
│   └── ...
├── storage-config/
│   ├── efs/
│   │   ├── snapshots/
│   │   │   └── 2025-11-29.json
│   │   └── current.json
│   └── s3/
│       └── buckets/
│           └── abinitio-source-data.json
├── iam-config/
│   ├── roles/
│   │   ├── eks-abinitio-batch-role/
│   │   │   ├── role.json
│   │   │   ├── trust-policy.json
│   │   │   └── policies/
│   │   │       ├── S3Access.json
│   │   │       └── EFSAccess.json
│   │   └── ...
│   └── access-denied-events/
│       └── year=2025/
│           └── month=11/
│               └── events.jsonl
└── graph-metadata/
    ├── customer_daily_agg/
    │   ├── graph.json
    │   ├── components.json
    │   └── versions/
    │       └── v1.2.3.json
    └── ...
```

**Lifecycle Policies:**

```json
{
  "Rules": [
    {
      "Id": "JobExecutionsLifecycle",
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
          "Days": 180,
          "StorageClass": "GLACIER_INSTANT_RETRIEVAL"
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER_FLEXIBLE_RETRIEVAL"
        }
      ],
      "Expiration": {
        "Days": 730
      }
    },
    {
      "Id": "ClusterStateLifecycle",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "cluster-state/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 180,
          "StorageClass": "GLACIER_FLEXIBLE_RETRIEVAL"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    },
    {
      "Id": "ConfigSnapshotsLifecycle",
      "Status": "Enabled",
      "Filter": {
        "And": {
          "Prefix": "storage-config/",
          "Tags": [
            {
              "Key": "Type",
              "Value": "Snapshot"
            }
          ]
        }
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER_FLEXIBLE_RETRIEVAL"
        }
      ],
      "Expiration": {
        "Days": 1825
      }
    }
  ]
}
```

**Bucket Configuration:**

```hcl
bucket = "abinitio-ai-metadata"

versioning = {
  enabled = true
}

server_side_encryption_configuration = {
  rule = {
    apply_server_side_encryption_by_default = {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = "arn:aws:kms:us-east-1:123456789012:key/abc-123"
    }
  }
}

logging = {
  target_bucket = "abinitio-logs"
  target_prefix = "s3-access-logs/"
}

object_lock_configuration = {
  object_lock_enabled = "Enabled"
  rule = {
    default_retention = {
      mode = "GOVERNANCE"
      days = 90
    }
  }
}

intelligent_tiering_configuration = [
  {
    name   = "EntireS3Bucket"
    status = "Enabled"
    tiering = {
      archive_access_tier = {
        days = 90
      }
      deep_archive_access_tier = {
        days = 180
      }
    }
  }
]
```

**Storage Estimates:**

| Data Type | Size/Day | 90 Days | 1 Year | Storage Class |
|-----------|----------|---------|--------|---------------|
| Job Executions | 500MB | 45GB | 180GB | Standard → IA |
| Cluster State | 50MB | 4.5GB | 18GB | Standard → IA |
| Storage Config | 10MB | 900MB | 3.6GB | Standard |
| IAM Config | 5MB | 450MB | 1.8GB | Standard |
| Graph Metadata | 100MB | - | 100MB | Standard |
| **Total** | **665MB** | **~50GB** | **~300GB** | Mixed |

**S3 Cost (Monthly):**
- Standard: 50GB × $0.023/GB = $1.15
- Standard-IA: 150GB × $0.0125/GB = $1.88
- Glacier: 100GB × $0.004/GB = $0.40
- **Total**: ~$3.50/month

---

### 2.3 Cold Data Layer (S3 Glacier)

**Purpose**: Long-term archival for compliance

**Data Types:**
- Historical job executions (>1 year)
- Old cluster configurations
- Compliance audit logs

**Retrieval Options:**

| Tier | Retrieval Time | Cost/GB |
|------|---------------|---------|
| Expedited | 1-5 minutes | $0.03 |
| Standard | 3-5 hours | $0.01 |
| Bulk | 5-12 hours | $0.0025 |

**Configuration:**

```hcl
glacier_ir = {
  storage_class = "GLACIER_IR"
  retrieval_tier = "Standard"
}

glacier_flexible = {
  storage_class = "GLACIER"
  retrieval_tier = "Bulk"
}
```

**Cost**: ~$0.50/month (archival storage)

---

## 3. Query & Analytics Layer

### 3.1 AWS Athena

**Purpose**: SQL queries on S3 data without servers

**Table Definitions:**

```sql
-- Job Executions Table
CREATE EXTERNAL TABLE IF NOT EXISTS job_executions (
  job_id STRING,
  job_name STRING,
  execution_date TIMESTAMP,
  status STRING,
  duration_minutes DOUBLE,
  peak_memory_gb DOUBLE,
  avg_cpu_cores DOUBLE,
  peak_cpu_cores DOUBLE,
  storage_used_gb DOUBLE,
  failure_reason STRING,
  error_details STRUCT<
    type: STRING,
    message: STRING,
    exit_code: INT
  >,
  input_data STRUCT<
    row_count: BIGINT,
    size_gb: DOUBLE,
    duplicate_rate: DOUBLE
  >,
  resources_used STRUCT<
    peak_memory_gb: DOUBLE,
    avg_cpu_cores: DOUBLE
  >
)
PARTITIONED BY (
  year INT,
  month INT,
  day INT,
  hour INT
)
STORED AS PARQUET
LOCATION 's3://abinitio-ai-metadata/job-executions/'
TBLPROPERTIES (
  'parquet.compression'='SNAPPY',
  'projection.enabled'='true',
  'projection.year.type'='integer',
  'projection.year.range'='2024,2030',
  'projection.month.type'='integer',
  'projection.month.range'='1,12',
  'projection.day.type'='integer',
  'projection.day.range'='1,31',
  'projection.hour.type'='integer',
  'projection.hour.range'='0,23'
);
```

**Common Queries:**

```sql
-- 1. Failure rate by job
SELECT
  job_name,
  COUNT(*) as total_executions,
  SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failures,
  SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as failure_rate
FROM job_executions
WHERE year = 2025 AND month = 11
GROUP BY job_name
ORDER BY failure_rate DESC;

-- 2. Resource usage trends
SELECT
  DATE_TRUNC('day', execution_date) as day,
  job_name,
  AVG(resources_used.peak_memory_gb) as avg_memory,
  MAX(resources_used.peak_memory_gb) as max_memory,
  PERCENTILE_APPROX(resources_used.peak_memory_gb, 0.95) as p95_memory
FROM job_executions
WHERE year = 2025 AND month = 11
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- 3. Duplicate data correlation with failures
SELECT
  input_data.duplicate_rate,
  COUNT(*) as executions,
  SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failures
FROM job_executions
WHERE year = 2025 AND month = 11
  AND input_data.duplicate_rate > 0
GROUP BY 1
ORDER BY 1;
```

**Query Optimization:**
- Use partition pruning
- Compress data with Snappy
- Store in columnar format (Parquet)
- Use projection for partitions

**Athena Cost:**
- $5 per TB scanned
- Average query: 100GB scanned = $0.50
- Monthly (100 queries): ~$50

---

### 3.2 Amazon QuickSight (Optional)

**Purpose**: Business intelligence dashboards

**Dashboards:**
1. Job Execution Health
   - Success rate over time
   - Failure reasons breakdown
   - Average execution time trends

2. Resource Utilization
   - CPU/Memory usage patterns
   - Storage consumption
   - Cost allocation

3. Prediction Accuracy
   - AI prediction accuracy vs actual
   - False positive/negative rates
   - Model performance metrics

**Cost**: $18/month (author) + $0.30/session (reader)

---

## 4. Data Pipeline

### 4.1 Real-time Streaming (Kinesis)

**Purpose**: Real-time event ingestion from EKS

```
EKS Pods → CloudWatch Logs → Kinesis Data Stream → Lambda → DynamoDB/S3
```

**Configuration:**

```hcl
kinesis_data_stream = {
  name             = "abinitio-events"
  shard_count      = 2  # Auto-scales
  retention_period = 24  # hours

  encryption = {
    type        = "KMS"
    kms_key_arn = "arn:aws:kms:us-east-1:123456789012:key/abc-123"
  }
}

kinesis_firehose = {
  name        = "abinitio-events-to-s3"
  destination = "extended_s3"

  s3_configuration = {
    bucket_arn = "arn:aws:s3:::abinitio-ai-metadata"
    prefix     = "job-executions/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"

    compression_format = "PARQUET"
    buffering_size     = 128  # MB
    buffering_interval = 300  # seconds
  }

  data_format_conversion = {
    enabled = true
    schema_configuration = {
      database_name = "abinitio_metadata"
      table_name    = "job_executions"
      region        = "us-east-1"
    }
  }
}
```

**Cost**: ~$30/month (2 shards)

### 4.2 Batch Processing (Lambda)

**Lambda Functions:**

#### 1. Job Execution Processor
```python
# lambda_job_processor.py
import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """Process job execution events"""

    for record in event['Records']:
        # Parse CloudWatch log event
        log_data = json.loads(record['body'])

        # Extract job metadata
        job_data = {
            'job_name': log_data['job_name'],
            'execution_timestamp': int(datetime.utcnow().timestamp()),
            'status': log_data['status'],
            'duration_minutes': log_data.get('duration_minutes'),
            'peak_memory_gb': log_data.get('peak_memory_gb'),
            'ttl': int(datetime.utcnow().timestamp()) + (90 * 24 * 3600)
        }

        # Write to DynamoDB
        table = dynamodb.Table('abinitio-job-executions')
        table.put_item(Item=job_data)

        # Also write to S3 for long-term storage
        s3_key = (
            f"job-executions/year={datetime.now().year}/"
            f"month={datetime.now().month:02d}/"
            f"day={datetime.now().day:02d}/"
            f"{log_data['job_id']}.json"
        )

        s3.put_object(
            Bucket='abinitio-ai-metadata',
            Key=s3_key,
            Body=json.dumps(log_data),
            ContentType='application/json'
        )

    return {'statusCode': 200}
```

#### 2. Cluster State Collector
```python
# lambda_cluster_collector.py
import boto3
import subprocess
import json
from datetime import datetime

eks = boto3.client('eks')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Collect EKS cluster state"""

    cluster_name = 'bi-abi-apps-prod'

    # Get cluster info from EKS API
    cluster_info = eks.describe_cluster(name=cluster_name)

    # Get node metrics (assumes kubectl configured)
    # In Lambda, use Kubernetes API directly
    nodes_info = get_node_metrics()

    cluster_state = {
        'cluster_name': cluster_name,
        'timestamp': int(datetime.utcnow().timestamp()),
        'available_cpu': nodes_info['available_cpu'],
        'available_memory_gi': nodes_info['available_memory_gi'],
        'node_count': nodes_info['node_count'],
        'ttl': int(datetime.utcnow().timestamp()) + (7 * 24 * 3600)
    }

    # Write to DynamoDB
    table = dynamodb.Table('abinitio-cluster-state')
    table.put_item(Item=cluster_state)

    return {'statusCode': 200}

def get_node_metrics():
    # Implementation to get node metrics
    # Use Kubernetes Python client
    pass
```

**Lambda Configuration:**

```hcl
lambda_job_processor = {
  function_name = "abinitio-job-processor"
  runtime       = "python3.11"
  handler       = "lambda_job_processor.lambda_handler"
  timeout       = 60
  memory_size   = 256

  environment = {
    TABLE_NAME = "abinitio-job-executions"
    BUCKET_NAME = "abinitio-ai-metadata"
  }

  reserved_concurrent_executions = 10
}
```

**Cost**: ~$5/month (1M invocations)

---

## 5. Security & Compliance

### 5.1 Encryption

**At Rest:**
- DynamoDB: AWS-managed KMS keys
- S3: Customer-managed KMS keys
- EBS: Encrypted volumes

**In Transit:**
- TLS 1.2+ for all API calls
- VPC endpoints for S3/DynamoDB access

**Key Management:**

```hcl
kms_key = {
  description             = "Encryption key for Ab Initio AI metadata"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::123456789012:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use by Lambda and DynamoDB"
        Effect = "Allow"
        Principal = {
          Service = ["lambda.amazonaws.com", "dynamodb.amazonaws.com"]
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:CreateGrant"
        ]
        Resource = "*"
      }
    ]
  })
}
```

### 5.2 Access Control (IAM)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/abinitio-job-executions",
        "arn:aws:dynamodb:us-east-1:123456789012:table/abinitio-cluster-state"
      ]
    },
    {
      "Sid": "S3ReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::abinitio-ai-metadata",
        "arn:aws:s3:::abinitio-ai-metadata/*"
      ]
    },
    {
      "Sid": "AthenaQuery",
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5.3 Audit Logging

Enable CloudTrail for all S3/DynamoDB access:

```hcl
cloudtrail = {
  name           = "abinitio-metadata-audit"
  s3_bucket_name = "abinitio-cloudtrail-logs"

  event_selector = [
    {
      read_write_type           = "All"
      include_management_events = true

      data_resource = [
        {
          type   = "AWS::S3::Object"
          values = ["arn:aws:s3:::abinitio-ai-metadata/*"]
        },
        {
          type   = "AWS::DynamoDB::Table"
          values = [
            "arn:aws:dynamodb:us-east-1:123456789012:table/abinitio-job-executions",
            "arn:aws:dynamodb:us-east-1:123456789012:table/abinitio-cluster-state"
          ]
        }
      ]
    }
  ]
}
```

---

## 6. Disaster Recovery

### 6.1 Backup Strategy

**DynamoDB:**
- Point-in-time recovery enabled (35 days)
- Daily automated backups
- Cross-region replication (optional)

```hcl
backup_configuration = {
  backup_retention_period = 35

  automated_backup_schedule = {
    schedule_expression = "cron(0 2 * * ? *)"  # 2 AM daily
  }
}
```

**S3:**
- Versioning enabled
- Cross-region replication to us-west-2
- Object lock for compliance

```hcl
replication_configuration = {
  role = "arn:aws:iam::123456789012:role/S3ReplicationRole"

  rules = [
    {
      id     = "ReplicateToWest"
      status = "Enabled"

      destination = {
        bucket        = "arn:aws:s3:::abinitio-ai-metadata-dr"
        storage_class = "STANDARD_IA"
      }
    }
  ]
}
```

### 6.2 Recovery Procedures

**RTO/RPO Targets:**
- **RTO**: 4 hours
- **RPO**: 5 minutes (DynamoDB), 1 hour (S3)

**Recovery Steps:**
1. Restore DynamoDB from point-in-time recovery
2. Sync S3 from DR region
3. Recreate Lambda functions from code repository
4. Validate data integrity

---

## 7. Cost Summary

### 7.1 Monthly Costs (Production Scale)

| Service | Details | Monthly Cost |
|---------|---------|--------------|
| **DynamoDB** | 3 tables, 100GB, on-demand | $200 |
| **S3 Standard** | 50GB | $1.15 |
| **S3 Standard-IA** | 150GB | $1.88 |
| **S3 Glacier** | 100GB | $0.40 |
| **Athena** | 1TB scanned/month | $5 |
| **Kinesis** | 2 shards | $30 |
| **Lambda** | 1M invocations | $5 |
| **CloudWatch Logs** | 100GB ingestion | $50 |
| **Data Transfer** | 50GB out | $4.50 |
| **KMS** | 1 key, 10K requests | $1 |
| **CloudTrail** | 1 trail | $2 |
| **QuickSight** (Optional) | 1 author | $18 |
| **Backups** | DynamoDB + S3 | $20 |
| **Total** | | **~$340/month** |

### 7.2 Cost Optimization Tips

1. **Enable S3 Intelligent-Tiering** - Saves ~30%
2. **Use DynamoDB on-demand** - Only pay for what you use
3. **Partition Athena tables** - Reduce scan costs by 80%
4. **Compress CloudWatch Logs** - Save 50% on ingestion
5. **Set lifecycle policies** - Auto-transition to cheaper storage
6. **Use Reserved Capacity** (if usage predictable) - Save 50%
7. **Enable CloudWatch Logs Insights** - Avoid exporting all logs

**Potential Savings**: $100-150/month (30-40% reduction)

---

## 8. Monitoring & Alerts

### 8.1 Key Metrics

```yaml
CloudWatch_Metrics:
  - Name: DataCollectionSuccess
    Namespace: AbinitioAI
    Dimensions:
      - CollectorType
    Statistic: Sum
    Period: 300

  - Name: StorageCost
    Namespace: AWS/Billing
    Dimensions:
      - ServiceName: Amazon S3
    Statistic: Maximum
    Period: 86400

  - Name: DynamoDBThrottles
    Namespace: AWS/DynamoDB
    Dimensions:
      - TableName
    Statistic: Sum
    Period: 60
```

### 8.2 Alarms

```hcl
cloudwatch_alarms = [
  {
    alarm_name          = "DataCollectionFailures"
    comparison_operator = "GreaterThanThreshold"
    evaluation_periods  = 2
    metric_name         = "Errors"
    namespace           = "AWS/Lambda"
    period              = 300
    statistic           = "Sum"
    threshold           = 5
    alarm_actions       = [sns_topic_arn]
  },
  {
    alarm_name          = "S3StorageCostHigh"
    comparison_operator = "GreaterThanThreshold"
    evaluation_periods  = 1
    metric_name         = "EstimatedCharges"
    namespace           = "AWS/Billing"
    period              = 86400
    statistic           = "Maximum"
    threshold           = 50
    alarm_actions       = [sns_topic_arn]
  }
]
```

---

## 9. Implementation Checklist

- [ ] Create S3 bucket with lifecycle policies
- [ ] Create DynamoDB tables with TTL
- [ ] Set up KMS encryption keys
- [ ] Configure IAM roles and policies
- [ ] Deploy Lambda functions
- [ ] Create Kinesis streams (if real-time)
- [ ] Set up Athena tables and partitions
- [ ] Enable CloudTrail for audit logging
- [ ] Configure backup and replication
- [ ] Set up CloudWatch alarms
- [ ] Test disaster recovery procedures
- [ ] Document runbooks
- [ ] Train team on operations

---

## 10. Next Steps

1. **Deploy infrastructure** using Terraform/CloudFormation
2. **Test data collection** with sample jobs
3. **Validate query performance** with Athena
4. **Monitor costs** for first month
5. **Optimize based on usage patterns**
6. **Integrate with AI prediction engine**

---

**Architecture Version**: 1.0
**Last Updated**: November 29, 2025
**Owner**: Data Engineering Team
