#!/usr/bin/env python3
"""
Metadata Collection Script for EKS Job Predictions

This script collects metadata from:
- EKS cluster (kubectl)
- AWS services (boto3)
- Job execution logs
- Application metrics

Stores data in JSON format for AI model training.
"""

import json
import subprocess
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataCollector:
    """Collects metadata from EKS and AWS for job predictions"""

    def __init__(self, cluster_name: str, region: str = 'us-east-1'):
        self.cluster_name = cluster_name
        self.region = region

        # Initialize AWS clients
        self.eks_client = boto3.client('eks', region_name=region)
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.efs_client = boto3.client('efs', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)

    def collect_eks_cluster_state(self) -> Dict[str, Any]:
        """Collect current EKS cluster state"""
        logger.info("Collecting EKS cluster state...")

        cluster_state = {
            'cluster_name': self.cluster_name,
            'region': self.region,
            'timestamp': datetime.utcnow().isoformat(),
            'node_groups': [],
            'available_resources': {}
        }

        try:
            # Get cluster info
            cluster_info = self.eks_client.describe_cluster(name=self.cluster_name)
            cluster_state['cluster_version'] = cluster_info['cluster']['version']
            cluster_state['cluster_arn'] = cluster_info['cluster']['arn']

            # Get node groups
            node_groups = self.eks_client.list_nodegroups(clusterName=self.cluster_name)

            for ng_name in node_groups.get('nodegroups', []):
                ng_info = self.eks_client.describe_nodegroup(
                    clusterName=self.cluster_name,
                    nodegroupName=ng_name
                )

                ng_data = {
                    'name': ng_name,
                    'instance_types': ng_info['nodegroup']['instanceTypes'],
                    'desired_size': ng_info['nodegroup']['scalingConfig']['desiredSize'],
                    'min_size': ng_info['nodegroup']['scalingConfig']['minSize'],
                    'max_size': ng_info['nodegroup']['scalingConfig']['maxSize']
                }

                cluster_state['node_groups'].append(ng_data)

        except Exception as e:
            logger.error(f"Error collecting EKS state: {e}")

        # Get resource availability from kubectl
        try:
            result = subprocess.run(
                ['kubectl', 'top', 'nodes', '--no-headers'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                total_cpu = 0
                total_memory = 0

                for line in lines:
                    parts = line.split()
                    if len(parts) >= 3:
                        # Parse CPU (remove 'm' suffix)
                        cpu = parts[1].replace('m', '')
                        total_cpu += int(cpu) / 1000 if cpu.isdigit() else 0

                        # Parse memory (remove 'Mi' or 'Gi' suffix)
                        memory = parts[2]
                        if 'Gi' in memory:
                            total_memory += float(memory.replace('Gi', ''))
                        elif 'Mi' in memory:
                            total_memory += float(memory.replace('Mi', '')) / 1024

                cluster_state['available_resources'] = {
                    'total_cpu_cores': total_cpu,
                    'total_memory_gi': total_memory
                }

        except Exception as e:
            logger.error(f"Error getting kubectl metrics: {e}")

        return cluster_state

    def collect_storage_config(self) -> Dict[str, Any]:
        """Collect EFS and S3 configuration"""
        logger.info("Collecting storage configuration...")

        storage_config = {
            'efs_filesystems': [],
            's3_buckets': [],
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            # Get EFS filesystems
            efs_response = self.efs_client.describe_file_systems()

            for fs in efs_response.get('FileSystems', []):
                fs_data = {
                    'filesystem_id': fs['FileSystemId'],
                    'name': fs.get('Name', ''),
                    'size_gb': fs['SizeInBytes']['Value'] / (1024**3),
                    'performance_mode': fs['PerformanceMode'],
                    'throughput_mode': fs.get('ThroughputMode', 'bursting'),
                    'encrypted': fs['Encrypted']
                }

                # Get mount targets
                mt_response = self.efs_client.describe_mount_targets(
                    FileSystemId=fs['FileSystemId']
                )
                fs_data['mount_targets'] = len(mt_response.get('MountTargets', []))

                storage_config['efs_filesystems'].append(fs_data)

        except Exception as e:
            logger.error(f"Error collecting EFS config: {e}")

        try:
            # List S3 buckets (filter by prefix if needed)
            buckets = self.s3_client.list_buckets()

            for bucket in buckets.get('Buckets', []):
                bucket_name = bucket['Name']

                # Only include relevant buckets
                if 'abinitio' in bucket_name.lower():
                    try:
                        # Get bucket location
                        location = self.s3_client.get_bucket_location(Bucket=bucket_name)

                        # Get encryption
                        try:
                            encryption = self.s3_client.get_bucket_encryption(Bucket=bucket_name)
                            encrypted = True
                        except:
                            encrypted = False

                        bucket_data = {
                            'name': bucket_name,
                            'region': location.get('LocationConstraint', 'us-east-1'),
                            'encrypted': encrypted
                        }

                        storage_config['s3_buckets'].append(bucket_data)

                    except Exception as e:
                        logger.warning(f"Error getting details for bucket {bucket_name}: {e}")

        except Exception as e:
            logger.error(f"Error collecting S3 config: {e}")

        return storage_config

    def collect_iam_config(self, service_account_name: str, namespace: str = 'abinitio-prod') -> Dict[str, Any]:
        """Collect IAM/IRSA configuration"""
        logger.info(f"Collecting IAM config for {namespace}/{service_account_name}...")

        iam_config = {
            'service_account': service_account_name,
            'namespace': namespace,
            'iam_role_arn': None,
            'policies': [],
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            # Get ServiceAccount from kubectl
            result = subprocess.run(
                ['kubectl', 'get', 'serviceaccount', service_account_name,
                 '-n', namespace, '-o', 'json'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                sa_data = json.loads(result.stdout)
                annotations = sa_data.get('metadata', {}).get('annotations', {})
                iam_role_arn = annotations.get('eks.amazonaws.com/role-arn')

                if iam_role_arn:
                    iam_config['iam_role_arn'] = iam_role_arn

                    # Get IAM role details
                    role_name = iam_role_arn.split('/')[-1]

                    try:
                        # List attached policies
                        policies_response = self.iam_client.list_attached_role_policies(
                            RoleName=role_name
                        )

                        for policy in policies_response.get('AttachedPolicies', []):
                            iam_config['policies'].append({
                                'name': policy['PolicyName'],
                                'arn': policy['PolicyArn']
                            })

                    except Exception as e:
                        logger.error(f"Error getting IAM policies: {e}")

        except Exception as e:
            logger.error(f"Error collecting IAM config: {e}")

        return iam_config

    def collect_job_execution_history(
        self,
        namespace: str = 'abinitio-prod',
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Collect job execution history from Kubernetes"""
        logger.info(f"Collecting job history from last {days} days...")

        history = []

        try:
            # Get completed jobs
            result = subprocess.run(
                ['kubectl', 'get', 'jobs', '-n', namespace, '-o', 'json'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                jobs_data = json.loads(result.stdout)

                for job in jobs_data.get('items', []):
                    job_name = job['metadata']['name']
                    creation_time = job['metadata']['creationTimestamp']

                    # Check if within time window
                    created = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    if (datetime.now(created.tzinfo) - created).days > days:
                        continue

                    status = job.get('status', {})
                    succeeded = status.get('succeeded', 0)
                    failed = status.get('failed', 0)

                    # Get pod logs and events for more details
                    execution_data = {
                        'job_name': job_name.rsplit('-', 1)[0],  # Remove hash suffix
                        'execution_date': creation_time,
                        'status': 'SUCCESS' if succeeded > 0 else 'FAILED' if failed > 0 else 'RUNNING',
                        'duration_minutes': None,
                        'resources_used': {},
                        'failure_reason': None
                    }

                    # Get completion time
                    completion_time = status.get('completionTime')
                    if completion_time:
                        completed = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
                        duration = (completed - created).total_seconds() / 60
                        execution_data['duration_minutes'] = round(duration, 1)

                    history.append(execution_data)

        except Exception as e:
            logger.error(f"Error collecting job history: {e}")

        return history

    def save_metadata(self, output_file: str = 'collected_metadata.json'):
        """Collect all metadata and save to file"""
        logger.info("Starting metadata collection...")

        metadata = {
            'collection_timestamp': datetime.utcnow().isoformat(),
            'cluster_state': self.collect_eks_cluster_state(),
            'storage_config': self.collect_storage_config(),
            'iam_config': self.collect_iam_config('abinitio-batch-sa'),
            'job_history': self.collect_job_execution_history()
        }

        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✓ Metadata saved to {output_file}")
        logger.info(f"  - Cluster state: {len(metadata['cluster_state']['node_groups'])} node groups")
        logger.info(f"  - Storage: {len(metadata['storage_config']['efs_filesystems'])} EFS, "
                   f"{len(metadata['storage_config']['s3_buckets'])} S3 buckets")
        logger.info(f"  - Job history: {len(metadata['job_history'])} executions")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Collect EKS metadata for AI predictions')
    parser.add_argument('--cluster', required=True, help='EKS cluster name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--output', default='collected_metadata.json', help='Output file')
    parser.add_argument('--days', type=int, default=30, help='Days of history to collect')

    args = parser.parse_args()

    collector = MetadataCollector(args.cluster, args.region)
    collector.save_metadata(args.output)


if __name__ == '__main__':
    main()
