---
title: "Checkov vs tfsec vs Trivy: Self-Hosted IaC Security Scanning 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "security", "devops", "iac"]
draft: false
description: "Compare Checkov, tfsec, and Trivy for self-hosted infrastructure-as-code security scanning. Learn which open-source tool best fits your Terraform, Kubernetes, and cloud compliance needs."
---

Infrastructure-as-code has become the standard for provisioning cloud resources, [kubernetes](https://kubernetes.io/) clusters, and container deployments. But with every Terraform module, Helm chart, and [docker](https://www.docker.com/)file committed to version control comes a critical question: **is your infrastructure configuration actually secure?**

Cloud misconfigurations are the leading cause of data breaches in modern deployments. An exposed S3 bucket, an overly permissive IAM role, or a Kubernetes pod running as root can compromise your entire environment. Self-hosted IaC scanning tools catch these issues **before** you apply changes — no cloud API keys required, no data sent to third-party services.

This guide compares three open-source IaC security scanners — Checkov, tfsec, and Trivy — evaluating their coverage, accuracy, deployment options, and CI/CD integration so you can choose the right tool for your pipeline.

For related reading, see our [OpenTofu vs Terraform vs Pulumi guide](../opentofu-vs-terraform-vs-pulumi-self-hosted-iac-guide-2026/) for infrastructure-as-code platform comparisons, and our [Trivy vulnerability scanner guide](../openvas-trivy-grype-self-hosted-vulnerability-scanner-guide/) for a broader look at Trivy's capabilities beyond IaC.

## Why Self-Host Infrastructure-as-Code Scanning

Running IaC security scanners on your own infrastructure offers several advantages over SaaS alternatives:

- **Full code privacy**: Your Terraform files, Kubernetes manifests, and CloudFormation templates never leave your network. For regulated industries (finance, healthcare, government), this is often a compliance requirement.
- **No API rate limits**: Cloud-based scanners may throttle scans or require API tokens. Self-hosted tools run locally with no external dependencies.
- **Faster feedback loops**: Local scanning completes in seconds, providing immediate feedback during development rather than waiting for a remote service to respond.
- **Custom policies**: You can write and test custom security policies that reflect your organization's specific requirements without waiting for a vendor to add support.
- **Offline operation**: Air-gapped environments (common in defense, critical infrastructure, and some enterprise setups) require tools that work without internet connectivity.

All three tools covered in this guide — Checkov, tfsec, and Trivy — are fully self-hostable, open-source, and support scanning without sending any data to external services.

## Checkov: Comprehensive Cloud-Native Policy Engine

**Checkov** by Bridgecrew (now part of Palo Alto Networks) is a policy-as-code framework that scans infrastructure-as-code files for security misconfigurations. It supports the broadest range of IaC formats among the three tools.

| Attribute | Details |
|-----------|---------|
| **Repository** | bridgecrewio/checkov |
| **Stars** | 8,645+ |
| **Last Updated** | April 2026 |
| **License** | Apache 2.0 |
| **Language** | Python |
| **Best For** | Multi-cloud policy enforcement with custom rule writing |

### Supported Scanners

Checkov includes dedicated scanners for:

- **Terraform** (AWS, Azure, GCP, Oracle Cloud, GitHub, Kubernetes)
- **CloudFormation** (AWS)
- **Kubernetes** (YAML, Helm, Kustomize)
- **Dockerfile**
- **ARM Templates** (Azure)
- **Serverless Framework**
- **OpenAPI/Swagger**
- **Bicep** (Azure)
- **Terraform Plan** JSON

### Policy Framework

Checkov's policy engine uses Python classes or YAML definitions. Each policy includes:

- A unique ID (e.g., `CKV_AWS_20`)
- Severity level (CRITICAL, HIGH, MEDIUM, LOW)
- Supported resource types
- The actual evaluation logic

You can write custom policies that check for organization-specific requirements:

```python
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck

class S3BucketVersioning(BaseResourceCheck):
    def __init__(self):
        name = "Ensure S3 bucket has versioning enabled"
        id = "CKV_AWS_999"
        supported_resources = ["aws_s3_bucket"]
        categories = [CheckCategories.BACKUP_AND_RECOVERY]
        super().__init__(name=name, id=id, categories=categories, supported_resources=supported_resources)

    def scan_resource_conf(self, conf):
        if "versioning" in conf:
            versioning_block = conf["versioning"]
            if isinstance(versioning_block, list):
                versioning_block = versioning_block[0]
            if versioning_block.get("enabled") is True:
                return CheckResult.PASSED
        return CheckResult.FAILED
```

## tfsec: Fast Terraform-Focused Scanner

**tfsec** was a dedicated Terraform static analysis tool known for its speed and simplicity. In 2023, the tfsec project was merged into **Trivy**, and the standalone tfsec repository is now in maintenance mode. The tfsec scanning engine lives on inside Trivy's `trivy config` command.

| Attribute | Details |
|-----------|---------|
| **Repository** | aquasecurity/tfsec |
| **Stars** | 6,986+ |
| **Status** | Merged into Trivy (maintenance mode) |
| **License** | MIT |
| **Language** | Go |
| **Best For** | Teams already using Trivy who need Terraform scanning |

### Supported Scanners

tfsec focuses exclusively on Terraform, with support for:

- **AWS** provider (most extensive coverage)
- **Azure** provider
- **GCP** provider
- **DigitalOcean** provider
- **OpenStack** provider
- **GitHub** provider
- **Kubernetes** provider
- **Oracle Cloud** provider
- **CloudStack** provider
- **Nutanix** provider

### Why tfsec Merged into Trivy

The merger makes strategic sense: Aqua Security's Trivy already handled container image scanning and SBOM generation. Adding Terraform scanning created a unified security tool that covers the entire software supply chain — from code to container to cloud infrastructure.

For existing tfsec users, the migration is straightforward. The `tfsec` CLI flags map directly to `trivy config` flags, and the underlying Rego-based policies are largely compatible.

## Trivy: Universal Security Scanner

**Trivy** by Aqua Security is a comprehensive vulnerability and misconfiguration scanner. While it started as a container image scanner, it now covers IaC files, SBOM generation, Kubernetes clusters, and Git repositories.

| Attribute | Details |
|-----------|---------|
| **Repository** | aquasecurity/trivy |
| **Stars** | 34,596+ |
| **Last Updated** | April 2026 |
| **License** | Apache 2.0 |
| **Language** | Go |
| **Best For** | Teams wanting a single scanner for containers + IaC + SBOM |

### Supported Scanners

Trivy's `trivy config` subcommand handles:

- **Terraform** (including tfsec-compatible checks)
- **CloudFormation**
- **Kubernetes** (YAML, Helm, Kustomize, Dockerfile)
- **Dockerfile**
- **Helm Charts**
- **Terraform Plan** JSON
- **Azure ARM Templates**
- **Ansible**
- **RedHat Openshift**

Additionally, Trivy scans:

- **Container images** (OS packages, application dependencies)
- **Filesystems** and root filesystems
- **Git repositories**
- **Virtual machine images**
- **Kubernetes clusters** (live)
- **SBOM** generation and validation

### Custom Policies

Trivy uses **Rego** (Open Policy Agent's query language) for custom policies, making it compatible with OPA/Gatekeeper deployments:

```rego
package terraform.aws.s3

__rego_metadata := {
    "id": "CUS001",
    "title": "S3 Bucket Versioning Required",
    "severity": "HIGH",
    "type": "Terraform Security Check",
}

deny contains msg {
    resource := input.aws_s3_bucket[_]
    not resource.versioning[0].enabled
    msg := sprintf("S3 bucket '%s' does not have versioning enabled", [resource.__address__])
}
```

## Feature Comparison

| Feature | Checkov | tfsec | Trivy |
|---------|---------|-------|-------|
| **Terraform scanning** | ✅ Yes | ✅ Yes (native) | ✅ Yes (via tfsec engine) |
| **CloudFormation** | ✅ Yes | ❌ No | ✅ Yes |
| **Kubernetes YAML** | ✅ Yes | ❌ No | ✅ Yes |
| **Dockerfile** | ✅ Yes | ❌ No | ✅ Yes |
| **Helm charts** | ✅ Yes | ❌ No | ✅ Yes |
| **ARM Templates** | ✅ Yes | ❌ No | ✅ Yes |
| **Serverless Framework** | ✅ Yes | ❌ No | ❌ No |
| **Ansible** | ❌ No | ❌ No | ✅ Yes |
| **Bicep** | ✅ Yes | ❌ No | ✅ Yes |
| **OpenAPI** | ✅ Yes | ❌ No | ❌ No |
| **Container images** | ❌ No | ❌ No | ✅ Yes |
| **SBOM generation** | ❌ No | ❌ No | ✅ Yes |
| **Custom policies** | Python, YAML | Rego | Rego |
| **Suppression comments** | ✅ Yes | ✅ Yes | ✅ Yes |
| **SARIF output** | ✅ Yes | ✅ Yes | ✅ Yes |
| **JSON output** | ✅ Yes | ✅ Yes | ✅ Yes |
| **JUnit XML output** | ✅ Yes | ❌ No | ✅ Yes |
| **Language** | Python | Go | Go |
| **License** | Apache 2.0 | MIT | Apache 2.0 |
| **Standalone Docker image** | ✅ Yes | ❌ No | ✅ Yes |

## Installation & Deployment

### Checkov

**Via pip (recommended):**

```bash
pip install checkov
```

**Via Docker:**

```bash
docker run --tty --volume /path/to/tf:/tf \
  bridgecrew/checkov --directory /tf --compact
```

**Docker Compose** for a persistent scanning service:

```yaml
version: "3.8"

services:
  checkov:
    image: bridgecrew/checkov:latest
    container_name: checkov-scanner
    volumes:
      - ./iac:/iac:ro
      - ./policies:/checkov-policies:ro
      - ./reports:/reports:rw
    command: >
      --directory /iac
      --output json
      --output-file-path /reports/checkov-results.json
      --external-checks-dir /checkov-policies
      --compact
    restart: unless-stopped
```

### Trivy (includes tfsec engine)

**Via package manager (Debian/Ubuntu):**

```bash
sudo apt-get install wget apt-transport-https gnupg
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

**Via Docker:**

```bash
docker run --rm -v /path/to/tf:/project \
  aquasec/trivy:latest config /project
```

**Docker Compose** with persistent vulnerability database:

```yaml
version: "3.8"

services:
  trivy:
    image: aquasec/trivy:latest
    container_name: trivy-scanner
    volumes:
      - ./iac:/project:ro
      - trivy-cache:/root/.cache/trivy
      - ./reports:/reports:rw
    environment:
      - TRIVY_CACHE_DIR=/root/.cache/trivy
    command: >
      config /project
      --format json
      --output /reports/trivy-results.json
      --exit-code 1
      --severity HIGH,CRITICAL
    restart: unless-stopped

volumes:
  trivy-cache:
```

## Scanning Terraform Files

### Checkov: Scanning a Terraform Project

```bash
# Scan directory recursively
checkov -d ./terraform --compact

# Scan single file
checkov -f ./terraform/main.tf

# Skip specific checks
checkov -d ./terraform --skip-check CKV_AWS_20,CKV_AWS_21

# Run only specific checks
checkov -d ./terraform --check CKV_AWS_20

# Output as SARIF for GitHub/GitLab integration
checkov -d ./terraform --output sarif --output-file-path results.sarif

# Use custom policies
checkov -d ./terraform --external-checks-dir ./custom-policies
```

### Trivy: Scanning the Same Terraform Project

```bash
# Scan directory with tfsec-compatible engine
trivy config ./terraform

# Scan single file
trivy config ./terraform/main.tf

# Set severity threshold
trivy config ./terraform --severity HIGH,CRITICAL

# Output as JSON
trivy config ./terraform --format json --output results.json

# Skip specific IDs
trivy config ./terraform --ignorefile .trivyignore

# Include suppressed findings
trivy config ./terraform --show-suppressed
```

### Example Scan Output

A typical Checkov scan of a Terraform project with an unencrypted S3 bucket:

```
Check: CKV_AWS_19: "Ensure all data stored in the S3 bucket have versioning enabled"
    FAILED for resource: aws_s3_bucket.data
    File: /main.tf:10-20
    Guide: https://docs.prismacloud.io/en/enterprise-edition/...

Check: CKV_AWS_20: "Ensure all data stored in the S3 bucket is securely encrypted at rest"
    FAILED for resource: aws_s3_bucket.data
    File: /main.tf:10-20
```

A Trivy scan of the same configuration:

```
2026-04-19T08:00:00Z    INFO    Detected config files: 1
main.tf (terraform)
Tests: 12 (SUCCESSES: 10, FAILURES: 2, EXCEPTIONS: 0)
Failures: 2 (UNKNOWN: 0, LOW: 0, MEDIUM: 1, HIGH: 1, CRITICAL: 0)

HIGH: S3 bucket has no server-side encryption
═══════════════════════════════════════════════════════════════════════
 File: main.tf
    10-20
───────────────────────────────────────────────────────────────────────
 10: resource "aws_s3_bucket" "data" {
```

## Scanning Kubernetes Manifests

### Checkov: Kubernetes YAML

```bash
# Scan Kubernetes manifests
checkov -d ./k8s-manifests --framework kubernetes

# Scan Helm chart
checkov -d ./helm-chart --framework helm

# Scan with Helm values override
checkov -f deployment.yaml --framework kubernetes
```

### Trivy: Kubernetes YAML

```bash
# Scan Kubernetes manifests
trivy config ./k8s-manifests

# Scan Helm chart
trivy config ./helm-chart --scanners misconfig

# Scan Helm chart with values file
trivy config ./helm-chart --helm-values values.yaml
```

### Scanning a Deployment with Privileged Container

Given a Kubernetes deployment that runs a privileged container:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vulnerable-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vulnerable
  template:
    spec:
      containers:
        - name: app
          image: myapp:latest
          securityContext:
            privileged: true
            runAsUser: 0
          resources:
            requests:
              memory: "64Mi"
              cpu: "250m"
            limits:
              memory: "128Mi"
              cpu: "500m"
```

Checkov reports:
- `CKV_K8S_25`: Minimize the admission of privileged containers — **FAILED**
- `CKV_K8S_38`: Ensure that Service Account Tokens are only mounted where necessary — **FAILED**

Trivy reports:
- `KSV001`: Privileged container detected — **HIGH**
- `KSV009`: Container running as root — **MEDIUM**

## CI/CD Pipeline Integration

### GitHub Actions

**Checkov:**

```yaml
name: IaC Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  checkov:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Checkov
        run: pip install checkov

      - name: Run Checkov scan
        run: |
          checkov -d ./terraform \
            --output sarif \
            --output-file-path results.sarif \
            --compact

      - name: Upload SARIF to GitHub
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: results.sarif
```

**Trivy:**

```yaml
name: IaC Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy config scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: config
          scan-ref: ./terraform
          format: sarif
          output: trivy-results.sarif
          severity: HIGH,CRITICAL
          exit-code: "1"

      - name: Upload SARIF to GitHub
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif
```

### GitLab CI

```yaml
iac-scan:
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy config --exit-code 1 --severity HIGH,CRITICAL ./terraform
  artifacts:
    reports:
      codequality: trivy-results.json
  rules:
 [jenkins](https://www.jenkins.io/)anges:
        - "terraform/**/*.tf"
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('IaC Security Scan') {
            steps {
                script {
                    // Run Trivy config scan
                    sh 'trivy config --format json --output trivy-results.json ./terraform'

                    // Parse results and fail on HIGH/CRITICAL
                    def result = readFile('trivy-results.json')
                    def parsed = readJSON text: result
                    def highCount = parsed.Results?.count { it.Severity in ['HIGH', 'CRITICAL'] } ?: 0

                    if (highCount > 0) {
                        error "Found ${highCount} HIGH/CRITICAL IaC misconfigurations"
                    }
                }
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'trivy-results.json', fingerprint: true
        }
    }
}
```

## Choosing the Right Scanner

The choice depends on your team's needs and existing toolchain:

**Choose Checkov if:**
- You need the widest IaC format support (Terraform, CloudFormation, ARM, Bicep, Serverless, OpenAPI, Dockerfile, Kubernetes)
- Your team prefers Python for custom policy development
- You want a mature, dedicated IaC scanning tool with 900+ built-in policies
- You need fine-grained policy controls with soft/hard fail modes

**Choose Trivy (with tfsec engine) if:**
- You want a single scanner for containers, IaC, Kubernetes, and SBOM
- Your team already uses Trivy for container image scanning
- You prefer Go-based tools for faster execution
- You need Rego-based custom policies (compatible with OPA/Gatekeeper)
- You want active development — tfsec's engine is maintained within Trivy

**Note:** Standalone tfsec is in maintenance mode. For new deployments, use Trivy's `trivy config` command, which includes the full tfsec scanning engine plus additional capabilities.

Both tools run entirely locally, require no cloud connectivity, and integrate seamlessly into self-hosted CI/CD pipelines. For teams also managing container security, Trivy offers the most comprehensive single-tool approach — see our [SBOM and dependency tracking guide](../self-hosted-sbom-dependency-tracking-dependency-track-syft-cyclonedx-guide-2026/) for a deeper look at Trivy's software bill of materials capabilities.

## FAQ

### Can Checkov and Trivy scan Terraform Plan files?

Yes. Both tools accept Terraform Plan JSON output. Run `terraform plan -out=tfplan && terraform show -json tfplan > tfplan.json`, then pass the JSON file to either `checkov -f tfplan.json` or `trivy config tfplan.json`. This lets you catch misconfigurations before applying any changes to your infrastructure.

### Is tfsec still maintained as a standalone project?

No. tfsec was merged into Trivy in 2023 and the standalone repository is in maintenance mode. The tfsec scanning engine is fully integrated into `trivy config`, so all existing tfsec checks continue to work. New development happens within the Trivy project.

### Which tool has better Kubernetes scanning coverage?

Trivy generally provides more comprehensive Kubernetes scanning because it covers not just YAML manifests but also Helm charts, Kustomize overlays, and live cluster resources. Checkov has strong Kubernetes policy coverage with 100+ dedicated checks, but Trivy's integration with the tfsec engine and its own native Kubernetes policies gives it a broader total.

### Can I suppress false positives in these scanners?

Yes. Checkov supports inline suppression comments in Terraform files (`# checkov:skip=CKV_AWS_20:reason`), and both tools support ignore files. Checkov uses `.checkov.yaml` or CLI flags, while Trivy uses `.trivyignore` (compatible with tfsec's `.tfsecignore`). Suppressions should always include a justification comment for auditability.

### Do these scanners work in air-gapped environments?

Checkov requires Python dependencies to be installed, which may need offline package mirroring. Trivy downloads a vulnerability database on first run but can operate in offline mode with `trivy config --offline-scan` for IaC scanning specifically — no database download is needed for configuration checks. Both tools can run fully disconnected once installed.

### How do I write custom security policies?

Checkov supports Python and YAML policy definitions. You create a Python class extending `BaseResourceCheck` or write a YAML rule with Rego-like conditions. Trivy uses Rego exclusively — write `.rego` files in a policy directory and pass them with `--policy` or place them in `.trivy/policy/`. Rego policies are portable between Trivy, OPA, and Gatekeeper.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Checkov vs tfsec vs Trivy: Self-Hosted IaC Security Scanning 2026",
  "description": "Compare Checkov, tfsec, and Trivy for self-hosted infrastructure-as-code security scanning. Learn which open-source tool best fits your Terraform, Kubernetes, and cloud compliance needs.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
