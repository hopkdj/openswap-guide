---
title: "Self-Hosted Infrastructure Drift Detection: Driftctl, Cloud Custodian & OpenTofu Guide 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "devops", "infrastructure", "terraform"]
draft: false
description: "Compare self-hosted infrastructure drift detection tools — Driftctl, Cloud Custodian, and OpenTofu — to keep your cloud infrastructure in sync with your IaC definitions."
---

## Why Infrastructure Drift Detection Matters

Infrastructure as Code (IaC) tools like Terraform and OpenTofu let you define cloud resources declaratively. But in practice, your real-world infrastructure almost always diverges from your code. Someone makes a manual change in the AWS console, a security team patches a security group, an autoscaler launches instances outside your Terraform state, or a team member deletes a resource directly. These are all examples of **infrastructure drift** — the gap between what your IaC says should exist and what actually exists in your cloud environment.

Left unchecked, drift causes outages, security vulnerabilities, cost overruns, and compliance failures. When your next `terraform apply` runs, it may delete manually-created resources, revert security patches, or fail entirely because the state no longer matches reality.

Drift detection tools solve this problem by comparing your IaC definitions against live cloud resources and alerting you to discrepancies before they cause damage. In this guide, we compare three leading self-hosted approaches: **Driftctl**, **Cloud Custodian**, and **OpenTofu's built-in drift detection**.

## Tool Overview & Quick Comparison

| Feature | Driftctl | Cloud Custodian | OpenTofu Built-in |
|---|---|---|---|
| **Primary Focus** | Infrastructure drift detection | Cloud governance & policy enforcement | IaC state management |
| **Supported Clouds** | AWS, Azure, GCP, Kubernetes | AWS, Azure, GCP, Kubernetes, OCI | Any Terraform provider |
| **Language** | Go | Python (YAML DSL) | Go |
| **License** | Apache 2.0 | Apache 2.0 | MPL 2.0 |
| **GitHub Stars** | 2,634 | 5,967 | 28,441 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Docker Support** | Official image | Official image | Official image |
| **CI/CD Integration** | Native | Native | Native (`tofu plan`) |
| **Policy Engine** | No (drift-only) | Yes (rules engine) | No (state-only) |
| **Cost Analysis** | No | Yes | Via Infracost plugin |

## Driftctl: Dedicated Drift Detection by Snyk

**Driftctl** is an open-source CLI tool developed by Snyk specifically for detecting infrastructure drift. It scans your cloud provider APIs, compares the results against your Terraform state, and generates a detailed report of all discrepancies.

### How Driftctl Works

Driftctl reads your Terraform state file (`.tfstate`) and then queries your cloud provider's APIs to enumerate all actual resources. It compares the two lists and categorizes differences into:

- **Unmanaged resources** — exist in the cloud but not in your Terraform state
- **Deleted resources** — defined in Terraform but missing from the cloud
- **Drifted resources** — exist in both but have configuration differences

### Installation

```bash
# Linux/macOS via curl
curl -sSfL https://driftctl.sh/install.sh | sh

# Or via Homebrew
brew install driftctl

# Or via Docker
docker run --rm -t \
  -v "$HOME/.aws:/root/.aws:ro" \
  ghcr.io/snyk/driftctl:latest scan
```

### Docker Compose Configuration

For CI/CD integration, you can run driftctl as part of a pipeline:

```yaml
version: "3.8"
services:
  driftctl:
    image: ghcr.io/snyk/driftctl:latest
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}
    volumes:
      - ./terraform:/terraform:ro
    working_dir: /terraform
    command: scan --from tfstate://terraform.tfstate --output html://drift-report.html
```

### Running a Scan

```bash
# Basic scan against AWS
driftctl scan --from tfstate://terraform.tfstate

# Scan with output to JSON for CI pipelines
driftctl scan --from tfstate://terraform.tfstate --output json://drift.json

# Scan specific resources only
driftctl scan --filter "Type=='aws_instance'"
```

### Sample Output

```
Found 47 resource(s)
  - 42 in Terraform state
  - 5 were not managed by IaC

  ✓ aws_s3_bucket.my_bucket (in sync)
  ✓ aws_security_group.web (in sync)
  ~ aws_instance.web_server (drifted: tags changed)
  + aws_security_group.manual_patch (unmanaged)
  - aws_cloudwatch_alarm.cpu_alert (deleted)

Coverage: 89% (42/47 resources managed)
```

### Use Cases

Driftctl is best for teams that want a **dedicated, purpose-built drift detection tool** with minimal configuration. Its filtering system lets you exclude known unmanaged resources (like VPC default security groups), and its HTML/JSON output formats integrate well with CI/CD dashboards and alerting systems.

## Cloud Custodian: Policy-Based Cloud Governance

**Cloud Custodian** by the Cloud Native Computing Foundation (CNCF) is a rules engine for cloud security, cost optimization, and governance. While not exclusively a drift detection tool, its policy engine can detect and remediate infrastructure drift as part of broader governance workflows.

### How Cloud Custodian Works

Cloud Custodian uses YAML-based policies to define desired state rules. It evaluates these rules against your actual cloud resources via provider APIs. When a resource violates a policy, Cloud Custodian can alert, tag, or even automatically remediate the violation.

### Installation

```bash
# Via pip
pip install c7n

# Or via Docker
docker pull cloudcustodian/custodian

# Via Docker Compose (see below)
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  custodian:
    image: cloudcustodian/custodian:latest
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}
    volumes:
      - ./policies:/policies:ro
      - ./output:/output
    working_dir: /policies
    command: run -s /output drift-detection.yml
```

### Drift Detection Policies

Here is a policy that detects unmanaged security groups:

```yaml
policies:
  - name: detect-unmanaged-security-groups
    resource: aws.security-group
    description: |
      Find security groups not tagged as managed by Terraform
    filters:
      - "tag:managed-by": absent
    actions:
      - type: notify
        to:
          - security-team@company.com
        transport:
          type: sqs
          queue: https://sqs.us-east-1.amazonaws.com/123456789/drift-alerts

  - name: detect-untagged-ec2-instances
    resource: aws.ec2
    filters:
      - "tag:Terraform": absent
      - State.Name: running
    actions:
      - type: tag
        key: "drift-detected"
        value: "true"
      - type: notify
        to:
          - infra-team@company.com
        transport:
          type: sns
          topic: arn:aws:sns:us-east-1:123456789:drift-alerts

  - name: detect-modified-security-group-rules
    resource: aws.security-group
    filters:
      - type: value
        key: "tag:Terraform-Hash"
        op: ne
        value: "expected-hash-value"
    actions:
      - type: notify
        to:
          - security@company.com
        subject: "Security group drift detected"
```

### Scheduled Execution

Cloud Custodian integrates with AWS Lambda, Azure Functions, and Kubernetes CronJobs for scheduled drift detection:

```bash
# Run on a schedule via cron
0 */6 * * * custodian run -s /var/log/custodian /policies/drift-detection.yml

# Or via Kubernetes CronJob
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: drift-detection
spec:
  schedule: "0 */6 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: custodian
            image: cloudcustodian/custodian:latest
            command: ["custodian", "run", "-s", "/output", "/policies/drift.yml"]
          restartPolicy: OnFailure
EOF
```

### Use Cases

Cloud Custodian excels when you need **drift detection as part of a broader governance strategy**. Its policy engine handles not just drift, but also cost optimization, security compliance, and automated remediation — all from a single YAML configuration.

## OpenTofu Built-in Drift Detection

**OpenTofu** (the open-source fork of Terraform) includes built-in drift detection through its `plan` and `refresh` commands. While not a standalone drift detection tool, OpenTofu's native capabilities are the most straightforward way to detect drift for teams already using OpenTofu or Terraform as their primary IaC tool.

### How OpenTofu Detects Drift

OpenTofu maintains a state file that tracks the last-known configuration of each managed resource. When you run `tofu plan`, OpenTofu:

1. Reads the current state file
2. Queries the cloud provider for the actual resource configuration
3. Compares the two and generates an execution plan showing any differences

### Installation

```bash
# Linux
curl -fsSL https://get.opentofu.org/install.sh | bash

# macOS
brew install opentofu

# Docker
docker pull opentofu/tofu:latest
```

### Docker Compose for CI/CD Drift Detection

```yaml
version: "3.8"
services:
  tofu-drift:
    image: opentofu/tofu:latest
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}
    volumes:
      - ./infrastructure:/workspace
    working_dir: /workspace
    command: |
      sh -c "
        tofu init -backend=true &&
        tofu plan -input=false -out=tfplan &&
        tofu show -json tfplan > /output/drift-report.json
      "
```

### Drift Detection Commands

```bash
# Quick drift check (no state modifications)
tofu plan -input=false -detailed-exitcode

# Exit code meanings:
# 0 = No changes (no drift)
# 1 = Error
# 2 = Changes present (drift detected)

# Full refresh and plan
tofu refresh
tofu plan -input=false

# Generate JSON report for CI integration
tofu plan -input=false -out=tfplan
tofu show -json tfplan > drift-report.json
```

### Automating Drift Detection in CI/CD

Here is a GitLab CI pipeline step for automated drift detection:

```yaml
drift-detection:
  image: opentofu/tofu:latest
  stage: test
  script:
    - tofu init -backend=true
    - tofu plan -input=false -detailed-exitcode || EXIT_CODE=$?
    - |
      if [ "${EXIT_CODE:-0}" = "2" ]; then
        echo "DRIFT DETECTED"
        tofu show tfplan > drift-details.txt
        exit 1
      fi
  only:
    - schedules
    - main
```

### Use Cases

OpenTofu's built-in drift detection is the **simplest option for teams already using OpenTofu or Terraform**. It requires no additional tools, integrates natively with your existing CI/CD pipelines, and provides detailed change plans for every drifted resource.

## Comparing All Three Approaches

| Criterion | Driftctl | Cloud Custodian | OpenTofu Built-in |
|---|---|---|---|
| **Setup Complexity** | Low | Medium | Low |
| **Drift Detail Level** | High (field-level) | Medium (tag/policy-based) | High (full plan diff) |
| **Remediation** | Report only | Auto-remediate possible | Via `tofu apply` |
| **Multi-Cloud** | Yes (AWS, Azure, GCP, K8s) | Yes (AWS, Azure, GCP, K8s, OCI) | Yes (any provider) |
| **Scheduling** | Via CI/cron | Native (Lambda, K8s CronJob) | Via CI/cron |
| **Alerting** | HTML/JSON output | SNS, SQS, email, Slack | Exit codes, JSON plan |
| **State File Required** | Yes | No | Yes |
| **Best For** | Dedicated drift monitoring | Governance + drift | Existing OpenTofu users |

## When to Use Each Tool

### Choose Driftctl When
- You want a dedicated, purpose-built drift detection tool
- You need detailed field-level drift reports
- You manage multiple IaC tools (Terraform, CloudFormation, Pulumi) and want a single drift scanner
- You need to exclude specific resources from drift analysis

### Choose Cloud Custodian When
- You want drift detection as part of broader cloud governance
- You need automated remediation (not just detection)
- You manage multi-cloud environments with unified policies
- You need cost optimization and security compliance alongside drift detection

### Choose OpenTofu Built-in When
- You already use OpenTofu or Terraform as your primary IaC tool
- You want the simplest possible setup with zero additional dependencies
- Your CI/CD pipeline already runs Terraform/OpenTofu commands
- You need detailed change plans that can be directly applied to fix drift

## CI/CD Integration Examples

### GitHub Actions with Driftctl

```yaml
name: Infrastructure Drift Detection
on:
  schedule:
    - cron: "0 */6 * * *"  # Every 6 hours
  workflow_dispatch:

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run driftctl
        uses: snyk/actions/driftctl@master
        with:
          args: scan --from tfstate://terraform.tfstate --output json://drift.json
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      - name: Upload drift report
        uses: actions/upload-artifact@v4
        with:
          name: drift-report
          path: drift.json
```

### Drift Detection with Slack Alerts

```bash
#!/bin/bash
# drift-check.sh - Run drift detection and notify Slack

DRIFT_OUTPUT=$(driftctl scan --from tfstate://terraform.tfstate --output json 2>&1)
UNMANAGED=$(echo "$DRIFT_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('summary',{}).get('unmanaged',0))")

if [ "$UNMANAGED" -gt 0 ]; then
  curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"⚠️ Infrastructure drift detected: $UNMANAGED unmanaged resource(s)\"}" \
    "$SLACK_WEBHOOK_URL"
  exit 1
fi

echo "No drift detected. Infrastructure is in sync."
exit 0
```

## FAQ

### What is infrastructure drift and why is it dangerous?

Infrastructure drift occurs when your actual cloud resources diverge from the definitions in your Infrastructure as Code (IaC) tool. This happens when someone makes manual changes in the cloud console, when auto-scaling creates resources outside your IaC, or when security patches are applied directly to resources. Drift is dangerous because it can cause unexpected behavior during your next deployment, create security vulnerabilities, increase costs, and make compliance audits impossible to pass.

### How often should I run drift detection?

For production environments, run drift detection at least every 6 hours. For critical infrastructure with strict compliance requirements, consider running it hourly. Most teams integrate drift detection into their CI/CD pipelines as a scheduled job that runs independently of deployments. The key is catching drift early, before it compounds into larger problems.

### Can drift detection tools automatically fix drift?

It depends on the tool. OpenTofu can fix drift by running `tofu apply`, which brings resources back into sync with your IaC definitions. Cloud Custodian can auto-remediate specific drift scenarios through its policy actions (e.g., re-tagging resources, reverting security group rules). Driftctl is report-only — it detects and alerts but does not fix drift. In all cases, automated remediation should be used carefully, as it may overwrite intentional manual changes.

### Do I need a dedicated drift detection tool if I already use Terraform or OpenTofu?

Not necessarily. If your only goal is to detect drift for Terraform/OpenTofu-managed resources, the built-in `tofu plan` command is sufficient. However, dedicated tools like Driftctl offer advantages: they detect unmanaged resources (things in your cloud that aren't in any IaC), they provide formatted reports for dashboards, and they can scan multiple IaC tool states simultaneously. Cloud Custodian adds policy-based governance on top of drift detection.

### Does drift detection work with Kubernetes resources?

Yes. Both Driftctl and Cloud Custodian support Kubernetes resource drift detection. Driftctl can scan Kubernetes clusters and compare actual resources against Terraform-managed Kubernetes definitions. Cloud Custodian has extensive Kubernetes policies for detecting drift in deployments, services, RBAC roles, and other cluster resources. OpenTofu's built-in drift detection also works with Kubernetes through the Kubernetes provider.

### How do I exclude resources from drift detection?

In Driftctl, use the `--exclude` flag or create a `.driftctlignore` file with resource patterns to skip. For example, you typically want to exclude default VPC security groups, auto-created CloudWatch log groups, and load balancer default listeners. Cloud Custodian uses policy filters to define which resources are in scope. OpenTofu's drift detection is limited to resources in your state file, so anything not managed by OpenTofu is automatically excluded.

## Further Reading

For related reading, see our [OpenTofu vs Terraform vs Pulumi IaC comparison](../opentofu-vs-terraform-vs-pulumi-self-hosted-iac-guide-2026/) and our [IaC security scanning guide covering Checkov, tfsec, and Trivy](../checkov-vs-tfsec-vs-trivy-self-hosted-iac-security-scanning-2026/). You may also find our [CI/CD pipeline guide with Woodpecker, Drone, and Gitea Actions](../2026-04-19-woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/) useful for automating drift detection in your pipelines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Infrastructure Drift Detection: Driftctl, Cloud Custodian & OpenTofu Guide 2026",
  "description": "Compare self-hosted infrastructure drift detection tools — Driftctl, Cloud Custodian, and OpenTofu — to keep your cloud infrastructure in sync with your IaC definitions.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
