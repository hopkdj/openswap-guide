---
title: "Self-Hosted IaC Security Scanners: KICS vs Terrascan vs ThreatMapper"
date: "2026-05-12"
tags: ["security", "iac", "terraform", "compliance", "devops", "self-hosted"]
draft: false
---

Infrastructure as Code (IaC) has become the standard for provisioning cloud and on-premises infrastructure. Tools like Terraform, CloudFormation, Kubernetes manifests, and Ansible playbooks define your entire infrastructure in version-controlled text files. But with this power comes a critical risk: a misconfigured resource in your IaC can expose your entire environment to security breaches.

IaC security scanners analyze your infrastructure definitions before they are applied, catching misconfigurations, compliance violations, and security vulnerabilities at the earliest possible stage -- while the code is still in your repository. This "shift-left" approach is far cheaper and safer than discovering security issues in production.

Three open-source tools lead this space: **KICS** (Keeping Infrastructure as Code Secure), **Terrascan**, and **ThreatMapper**. Each takes a different approach to IaC security, from Terraform-specific scanning to full cloud-native application protection. This guide compares them to help you choose the right scanner for your pipeline.

## Understanding IaC Security Scanning

IaC security scanners parse your infrastructure definition files and compare them against a database of known misconfiguration patterns, compliance frameworks, and security best practices. Common findings include:

- S3 buckets with public read access
- Security groups allowing unrestricted inbound traffic (0.0.0.0/0)
- Unencrypted storage volumes or databases
- Missing logging and monitoring configurations
- IAM policies granting excessive permissions
- Kubernetes containers running as root

Scanners can run locally during development, as pre-commit hooks, in CI/CD pipelines, or as continuous monitoring agents. The best results come from running them at multiple stages -- catch issues early during development and enforce compliance gates before deployment.

## Project Comparison at a Glance

| Feature | KICS | Terrascan | ThreatMapper |
|---------|------|-----------|--------------|
| GitHub Stars | 2,600+ | 5,200+ | 5,200+ |
| Last Updated | Active (Apr 2026) | Active (Nov 2025) | Active (Mar 2026) |
| IaC Formats | Terraform, K8s, CFN, Ansible, Dockerfile, ARM | Terraform, K8s, Helm, CFN | Terraform, K8s, Docker, Helm |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Query Language | Rego (OPA) | Rego (OPA) | Proprietary engine |
| Compliance Frameworks | CIS, NIST, PCI-DSS, HIPAA, SOC2 | CIS, NIST, PCI-DSS, GDPR | CIS, NIST, SOC2 |
| CI/CD Integration | GitHub Actions, GitLab, Jenkins | GitHub Actions, GitLab, Jenkins | GitHub Actions, GitLab CI |
| Dashboard UI | No (CLI only) | No (CLI only) | Yes (built-in) |
| Runtime Scanning | No | No | Yes (containers, hosts) |
| SBOM Generation | No | No | Yes |
| Docker Compose | Yes | No (CLI) | Yes |

KICS and Terrascan are focused purely on static analysis of IaC files. ThreatMapper goes further, providing a complete Cloud-Native Application Protection Platform (CNAPP) that includes runtime scanning, software composition analysis (SCA), and a management dashboard.

## Installation and Deployment

### KICS

KICS provides a simple Docker-based installation with a ready-to-use docker-compose.yml:

```yaml
version: "3"
services:
  kics:
    platform: linux
    image: checkmarx/kics:latest
    container_name: kics-scanner
    volumes:
      - ./infrastructure:/path/
    command: scan -p /path/ -v --output-path /path/results
```

CLI installation:

```bash
# Homebrew (macOS/Linux)
brew install kics

# Or download binary from GitHub releases
curl -sL https://github.com/Checkmarx/kics/releases/latest/download/kics_linux_amd64.tar.gz | tar xz
sudo mv kics /usr/local/bin/
```

Running a scan:

```bash
kics scan -p ./terraform/ --output-path ./results/ -v
```

### Terrascan

```bash
# Homebrew (macOS/Linux)
brew install terrascan

# Or download binary
curl -sL https://github.com/tenable/terrascan/releases/latest/download/terrascan_$(uname -s)_$(uname -m).tar.gz | tar xz
sudo mv terrascan /usr/local/bin/

# Initialize policy repository
terrascan init
```

Running a scan:

```bash
terrascan scan -i terraform -d ./infrastructure/
```

### ThreatMapper

ThreatMapper provides a full management platform with Docker Compose:

```yaml
version: "3.8"
services:
  threatmapper:
    image: deepfenceio/deepfence-ce:latest
    container_name: threatmapper
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - threatmapper-data:/var/lib/deepfence
    environment:
      - MGMT_CONSOLE_PORT=443
      - MGMT_CONSOLE_DATA_PATH=/var/lib/deepfence
    deploy:
      resources:
        limits:
          memory: 4G

volumes:
  threatmapper-data:
```

After starting, access the web UI at `https://<your-server>` to configure scanning policies, view results, and manage agents.

## Configuration and Policy Customization

### KICS

KICS uses Rego (the OPA policy language) for its queries, making it easy to customize or add new checks:

```bash
# Run with specific severity filter
kics scan -p ./terraform/ --fail-on high,critical

# Run with custom queries
kics scan -p ./terraform/ --queries-path ./custom-queries/

# Exclude specific checks
kics scan -p ./terraform/ --exclude-results <result-id>
```

Sample KICS output:

```
Files scanned: 12
Parsed files: 12
Queries loaded: 756
Queries failed to execute: 0

Results:
  HIGH: 3
  MEDIUM: 7
  LOW: 2
  INFO: 5
  TRACE: 1
```

### Terrascan

Terrascan also uses Rego for policies and supports custom policy packs:

```bash
# Run with specific policy type
terrascan scan -i terraform -d ./infrastructure/ -t aws

# Run with custom policies
terrascan scan -i terraform -d ./infrastructure/ -p ./custom-policies/

# Output in different formats
terrascan scan -i terraform -d ./infrastructure/ -o json
terrascan scan -i terraform -d ./infrastructure/ -o junit-xml
```

### ThreatMapper

ThreatMapper provides a web-based policy management interface:

1. Navigate to Settings > Compliance in the dashboard
2. Select compliance frameworks (CIS, NIST, PCI-DSS)
3. Configure scanning schedules and notification policies
4. View scan results with risk scoring and remediation guidance

ThreatMapper also supports API-driven scanning:

```bash
# Scan a directory via the API
curl -X POST https://threatmapper/api/v1/scan   -H "Authorization: Bearer <token>"   -d '{"path": "/path/to/terraform", "type": "terraform"}'
```

## CI/CD Pipeline Integration

### GitHub Actions with KICS

```yaml
name: IaC Security Scan
on: [push, pull_request]
jobs:
  kics-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run KICS scan
        uses: checkmarx/kics-github-action@v1.7.0
        with:
          path: ./infrastructure/
          fail_on: high,critical
          output_path: ./kics-results/
          output_formats: json,sarif
```

### GitHub Actions with Terrascan

```yaml
name: IaC Security Scan
on: [push, pull_request]
jobs:
  terrascan-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Terrascan
        uses: accurics/terrascan-action@main
        with:
          iac_type: terraform
          iac_dir: ./infrastructure/
          exit_code: 1
```

### GitHub Actions with ThreatMapper

```yaml
name: ThreatMapper Scan
on: [push, pull_request]
jobs:
  threatmapper-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ThreatMapper
        run: |
          curl -sL https://github.com/deepfence/ThreatMapper/releases/latest/download/linux_amd64_deepfence-ce -o deepfence-ce
          chmod +x deepfence-ce
          ./deepfence-ce scan -dir ./infrastructure/
```

## When to Choose Each

### Choose KICS if:
- You need the broadest IaC format support (7+ formats)
- You want the most active open-source project in this space
- You need detailed compliance reporting for audits
- You prefer Rego-based policies that are easy to customize
- You want a lightweight CLI-only tool for CI/CD gates

### Choose Terrascan if:
- You are primarily a Terraform shop
- You need SARIF output for GitHub security tab integration
- You want Tenable backing and commercial support options
- You need custom policy packs with Rego
- You are already using other Tenable security products

### Choose ThreatMapper if:
- You need a complete CNAPP platform, not just IaC scanning
- You want runtime container and host scanning in addition to IaC
- You need a web dashboard for centralized security management
- You want SBOM generation and vulnerability correlation
- You are managing a large fleet of cloud-native workloads

## Why Scan IaC Before Deployment?

The cost of fixing a security issue increases exponentially the later it is discovered. A misconfiguration caught during code review costs minutes to fix. The same issue discovered in production could mean a data breach, compliance violation, or service outage.

IaC security scanning is particularly critical because infrastructure definitions are applied programmatically. A single Terraform apply can provision hundreds of resources across multiple accounts and regions. If those resources contain security misconfigurations, the blast radius is enormous.

For organizations pursuing DevSecOps, IaC scanners are the bridge between development speed and security compliance. They enable developers to catch security issues in their IDE or pull request, before the code ever reaches a staging environment.

If you are already scanning container images, check our [container image scanning guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide/) for complementary tools. For Kubernetes-specific policy enforcement, our [Kubernetes policy enforcement guide](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement/) covers runtime admission control. And for broader container security hardening, our [container security hardening guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/) provides defense-in-depth strategies.

## FAQ

### What is the difference between IaC scanning and container image scanning?

IaC scanning analyzes your infrastructure definition files (Terraform, CloudFormation, Kubernetes YAML) for misconfigurations before resources are provisioned. Container image scanning analyzes built container images for known vulnerabilities in their software packages (CVEs). Both are essential: IaC scanning catches configuration errors, image scanning catches vulnerable dependencies. They are complementary, not interchangeable.

### Can these scanners scan Kubernetes YAML files?

Yes. KICS supports Kubernetes manifests natively. Terrascan supports Kubernetes YAML and Helm charts. ThreatMapper supports Kubernetes manifests, Helm charts, and Kustomize overlays. All three can detect issues like containers running as root, missing resource limits, privileged containers, and missing security contexts.

### How do I handle false positives in IaC scans?

All three scanners allow you to exclude specific rules or results. In KICS, use `--exclude-results` with result IDs. In Terrascan, use skip comments in your Terraform code (`#ts:skip=RuleID reason`). In ThreatMapper, configure exclusions through the web dashboard. Document each exclusion with a justification for audit purposes.

### Do these tools integrate with Terraform Cloud or Enterprise?

KICS and Terrascan can be integrated as pre-plan hooks in Terraform Cloud/Enterprise using the run task API. ThreatMapper provides API endpoints that can be called from Terraform Cloud run tasks. For self-hosted alternatives to Terraform Cloud, our [Terraform PR automation guide](../2026-04-22-atlantis-vs-digger-vs-terrateam-self-hosted-terraform-pr-automation-2026/) covers open-source options.

### Which compliance frameworks are supported?

KICS supports the broadest set: CIS Benchmark, NIST 800-53, PCI-DSS, HIPAA, SOC2, and GDPR. Terrascan supports CIS, NIST, PCI-DSS, and GDPR. ThreatMapper supports CIS, NIST, and SOC2, with the ability to create custom compliance frameworks through the dashboard.

### How often should I update the policy database?

Update policies at least weekly, or better yet, integrate policy updates into your CI/CD pipeline. KICS and Terrascan download policy updates at initialization time. ThreatMapper updates policies automatically from its central management server. Stale policies may miss newly discovered misconfiguration patterns.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IaC Security Scanners: KICS vs Terrascan vs ThreatMapper",
  "description": "Compare KICS, Terrascan, and ThreatMapper for self-hosted IaC security scanning. Docker configs, CI/CD integration, and compliance frameworks covered.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
