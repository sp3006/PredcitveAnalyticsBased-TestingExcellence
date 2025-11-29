# AI-Powered EKS Job Failure Predictor - MVP Demo

## 🎯 Overview

This MVP demonstrates an AI-powered system that predicts failures for Ab Initio jobs running on AWS EKS **before execution**. It uses **Anthropic's Claude API** for intelligent analysis and predictions.

### Key Features

✅ **Real-time AI Predictions** - Uses Claude 3.5 Sonnet for accurate failure prediction
✅ **Interactive Demo** - Easy-to-use CLI interface
✅ **Historical Analysis** - Learns from past job executions
✅ **Multi-dimensional Predictions** - Covers pod scheduling, storage mounts, memory, IAM, data quality
✅ **Actionable Recommendations** - Provides specific fixes for each issue
✅ **Effort Estimation** - Automatically categorizes fix complexity

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+**
2. **Anthropic API Key** - Get from https://console.anthropic.com/
3. **AWS CLI** (optional, for real data collection)
4. **kubectl** (optional, for real data collection)

### Installation

```bash
# 1. Install dependencies
pip install anthropic boto3 pyyaml

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY='your-api-key-here'

# 3. Run the demo
python SPDEMO_demo.py
```

### First Run

```bash
$ python SPDEMO_demo.py

╔═══════════════════════════════════════════════════════════╗
║   AI-Powered EKS Job Failure Predictor - Demo            ║
║   Using Anthropic Claude API                             ║
╚═══════════════════════════════════════════════════════════╝

This demo predicts failures for Ab Initio jobs running in EKS
with AWS services (EFS, S3, IAM/IRSA)

✓ Loaded demo data successfully
  - 8 historical executions
  - 3 job configurations

=== AI-Powered EKS Job Failure Predictor ===

Available Jobs:
  1. customer_daily_aggregation
     Daily customer transaction aggregation
     Schedule: 0 2 * * *

  2. sales_analytics_daily
     Daily sales analytics and reporting
     Schedule: 0 4 * * *

  3. inventory_snapshot
     Hourly inventory snapshot
     Schedule: 0 * * * *

  4. Analyze Historical Failures
  5. Exit

Select option:
```

---

## 📊 Demo Data Included

The demo includes realistic sample data:

### 1. **Historical Job Executions** (`SPDEMO_historical_job_data.json`)

- **8 job executions** (4 successes, 4 failures)
- Failure types:
  - OOMKilled (memory exceeded)
  - EFS mount timeout
  - Pod scheduling failure (insufficient CPU)
  - S3 Access Denied (IAM permissions)
- Resource usage metrics
- EKS pod information
- Timing data

### 2. **Sample Job Configurations** (`SPDEMO_sample_job_configs.json`)

- **3 Ab Initio jobs** with complete configurations:
  - Graph metadata (components, sorts, joins, aggregations)
  - Source data configuration (Teradata, duplicates, staging)
  - Kubernetes specifications (resources, nodeSelector, tolerations)
  - Storage configuration (EFS)
  - IAM/IRSA requirements

### 3. **EKS Cluster Configuration** (from `config/eks_cluster_config.yaml`)

- Node groups and capacity
- Available CPU/memory resources
- CSI drivers installed
- Resource quotas

---

## 🤖 How It Works

### AI Prediction Flow

```
User selects job
      ↓
Load job config + historical data
      ↓
Send to Claude API for analysis
      ↓
Claude analyzes:
  - Pod scheduling feasibility
  - EFS mount success probability
  - Memory OOMKill risk
  - IAM permission gaps
  - Data quality issues
      ↓
Return predictions with:
  - Probability (0-100%)
  - Severity (LOW/MEDIUM/HIGH/CRITICAL)
  - Root causes
  - Recommendations
  - Effort estimation
```

### Claude API Configuration

The demo uses **Claude 3.5 Sonnet** (`claude-3-5-sonnet-20241022`) with:
- **Model**: Anthropic's latest Sonnet model for accuracy
- **Temperature**: 0.3 (lower for consistent predictions)
- **Max Tokens**: 4096
- **Purpose**: Structured JSON output for predictions

### Example Prediction

```json
{
  "predictions": {
    "pod_scheduling": {
      "probability": 65,
      "severity": "MEDIUM",
      "root_cause": "Requested 8 CPU cores but only 5 available",
      "recommendations": [
        "Scale up EKS node group",
        "Reduce parallelism from 4 to 2"
      ]
    },
    "memory_oomkill": {
      "probability": 85,
      "severity": "HIGH",
      "root_cause": "Historical peak memory (16.2GB) exceeds limit (16GB)",
      "recommendations": [
        "Increase memory limit to 20Gi",
        "Enable external sort to reduce memory footprint"
      ]
    }
  },
  "overall_assessment": {
    "should_execute": false,
    "overall_severity": "HIGH",
    "overall_probability": 72,
    "recommendation": "Address high-severity issues before execution"
  },
  "estimated_effort": {
    "category": "MEDIUM",
    "story_points": 3,
    "estimated_hours": "4-8"
  }
}
```

---

## 📁 Demo Files

| File | Purpose | Size |
|------|---------|------|
| `SPDEMO_demo.py` | Interactive demo tool | Main application |
| `SPDEMO_historical_job_data.json` | Sample historical executions | 8 jobs with metrics |
| `SPDEMO_sample_job_configs.json` | Sample job configurations | 3 complete configs |
| `SPDEMO_collect_metadata.py` | Real data collection script | For production use |
| `SPDEMO_README.md` | This file | Documentation |
| `SPDEMO_METADATA_GUIDE.md` | Metadata collection guide | Best practices |
| `SPDEMO_STORAGE_ARCHITECTURE.md` | Cloud storage guide | AWS/cloud design |

---

## 💻 Usage Examples

### Example 1: Predict for a Job

```bash
$ python SPDEMO_demo.py

Select option: 1

Analyzing: customer_daily_aggregation
🤖 Analyzing with Claude AI...

=== Prediction Results for customer_daily_aggregation ===

✓ Overall Decision: SAFE TO EXECUTE
Severity: LOW
Recommendation: Safe to execute with standard monitoring

Detailed Analysis:

Pod Scheduling
  Probability: 15%
  Severity: LOW
  Cause: Sufficient cluster resources available
  Recommendations:
    • Monitor cluster capacity during peak hours

EFS Mount
  Probability: 10%
  Severity: LOW
  Cause: EFS configuration appears correct
  Recommendations:
    • Security group allows NFS port 2049

Memory OOMKill
  Probability: 25%
  Severity: LOW
  Cause: Historical peak (13.2GB) within limits (16GB)
  Recommendations:
    • Current memory limits are adequate
    • Monitor for data volume spikes

IAM Permissions
  Probability: 5%
  Severity: LOW
  Cause: ServiceAccount properly configured with IRSA
  Recommendations:
    • IAM role has required S3 and EFS permissions

Data Quality
  Probability: 20%
  Severity: LOW
  Cause: Historical duplicate rate of 6%
  Recommendations:
    • Add DEDUP component for data cleanliness

Effort Estimation:
  Category: SIMPLE
  Story Points: 1
  Estimated Hours: 1-2

Save predictions to file? (y/n):
```

### Example 2: Analyze Historical Failures

```bash
Select option: 4

=== Historical Failure Analysis ===

Found 4 failures. Analyzing patterns...
🤖 Analyzing with Claude AI...

Based on the historical failures, I've identified these patterns:

**Common Failure Patterns:**

1. **Resource-Related Failures (50%)**
   - OOMKilled: Memory limits too low for data volume spikes
   - Pod Pending: Insufficient CPU during high parallelism jobs

2. **Infrastructure Failures (25%)**
   - EFS Mount Timeout: Security group misconfiguration
   - Likely cause: NFS port 2049 not open from all nodes

3. **Permission Failures (25%)**
   - S3 Access Denied: IAM role missing s3:GetObject permission
   - IRSA not properly configured for service account

**Root Cause Categories:**

1. **Inadequate Resource Limits**: Jobs failing when data volume exceeds normal
2. **Network/Security Configuration**: Storage mount failures
3. **IAM/IRSA Misconfiguration**: Permission issues

**Preventive Measures:**

1. **Immediate (High Priority):**
   - Fix EFS security group rules (add port 2049 from node SG)
   - Add missing S3 permissions to IAM role
   - Increase memory limits by 30% buffer

2. **Short-term:**
   - Implement pre-execution resource validation
   - Add horizontal pod autoscaling
   - Enable external sort for memory-intensive jobs

3. **Long-term:**
   - Predictive scaling based on data volume
   - Automated IRSA validation in CI/CD
   - Resource quota management

**Priority Recommendations:**

1. **Fix security group** for EFS (CRITICAL)
2. **Update IAM policies** for S3 access (CRITICAL)
3. **Increase memory limits** to 20Gi for customer_daily_aggregation (HIGH)
4. **Implement CPU quota** management (MEDIUM)
```

---

## 🔧 Customization

### Use Your Own Data

Replace the sample data with your real data:

```bash
# 1. Collect metadata from your EKS cluster
python SPDEMO_collect_metadata.py \
  --cluster bi-abi-apps-prod \
  --region us-east-1 \
  --output my_cluster_data.json

# 2. Update SPDEMO_demo.py to load your data
# Edit line 67-75 to point to your files
```

### Adjust Prediction Sensitivity

In `SPDEMO_demo.py`, modify the Claude API parameters:

```python
# For more conservative predictions (higher sensitivity)
temperature=0.1  # Default: 0.3

# For more detailed analysis
max_tokens=8192  # Default: 4096
```

### Add Custom Failure Types

Extend the prompt in `predict_with_claude()` method to include additional failure scenarios:

```python
prompt = f"""
...existing prompt...

Additional analysis required:
6. **Network Policy** - Will network policies block required traffic?
7. **ConfigMap/Secret** - Are all configurations available?
"""
```

---

## 📈 Model Selection

### Why Claude 3.5 Sonnet?

| Model | Predictability | Speed | Cost | Best For |
|-------|---------------|-------|------|----------|
| **Claude 3.5 Sonnet** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $$ | **Production predictions** |
| Claude 3 Opus | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | $$$ | Complex analysis |
| Claude 3 Haiku | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ | Quick checks |

**Recommendation**: Use **Claude 3.5 Sonnet** for best balance of accuracy, speed, and cost.

### Alternative Models

The demo can be adapted for other AI models:

**OpenAI GPT-4**:
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[{"role": "user", "content": prompt}]
)
```

**AWS Bedrock (Claude)**:
```python
import boto3
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": prompt}]
    })
)
```

---

## 🎓 Learning Outcomes

This demo demonstrates:

1. **AI for DevOps** - Using LLMs for infrastructure predictions
2. **Shift-Left Testing** - Catching issues before execution
3. **EKS Best Practices** - Resource management, IRSA, storage
4. **Prompt Engineering** - Structured prompts for consistent outputs
5. **Interactive CLI** - User-friendly Python applications

---

## 🐛 Troubleshooting

### Error: "ANTHROPIC_API_KEY not set"

**Solution**:
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

### Error: "Module 'anthropic' not found"

**Solution**:
```bash
pip install anthropic
```

### Error: "File not found: SPDEMO_historical_job_data.json"

**Solution**: Ensure you're running from the project root directory:
```bash
cd /path/to/eks-abinitio-app
python SPDEMO_demo.py
```

### Claude API Rate Limits

If you hit rate limits:
- **Free tier**: 5 requests/minute
- **Paid tier**: 50+ requests/minute
- **Solution**: Add delays between predictions or upgrade plan

---

## 💰 Cost Estimation

### Claude API Pricing (as of 2025)

| Model | Input | Output | Est. Cost/Prediction |
|-------|-------|--------|---------------------|
| Claude 3.5 Sonnet | $3/MTok | $15/MTok | ~$0.05 - $0.10 |
| Claude 3 Opus | $15/MTok | $75/MTok | ~$0.25 - $0.50 |
| Claude 3 Haiku | $0.25/MTok | $1.25/MTok | ~$0.005 - $0.01 |

**For 100 predictions/day**:
- Claude 3.5 Sonnet: ~$5-10/day = **$150-300/month**
- Claude 3 Haiku: ~$0.50-1/day = **$15-30/month**

**ROI**: Preventing a single production failure saves **$5,000-50,000** >> Monthly API cost

---

## 🔜 Next Steps

### For Production Use

1. **Collect Real Data**:
   ```bash
   python SPDEMO_collect_metadata.py --cluster your-cluster
   ```

2. **Set Up Automated Collection**:
   - Run metadata collection daily via cron
   - Store in S3/DynamoDB for historical analysis

3. **Integrate with CI/CD**:
   - Add prediction step before deployment
   - Block deployments on CRITICAL severity

4. **Add JIRA Integration**:
   - Auto-create tickets for predicted failures
   - Use existing `jira_integration.py` module

5. **Train Custom Models** (Advanced):
   - Use historical data to train specialized models
   - Fine-tune Claude or train XGBoost for specific failure types

### Extend the Demo

- Add web UI (Flask/FastAPI)
- Real-time monitoring dashboard
- Slack/Teams notifications
- Multi-cluster support
- Cost optimization predictions

---

## 📞 Support

- **Documentation**: See other `SPDEMO_*.md` files
- **Issues**: Check `EKS_TESTING_EXCELLENCE_GUIDE.md` for troubleshooting
- **API Docs**: https://docs.anthropic.com/claude/reference

---

## 📝 License

This demo is provided as-is for educational and evaluation purposes.

---

**Demo Version**: 1.0.0
**Last Updated**: November 29, 2025
**Powered by**: Anthropic Claude 3.5 Sonnet
