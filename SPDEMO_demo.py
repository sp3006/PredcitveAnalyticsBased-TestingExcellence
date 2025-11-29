#!/usr/bin/env python3
"""
AI-Powered EKS Job Failure Predictor - Interactive Demo

This demo uses Anthropic's Claude API to predict failures for Ab Initio jobs
running in EKS with AWS services (EFS, S3, IAM/IRSA).

Features:
- Interactive job selection
- Real-time AI-powered predictions using Claude
- Historical data analysis
- Actionable recommendations
- JIRA ticket preview
"""

import os
import sys
import json
import anthropic
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class EKSJobPredictor:
    """
    Interactive AI-powered job failure predictor
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize predictor with Anthropic API key"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')

        if not self.api_key:
            print(f"{Colors.FAIL}Error: ANTHROPIC_API_KEY not set{Colors.ENDC}")
            print("Set it with: export ANTHROPIC_API_KEY='your-api-key'")
            sys.exit(1)

        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Load demo data
        self.load_demo_data()

    def load_demo_data(self):
        """Load historical data and job configurations"""
        base_path = Path(__file__).parent

        # Load historical job executions
        history_file = base_path / 'SPDEMO_historical_job_data.json'
        with open(history_file, 'r') as f:
            self.historical_data = json.load(f)

        # Load sample job configurations
        config_file = base_path / 'SPDEMO_sample_job_configs.json'
        with open(config_file, 'r') as f:
            self.job_configs = json.load(f)

        # Load EKS cluster state
        cluster_file = base_path / 'config' / 'eks_cluster_config.yaml'
        try:
            import yaml
            with open(cluster_file, 'r') as f:
                self.cluster_config = yaml.safe_load(f)
        except:
            # Simplified cluster config if YAML load fails
            self.cluster_config = {
                'cluster_info': {
                    'cluster_name': 'bi-abi-apps-prod',
                    'region': 'us-east-1'
                },
                'node_groups': [{
                    'name': 'data-processing-ng',
                    'available_cpu': 20,
                    'available_memory_gi': 280
                }]
            }

        print(f"{Colors.OKGREEN}✓ Loaded demo data successfully{Colors.ENDC}")
        print(f"  - {len(self.historical_data['job_execution_history'])} historical executions")
        print(f"  - {len(self.job_configs['jobs'])} job configurations")
        print()

    def display_menu(self):
        """Display interactive menu"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== AI-Powered EKS Job Failure Predictor ==={Colors.ENDC}\n")
        print("Available Jobs:")

        for i, job in enumerate(self.job_configs['jobs'], 1):
            print(f"  {i}. {job['job_name']}")
            print(f"     {Colors.OKCYAN}{job['description']}{Colors.ENDC}")
            print(f"     Schedule: {job['schedule']}")
            print()

        print(f"  {len(self.job_configs['jobs']) + 1}. Analyze Historical Failures")
        print(f"  {len(self.job_configs['jobs']) + 2}. Exit")
        print()

    def get_historical_context(self, job_name: str) -> str:
        """Get historical execution context for a job"""
        job_history = [
            exec for exec in self.historical_data['job_execution_history']
            if exec['job_name'] == job_name
        ]

        if not job_history:
            return "No historical data available"

        successes = [e for e in job_history if e['status'] == 'SUCCESS']
        failures = [e for e in job_history if e['status'] == 'FAILED']

        context = f"Historical Context for {job_name}:\n"
        context += f"- Total executions: {len(job_history)}\n"
        context += f"- Successes: {len(successes)}\n"
        context += f"- Failures: {len(failures)}\n"

        if failures:
            context += "\nRecent Failures:\n"
            for failure in failures[:3]:
                context += f"  - {failure['execution_date']}: {failure['failure_reason']}\n"

        if successes:
            avg_memory = sum(s['resources_used']['peak_memory_gb'] for s in successes) / len(successes)
            avg_cpu = sum(s['resources_used']['avg_cpu_cores'] for s in successes) / len(successes)
            avg_storage = sum(s['resources_used']['storage_used_gb'] for s in successes) / len(successes)

            context += f"\nAverage Resource Usage (Successful Runs):\n"
            context += f"  - Memory: {avg_memory:.1f} GB\n"
            context += f"  - CPU: {avg_cpu:.1f} cores\n"
            context += f"  - Storage: {avg_storage:.1f} GB\n"

        return context

    def predict_with_claude(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Use Claude API to predict job failures"""

        job_name = job_config['job_name']
        historical_context = self.get_historical_context(job_name)

        # Build comprehensive context for Claude
        prompt = f"""You are an expert in predicting failures for Ab Initio jobs running on AWS EKS.

Analyze this job configuration and predict potential failures:

**Job Configuration:**
```json
{json.dumps(job_config, indent=2)}
```

**Historical Execution Data:**
{historical_context}

**EKS Cluster State:**
- Available CPU: {self.cluster_config['node_groups'][0]['available_cpu']} cores
- Available Memory: {self.cluster_config['node_groups'][0]['available_memory_gi']} GB
- Cluster: {self.cluster_config['cluster_info']['cluster_name']}

**Analysis Required:**

Predict failures across these categories:
1. **Pod Scheduling** - Will the pod be schedulable given current cluster resources?
2. **EFS Mount** - Will EFS mount succeed?
3. **Memory (OOMKill)** - Will the job exceed memory limits?
4. **IAM Permissions** - Are required AWS permissions in place?
5. **Data Quality** - Will duplicate data cause issues?

For each category, provide:
- **Probability** (0-100%)
- **Severity** (LOW, MEDIUM, HIGH, CRITICAL)
- **Root Cause** (why this failure might occur)
- **Recommendations** (how to prevent it)

Return your analysis as a JSON object with this structure:
{{
  "predictions": {{
    "pod_scheduling": {{
      "probability": <number>,
      "severity": "<string>",
      "root_cause": "<string>",
      "recommendations": ["<string>", ...]
    }},
    "efs_mount": {{ ... }},
    "memory_oomkill": {{ ... }},
    "iam_permissions": {{ ... }},
    "data_quality": {{ ... }}
  }},
  "overall_assessment": {{
    "should_execute": <boolean>,
    "overall_severity": "<string>",
    "overall_probability": <number>,
    "recommendation": "<string>"
  }},
  "estimated_effort": {{
    "category": "SIMPLE|MEDIUM|COMPLEX|CRITICAL",
    "story_points": <number>,
    "estimated_hours": "<string>"
  }}
}}

Provide only the JSON output, no additional text."""

        print(f"{Colors.OKCYAN}🤖 Analyzing with Claude AI...{Colors.ENDC}")

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.3,  # Lower temperature for more consistent predictions
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to parse JSON
            # Sometimes Claude wraps JSON in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            predictions = json.loads(response_text.strip())

            return predictions

        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}Error parsing Claude response: {e}{Colors.ENDC}")
            print(f"Response: {response_text[:500]}")
            return None
        except Exception as e:
            print(f"{Colors.FAIL}Error calling Claude API: {e}{Colors.ENDC}")
            return None

    def display_predictions(self, predictions: Dict[str, Any], job_name: str):
        """Display prediction results in a formatted way"""

        if not predictions:
            print(f"{Colors.FAIL}No predictions available{Colors.ENDC}")
            return

        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Prediction Results for {job_name} ==={Colors.ENDC}\n")

        # Overall Assessment
        overall = predictions.get('overall_assessment', {})
        should_execute = overall.get('should_execute', True)
        overall_severity = overall.get('overall_severity', 'UNKNOWN')

        if should_execute:
            status_color = Colors.OKGREEN
            status_icon = "✓"
        else:
            status_color = Colors.FAIL
            status_icon = "✗"

        print(f"{status_color}{Colors.BOLD}{status_icon} Overall Decision: {'SAFE TO EXECUTE' if should_execute else 'DO NOT EXECUTE'}{Colors.ENDC}")
        print(f"Severity: {self._severity_color(overall_severity)}{overall_severity}{Colors.ENDC}")
        print(f"Recommendation: {overall.get('recommendation', 'N/A')}")
        print()

        # Individual Predictions
        print(f"{Colors.BOLD}Detailed Analysis:{Colors.ENDC}\n")

        pred_details = predictions.get('predictions', {})

        for pred_type, details in pred_details.items():
            probability = details.get('probability', 0)
            severity = details.get('severity', 'UNKNOWN')

            print(f"{Colors.BOLD}{pred_type.replace('_', ' ').title()}{Colors.ENDC}")
            print(f"  Probability: {self._prob_color(probability)}{probability}%{Colors.ENDC}")
            print(f"  Severity: {self._severity_color(severity)}{severity}{Colors.ENDC}")
            print(f"  Cause: {details.get('root_cause', 'N/A')}")

            recommendations = details.get('recommendations', [])
            if recommendations:
                print(f"  Recommendations:")
                for rec in recommendations:
                    print(f"    • {rec}")
            print()

        # Effort Estimation
        effort = predictions.get('estimated_effort', {})
        if effort:
            print(f"{Colors.BOLD}Effort Estimation:{Colors.ENDC}")
            print(f"  Category: {effort.get('category', 'N/A')}")
            print(f"  Story Points: {effort.get('story_points', 'N/A')}")
            print(f"  Estimated Hours: {effort.get('estimated_hours', 'N/A')}")
            print()

    def _prob_color(self, probability: float) -> str:
        """Get color based on probability"""
        if probability >= 70:
            return Colors.FAIL
        elif probability >= 40:
            return Colors.WARNING
        else:
            return Colors.OKGREEN

    def _severity_color(self, severity: str) -> str:
        """Get color based on severity"""
        severity_map = {
            'CRITICAL': Colors.FAIL,
            'HIGH': Colors.WARNING,
            'MEDIUM': Colors.OKCYAN,
            'LOW': Colors.OKGREEN
        }
        return severity_map.get(severity, Colors.ENDC)

    def analyze_historical_failures(self):
        """Analyze historical failures with Claude"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Historical Failure Analysis ==={Colors.ENDC}\n")

        failures = [
            exec for exec in self.historical_data['job_execution_history']
            if exec['status'] == 'FAILED'
        ]

        if not failures:
            print("No failures found in historical data")
            return

        print(f"Found {len(failures)} failures. Analyzing patterns...\n")

        # Build failure summary for Claude
        failure_summary = []
        for f in failures:
            failure_summary.append({
                'job': f['job_name'],
                'date': f['execution_date'],
                'reason': f['failure_reason'],
                'details': f.get('error_details', {})
            })

        prompt = f"""Analyze these historical job failures and identify patterns:

**Historical Failures:**
```json
{json.dumps(failure_summary, indent=2)}
```

Provide:
1. Common failure patterns
2. Root cause categories
3. Preventive measures
4. Priority recommendations

Format as a concise analysis."""

        print(f"{Colors.OKCYAN}🤖 Analyzing with Claude AI...{Colors.ENDC}\n")

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            analysis = message.content[0].text
            print(analysis)
            print()

        except Exception as e:
            print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}")

    def run_interactive_demo(self):
        """Run the interactive demo"""

        while True:
            self.display_menu()

            try:
                choice = input(f"{Colors.BOLD}Select option: {Colors.ENDC}")
                choice_num = int(choice)

                if choice_num == len(self.job_configs['jobs']) + 1:
                    # Analyze historical failures
                    self.analyze_historical_failures()
                    input("\nPress Enter to continue...")

                elif choice_num == len(self.job_configs['jobs']) + 2:
                    # Exit
                    print(f"\n{Colors.OKGREEN}Thank you for using the EKS Job Predictor!{Colors.ENDC}\n")
                    break

                elif 1 <= choice_num <= len(self.job_configs['jobs']):
                    # Predict for selected job
                    job_config = self.job_configs['jobs'][choice_num - 1]

                    print(f"\n{Colors.OKCYAN}Analyzing: {job_config['job_name']}{Colors.ENDC}")

                    predictions = self.predict_with_claude(job_config)

                    if predictions:
                        self.display_predictions(predictions, job_config['job_name'])

                        # Ask if user wants to save results
                        save = input(f"\n{Colors.BOLD}Save predictions to file? (y/n): {Colors.ENDC}")
                        if save.lower() == 'y':
                            self.save_predictions(predictions, job_config['job_name'])

                    input("\nPress Enter to continue...")

                else:
                    print(f"{Colors.FAIL}Invalid option{Colors.ENDC}")

            except ValueError:
                print(f"{Colors.FAIL}Please enter a number{Colors.ENDC}")
            except KeyboardInterrupt:
                print(f"\n\n{Colors.OKGREEN}Exiting...{Colors.ENDC}\n")
                break
            except Exception as e:
                print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}")

    def save_predictions(self, predictions: Dict[str, Any], job_name: str):
        """Save predictions to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"SPDEMO_prediction_{job_name}_{timestamp}.json"

        output = {
            'job_name': job_name,
            'timestamp': timestamp,
            'predictions': predictions
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"{Colors.OKGREEN}✓ Saved to {filename}{Colors.ENDC}")


def main():
    """Main entry point"""

    print(f"""
{Colors.HEADER}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════╗
║   AI-Powered EKS Job Failure Predictor - Demo            ║
║   Using Anthropic Claude API                             ║
╚═══════════════════════════════════════════════════════════╝
{Colors.ENDC}
""")

    print("This demo predicts failures for Ab Initio jobs running in EKS")
    print("with AWS services (EFS, S3, IAM/IRSA)\n")

    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print(f"{Colors.WARNING}Note: Set ANTHROPIC_API_KEY environment variable{Colors.ENDC}")
        print(f"{Colors.WARNING}Get your API key from: https://console.anthropic.com/{Colors.ENDC}\n")

        api_key = input("Enter your Anthropic API key (or press Enter to use env var): ").strip()
        if api_key:
            os.environ['ANTHROPIC_API_KEY'] = api_key

    try:
        predictor = EKSJobPredictor()
        predictor.run_interactive_demo()
    except Exception as e:
        print(f"{Colors.FAIL}Fatal error: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == '__main__':
    main()
