---
title: "Self-Hosted Container SBOM Generators — Syft vs Trivy vs spdx-sbom-generator"
date: "2026-05-19"
tags: ["containers", "security", "sbom", "devops", "self-hosted", "compliance"]
draft: false
---

A Software Bill of Materials (SBOM) is a structured inventory of every component, library, and dependency included in a container image. Think of it as an ingredients label for software — listing every package version, license, and supplier so you can answer critical questions: Does this image contain Log4j? Are any components under licenses that violate our compliance policy? Which dependencies need urgent patching?

Regulatory frameworks increasingly require SBOMs. US Executive Order 14028 mandates SBOMs for all software sold to the federal government. The EU Cyber Resilience Act requires SBOMs for products placed on the European market. Organizations that build, deploy, or consume container images need reliable tools to generate and maintain accurate SBOMs.

This guide compares three leading open-source SBOM generators for container images: **Syft** (by Anchore), **Trivy** (by Aqua Security), and **spdx-sbom-generator**. Each produces SBOMs in different formats, with varying depth of analysis and integration capabilities.

## Quick Comparison

| Feature | Syft | Trivy | spdx-sbom-generator |
|---------|------|-------|---------------------|
| GitHub Stars | 8,955 | 35,046 | 426 |
| Primary Format | CycloneDX, SPDX | CycloneDX, SPDX, GitHub | SPDX only |
| Container Image Support | Yes | Yes | No (filesystem only) |
| OS Package Detection | Yes | Yes | Limited |
| Language Package Detection | 20+ ecosystems | 15+ ecosystems | Go, npm, pip, Maven |
| Binary Analysis | Yes | Yes | No |
| Vulnerability Scanning | Via Grype | Built-in | No |
| Docker Registry Pull | Yes | Yes | No |
| CI/CD Integration | GitHub Action, CLI | GitHub Action, CLI | GitHub Action |
| License Detection | Yes | Yes | Yes |
| Output Formats | JSON, Table, SPDX, CycloneDX | JSON, Table, SPDX, CycloneDX | SPDX JSON, YAML |
| Language | Go | Go | Go |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |

## Syft — Comprehensive Container SBOM Generator

**Syft** is the most mature and feature-rich SBOM generator in the open-source ecosystem. Developed by Anchore, it supports over 20 package ecosystems and produces SBOMs in both SPDX and CycloneDX formats.

### Installation

```bash
# Linux/macOS
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Homebrew
brew install syft

# Docker
docker run --rm anchore/syft:latest --version
```

### Generating SBOMs from Container Images

```bash
# Generate SBOM from a Docker image
syft nginx:latest -o json > nginx-sbom.json

# Output in SPDX format
syft nginx:latest -o spdx-json > nginx-spdx.json

# Output in CycloneDX format
syft nginx:latest -o cyclonedx-json > nginx-cyclonedx.json

# Scan a specific registry
syft registry:docker.io/library/nginx:1.25 -o spdx-json

# Compare two SBOMs
syft nginx:1.24 -o json > old.json
syft nginx:1.25 -o json > new.json
syft compare old.json new.json
```

### Docker Compose Integration

```yaml
version: "3.8"
services:
  syft-scanner:
    image: anchore/syft:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./sbom-output:/output:rw
    command: ["docker:myapp:latest", "-o", "spdx-json=/output/myapp-sbom.spdx.json"]
    restart: "no"
```

### Pipeline Integration

```bash
# Generate SBOM and pipe to Grype for vulnerability scanning
syft myapp:latest -o json | grype --input syft-json

# Generate SBOM in CI with specific output formats
syft . -o spdx-json=sbom.spdx.json -o cyclonedx-json=sbom.cdx.json
```

### Key Features

- **20+ package ecosystems**: Supports Alpine APK, Debian dpkg, Red Hat RPM, Python pip, Java JAR/Gradle, JavaScript npm, Go modules, Rust Cargo, Ruby gems, PHP Composer, .NET NuGet, and more
- **Binary analysis**: Detects packages installed from compiled binaries, not just package manager metadata
- **Container image scanning**: Direct registry pulling with support for Docker, OCI, and containerd image formats
- **SBOM comparison**: Built-in diff tool for comparing SBOMs across image versions
- **Grype integration**: Seamless handoff to Anchore's vulnerability scanner

## Trivy — All-in-One Security Scanner with SBOM

**Trivy** is primarily a vulnerability scanner but includes robust SBOM generation capabilities. Its strength lies in combining SBOM creation with vulnerability detection in a single tool.

### Installation

```bash
# Linux
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Homebrew
brew install trivy

# Docker
docker run --rm aquasecurity/trivy --version
```

### Generating SBOMs

```bash
# Generate SBOM from a container image
trivy image --format spdx-json --output sbom.spdx.json nginx:latest

# Generate CycloneDX SBOM
trivy image --format cyclonedx --output sbom.cdx.json nginx:latest

# Scan filesystem for SBOM
trivy fs --format spdx-json --output sbom.spdx.json /path/to/project

# Generate SBOM with vulnerability data
trivy image --format cyclonedx --security-checks vuln nginx:latest > sbom-with-vulns.cdx.json

# SBOM from running container
trivy image --format spdx-json myapp:1.0 > app-sbom.spdx.json
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  trivy-sbom:
    image: aquasecurity/trivy:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./sbom-output:/output:rw
    command:
      - "image"
      - "--format"
      - "spdx-json"
      - "--output"
      - "/output/sbom.spdx.json"
      - "myapp:latest"
    restart: "no"
```

### Key Features

- **Combined SBOM + vulnerability scanning**: Generate SBOMs and immediately identify known CVEs in a single pass
- **15+ ecosystems**: Covers major operating systems and programming language package managers
- **Misconfiguration detection**: Scans Dockerfiles, Kubernetes manifests, and Terraform configs for security issues
- **Secret scanning**: Detects hardcoded credentials, API keys, and tokens in container layers
- **SBOM enrichment**: Attach vulnerability data directly to SBOM entries for immediate risk assessment

## spdx-sbom-generator — Focused SPDX SBOM Tool

**spdx-sbom-generator** is a specialized tool focused exclusively on generating SPDX-format SBOMs. It is simpler than Syft or Trivy but produces standards-compliant output suitable for compliance requirements.

### Installation

```bash
# Go installation
go install github.com/opensbom-generator/spdx-sbom-generator@latest

# Download binary
curl -L https://github.com/opensbom-generator/spdx-sbom-generator/releases/latest/download/spdx-sbom-generator-linux-amd64.tar.gz | tar -xz
sudo mv spdx-sbom-generator /usr/local/bin/
```

### Usage

```bash
# Generate SPDX SBOM from source directory
spdx-sbom-generator --path /path/to/project --output sbom.spdx.json

# Generate in YAML format
spdx-sbom-generator --path . --format yaml --output sbom.spdx.yaml

# Specify SPDX version
spdx-sbom-generator --path . --spdx-version 2.3 --output sbom.spdx.json
```

### Key Features

- **SPDX-only focus**: Produces strictly standards-compliant SPDX 2.2 and 2.3 SBOMs
- **Lightweight**: Single binary with no external dependencies
- **CI/CD friendly**: Simple CLI interface ideal for automated pipelines
- **Multiple language support**: Go modules, npm, pip, Maven, and more
- **GitHub Action**: Official GitHub Action for automated SBOM generation in CI

## Why Self-Host Your SBOM Generation Pipeline?

Supply chain security starts with visibility into what your software contains. When you rely on third-party SBOM services, you expose your container image contents, dependency lists, and potentially proprietary build information to external systems. Self-hosted SBOM generation keeps this sensitive data within your infrastructure.

Regulatory compliance increasingly demands accurate, up-to-date SBOMs. Government contracts, enterprise procurement requirements, and industry regulations all specify SBOM formats and delivery timelines. Running your own SBOM pipeline means you control the generation schedule, output format, and data retention — without depending on external service availability or rate limits.

Integration with existing security workflows is seamless when SBOM generation runs locally. Your SBOM data feeds directly into internal vulnerability management systems, license compliance tools, and procurement databases. There are no API calls to external services, no data transfer costs, and no latency in the scanning pipeline.

Cost efficiency matters at scale. Commercial SBOM services often charge per-scan or per-image, with enterprise pricing reaching thousands of dollars monthly for high-volume CI/CD pipelines. Open-source tools like Syft, Trivy, and spdx-sbom-generator are free, run on your existing CI infrastructure, and scale without additional licensing costs.

For comprehensive container security, SBOM generation is one layer among many. Our [container image scanning guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/) covers vulnerability detection, our [container security hardening article](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/) addresses runtime security, and our [container sandboxing comparison](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/) explores isolation strategies for untrusted workloads.

## Choosing the Right SBOM Generator

**Choose Syft if:** You need the broadest package ecosystem coverage, SBOM comparison capabilities, or plan to integrate with Grype for vulnerability scanning. Syft is the most feature-complete standalone SBOM generator available.

**Choose Trivy if:** You want SBOM generation combined with vulnerability scanning, misconfiguration detection, and secret scanning in a single tool. Trivy is the all-in-one security scanner that happens to produce excellent SBOMs.

**Choose spdx-sbom-generator if:** Your compliance requirement specifies SPDX format exclusively, you need the simplest possible CLI tool, or you are generating SBOMs for source code repositories rather than container images.

## FAQ

### What is the difference between SPDX and CycloneDX SBOM formats?

SPDX (Software Package Data Exchange) is an ISO-standard format maintained by the Linux Foundation, widely used in government and enterprise compliance. CycloneDX, maintained by OWASP, is designed specifically for application security use cases and supports richer vulnerability and dependency graph data. Both are widely accepted — check your compliance requirements for format specifications.

### Can these tools generate SBOMs for images in private registries?

Yes. Syft and Trivy support authentication to private Docker registries via Docker credential helpers or explicit credentials. Configure `docker login` before running the tools, or pass credentials via environment variables (`TRIVY_USERNAME`/`TRIVY_PASSWORD` for Trivy).

### How often should I regenerate SBOMs?

Regenerate SBOMs every time you build a new container image, and periodically (weekly or monthly) for running production images to catch newly disclosed vulnerabilities. Automated CI/CD pipelines should generate SBOMs as a standard build artifact alongside the image itself.

### Do SBOMs include transitive dependencies?

Yes, all three tools recursively resolve and include transitive (indirect) dependencies. Syft provides the most detailed dependency graphs, showing parent-child relationships between packages. Trivy includes transitive dependencies in its SBOM output with vulnerability data attached.

### Can I compare SBOMs across image versions to see what changed?

Syft has a built-in `syft compare` command that diffs two SBOMs and reports added, removed, and modified packages. Trivy does not have a native comparison feature, but you can use external tools like `diff` or SBOM-specific comparison tools on the JSON output.

### Are SBOMs required by law?

US Executive Order 14028 requires SBOMs for software sold to the federal government. The EU Cyber Resilience Act (CRA) requires SBOMs for products with digital elements placed on the EU market. Many enterprise procurement processes now require SBOMs as a standard deliverable, regardless of government mandates.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container SBOM Generators — Syft vs Trivy vs spdx-sbom-generator",
  "description": "Compare three open-source SBOM generators for container images: Syft, Trivy, and spdx-sbom-generator. Learn which tool is best for your compliance and security needs.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
