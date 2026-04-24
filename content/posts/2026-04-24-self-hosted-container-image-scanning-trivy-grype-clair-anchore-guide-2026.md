---
title: "Self-Hosted Container Image Scanning: Trivy vs Grype vs Clair Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "security", "containers", "devops"]
draft: false
description: "Complete guide to self-hosted container image scanning in 2026. Compare Trivy, Grype, and Clair for Docker image vulnerability detection with Docker Compose setups, CI/CD integration, and registry pipeline configuration."
---

## Why Self-Host Container Image Scanning?

Every container image you deploy carries inherited risk. A single base image can pull in hundreds of transitive dependencies, each with its own vulnerability surface. When you scan container images using commercial SaaS platforms, you expose your entire software inventory — package names, versions, base images, and deployment targets — to a third-party cloud service. Self-hosted container image scanning eliminates this data leakage while delivering zero licensing costs and unlimited scan throughput.

For teams running CI/CD pipelines, container registries, or Kubernetes clusters, image scanning is not a nice-to-have — it is a fundamental security control. The right scanner catches critical CVEs before they reach production, blocks vulnerable images at the registry gate, and generates SBOMs for compliance audits. This guide compares the three leading open-source container image scanners and provides production-ready Docker Compose configurations for each.

## Quick Comparison: Trivy vs Grype vs Clair

| Feature | Trivy (Aqua Security) | Grype (Anchore) | Clair (Quay) |
|---------|----------------------|-----------------|--------------|
| **Developer** | Aqua Security | Anchore | Red Hat / Quay |
| **Language** | Go | Go | Go |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 34,683 | 12,076 | 10,969 |
| **Last Updated** | 2026-04-24 | 2026-04-22 | 2026-04-23 |
| **Primary Focus** | All-in-one security scanner | Container image scanning | Registry-integrated scanning |
| **Scan Targets** | Containers, filesystems, IaC, git repos, Kubernetes | Container images, filesystems, SBOMs | Container images (OCI/Docker) |
| **Vulnerability Sources** | OS package DBs, GitHub Advisories, Go, npm, Python, Ruby, PHP, Rust, .NET | GitHub Advisories, OSV, distro databases | CVE databases, Red Hat OVAL, Ubuntu USN, Debian DSA |
| **Misconfiguration Scanning** | ✅ Dockerfile, Kubernetes, Terraform, CloudFormation, Helm | ❌ | ❌ |
| **Secret Detection** | ✅ Built-in | ❌ | ❌ |
| **SBOM Generation** | ✅ CycloneDX, SPDX | ✅ (via Syft) | ❌ |
| **SBOM Scanning** | ✅ | ✅ | ❌ |
| **CI/CD Integration** | Native CLI, GitHub Actions, CI plugins | Native CLI, GitHub Actions, Jenkins plugin | REST API, webhook notifications |
| **Registry Integration** | Manual (CLI-based) | Manual (CLI-based) | ✅ Native (push-time scanning) |
| **Web Interface** | Trivy Operator Dashboard (Kubernetes) | None (CLI only) | Quay UI integration |
| **Resource Requirements** | Low (single binary) | Low (single binary) | Medium (PostgreSQL backend) |
| **Best For** | All-in-one scanning pipeline | CI/CD image scanning | Registry-native scanning |

## Trivy: The All-in-One Security Scanner

[Trivy](https://github.com/aquasecurity/trivy) is the most popular open-source container image scanner, with over 34,000 GitHub stars and daily updates from Aqua Security. Its distinguishing feature is breadth: Trivy scans containers, filesystems, Infrastructure as Code, Git repositories, Kubernetes clusters, and cloud configurations — all from a single binary.

Trivy's vulnerability database covers operating system packages (Alpine, RHEL, Debian, Ubuntu, Amazon Linux, SUSE, Oracle, Photon OS), language-specific ecosystems (Go, npm, pip, Cargo, Composer, NuGet, Maven, pipenv, poetry), and cloud platforms. It also detects misconfigurations in Dockerfiles, Kubernetes manifests, Terraform, CloudFormation, Helm charts, and Ansible playbooks using built-in policy checks.

### Key Trivy Features

- **Multi-format scanning**: OCI images, container registries, local filesystems, Git repos, Kubernetes clusters
- **Misconfiguration detection**: Built-in Rego policies for Docker, Kubernetes, Terraform, CloudFormation
- **Secret scanning**: Detects hardcoded secrets in Dockerfiles, configs, and source code
- **SBOM generation**: Produces CycloneDX and SPDX software bills of materials
- **Multiple output formats**: JSON, SARIF, CycloneDX, SPDX, table, template
- **Offline mode**: Download the vulnerability database once and scan air-gapped systems

### Docker Compose: Trivy Scanner

Trivy runs as a single binary with no database dependency, making it the simplest scanner to deploy. The Docker Compose setup below runs Trivy in server mode, enabling it to accept scan requests via a REST API:

```yaml
version: "3.8"
services:
  trivy:
    image: aquasec/trivy:latest
    container_name: trivy-scanner
    restart: unless-stopped
    ports:
      - "4954:4954"
    command: server --listen 0.0.0.0:4954 --cache-dir /tmp/trivy-db
    volumes:
      - trivy-cache:/tmp/trivy-db
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - TRIVY_DB_REPOSITORY=ghcr.io/aquasecurity/trivy-db
      - TRIVY_JAVA_DB_REPOSITORY=ghcr.io/aquasecurity/trivy-java-db
      - TRIVY_IGNORE_UNFIXED=true
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # One-shot scanner for CI/CD pipelines
  trivy-scan:
    image: aquasec/trivy:latest
    container_name: trivy-ci-scan
    profiles: ["scan"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: image --severity HIGH,CRITICAL --format table alpine:3.19
    depends_on:
      - trivy

volumes:
  trivy-cache:
```

To scan a specific image:

```bash
# Scan a Docker image (single run)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro \
  aquasec/trivy:latest image --severity HIGH,CRITICAL --format table nginx:latest

# Scan via server API
curl -s http://localhost:4954/scan \
  -d '{"artifact": "nginx:latest"}' \
  | jq '.Results[] | select(.Vulnerabilities | length > 0)'

# Scan with misconfiguration detection
docker run --rm -v $(pwd):/project aquasec/trivy:latest config \
  --severity HIGH,CRITICAL /project/

# Scan a filesystem for secrets
docker run --rm -v $(pwd):/project aquasec/trivy:latest fs \
  --scanners secret /project/
```

## Grype: Focused Container Image Scanning

[Grype](https://github.com/anchore/grype) by Anchore is a purpose-built vulnerability scanner for container images and filesystems. Unlike Trivy's all-in-one approach, Grype focuses on doing one thing exceptionally well: finding known vulnerabilities in container packages and producing actionable results.

Grype's matching engine uses multiple strategies — direct package matching, CPE-based matching, and indirect dependency resolution — to maximize detection coverage while minimizing false positives. It integrates seamlessly with Syft (also by Anchore) for SBOM generation, creating a complete container scanning workflow.

### Key Grype Features

- **Deep package matching**: Direct, CPE-based, and source indirection matching strategies
- **SBOM scanning**: Import SBOMs from Syft, Scanoss, or CycloneDX and scan them for vulnerabilities
- **CI/CD optimized**: Fast, single-binary execution designed for pipeline integration
- **Policy support**: Fail builds based on severity thresholds with `--fail-on` flag
- **Multiple output formats**: Table, JSON, CycloneDX, SPDX, SARIF
- **Database freshness**: Daily vulnerability database updates from multiple sources

### Docker Compose: Grype Scanner

Like Trivy, Grype runs as a single binary. The Docker Compose setup uses Syft alongside Grype for the full scan-and-SBOM workflow:

```yaml
version: "3.8"
services:
  grype:
    image: anchore/grype:latest
    container_name: grype-scanner
    restart: unless-stopped
    entrypoint: ["grype"]
    command: --version
    volumes:
      - grype-cache:/root/.cache/grype
    environment:
      - GRYPE_DB_AUTO_UPDATE=true
      - GRYPE_DB_CACHE_DIR=/root/.cache/grype
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  syft:
    image: anchore/syft:latest
    container_name: syft-sbom
    profiles: ["sbom"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: nginx:latest -o cyclonedx-json > sbom.json
    depends_on:
      - grype

volumes:
  grype-cache:
```

Practical Grype scanning commands:

```bash
# Scan a Docker image with severity filter
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro \
  anchore/grype:latest nginx:latest --severity high,critical

# Scan and fail on critical vulnerabilities (CI/CD gate)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro \
  anchore/grype:latest myapp:latest --fail-on critical

# Generate SBOM with Syft, then scan with Grype
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro \
  anchore/syft:latest nginx:latest -o json | \
  docker run --rm -i anchore/grype:latest sbom:json -

# Scan a local filesystem
docker run --rm -v $(pwd):/project anchore/grype:latest dir:/project
```

## Clair: Registry-Native Image Scanning

[Clair](https://github.com/quay/clair) is Red Hat's open-source container image vulnerability scanner, designed for deep integration with container registries — particularly [Project Quay](https://github.com/quay/quay). Unlike Trivy and Grype, which are CLI tools you invoke per-scan, Clair runs as a persistent service that automatically scans images as they are pushed to a registry.

Clair uses a four-stage indexing pipeline: manifest retrieval, layer extraction, package detection, and vulnerability matching. It indexes all layers of a container image and stores the results in a PostgreSQL database, enabling historical vulnerability tracking and trend analysis. Clair notifies clients about new vulnerabilities via webhooks when its database is updated.

### Key Clair Features

- **Registry-native**: Automatically scans images on push — no manual CLI invocation needed
- **Incremental indexing**: Only scans new layers, caching results for unchanged layers
- **Vulnerability notifications**: Webhook-based alerts when new CVEs affect indexed images
- **Historical tracking**: PostgreSQL backend enables trend analysis and audit trails
- **API-driven**: REST API for programmatic scanning and result retrieval
- **Quay integration**: Native scanning within Project Quay's web interface

### Docker Compose: Clair Scanner

Clair requires a PostgreSQL backend and runs as a multi-service architecture. Here is a production-ready Docker Compose configuration:

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16-alpine
    container_name: clair-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: clair
      POSTGRES_PASSWORD: clair-password
      POSTGRES_DB: clair
    volumes:
      - clair-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U clair"]
      interval: 5s
      timeout: 3s
      retries: 5

  clair:
    image: quay/projectquay/clair:latest
    container_name: clair-scanner
    restart: unless-stopped
    ports:
      - "6060:6060"
    environment:
      - CLAIR_CONF=/etc/clair/config.yaml
      - CLAIR_MODE=combiner
    volumes:
      - ./clair-config.yaml:/etc/clair/config.yaml:ro
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6060/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  clair-indexer:
    image: quay/projectquay/clair:latest
    container_name: clair-indexer
    restart: unless-stopped
    environment:
      - CLAIR_CONF=/etc/clair/config.yaml
      - CLAIR_MODE=indexer
    volumes:
      - ./clair-config.yaml:/etc/clair/config.yaml:ro
    depends_on:
      postgres:
        condition: service_healthy

  clair-matcher:
    image: quay/projectquay/clair:latest
    container_name: clair-matcher
    restart: unless-stopped
    environment:
      - CLAIR_CONF=/etc/clair/config.yaml
      - CLAIR_MODE=matcher
    volumes:
      - ./clair-config.yaml:/etc/clair/config.yaml:ro
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  clair-pgdata:
```

Clair configuration file (`clair-config.yaml`):

```yaml
http_listen_addr: 0.0.0.0:6060
log_level: info
indexer:
  connstring: host=postgres port=5432 dbname=clair user=clair password=clair-password sslmode=disable
  scanlock_retry: 10
  layer_scan_concurrency: 5
matcher:
  connstring: host=postgres port=5432 dbname=clair user=clair password=clair-password sslmode=disable
  migrations: true
notifier:
  connstring: host=postgres port=5432 dbname=clair user=clair password=clair-password sslmode=disable
  migrations: true
  delivery_interval: 1m
  poll_interval: 5m
```

Indexing and scanning a container image via Clair's API:

```bash
# Index an image (send manifest reference)
curl -X POST http://localhost:6060/api/v1/index_state

# Get vulnerability report for a manifest
MANIFEST_HASH=$(curl -s -X POST http://localhost:6060/api/v1/index \
  -H "Content-Type: application/json" \
  -d '{"layers": [{"uri": "https://registry.example.com/v2/library/nginx/blobs/sha256:abc123"}]}' \
  | jq -r '.manifest.hash')

curl -s http://localhost:6060/api/v1/vulnerability_report/${MANIFEST_HASH} \
  | jq '.vulnerabilities[] | select(.severity == "Critical" or .severity == "High")'
```

## Architecture Comparison: How Each Scanner Works

Understanding the underlying architecture helps you choose the right tool for your deployment model.

| Architecture Aspect | Trivy | Grype | Clair |
|--------------------|-------|-------|-------|
| **Execution Model** | Single binary, CLI or server mode | Single binary, CLI mode | Multi-service (indexer, matcher, combiner) |
| **Database** | Embedded BoltDB (local) | Embedded BoltDB (local) | PostgreSQL (external, shared) |
| **DB Update Frequency** | On-demand (every 12h by default) | On-demand (daily) | Continuous (auto-fetch) |
| **Scanning Trigger** | Manual CLI or API call | Manual CLI call | Automatic on image push |
| **Layer Caching** | Local cache directory | Local cache directory | PostgreSQL-backed layer index |
| **Concurrent Scans** | Sequential (per process) | Sequential (per process) | Multiple indexer instances |
| **Persistence** | Stateless (except cache) | Stateless (except cache) | Full scan history in PostgreSQL |
| **Horizontal Scaling** | Run multiple instances | Run multiple instances | Built-in (separate indexer/matcher pods) |
| **Kubernetes Deployment** | Simple (single pod) | Simple (single pod) | Complex (multiple pods + PostgreSQL) |

**Trivy** is the easiest to deploy — a single container with optional server mode. It is ideal for CI/CD pipelines where you need quick, on-demand scans with minimal infrastructure.

**Grype** follows the same single-binary model but focuses exclusively on container and filesystem scanning. Its Syft integration makes it the best choice for teams that need SBOM generation alongside vulnerability detection.

**Clair** requires the most infrastructure (PostgreSQL, multiple services) but delivers the most powerful registry integration. If you run a container registry and want automatic scanning on every push, Clair is the natural choice.

## CI/CD Pipeline Integration

All three scanners integrate into CI/CD pipelines, but the integration patterns differ significantly.

### GitHub Actions: Trivy

```yaml
name: Container Security Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  trivy-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

### GitHub Actions: Grype

```yaml
name: Container Security Scan
on:
  push:
    branches: [main]

jobs:
  grype-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Grype vulnerability scanner
        uses: anchore/scan-action@v3
        with:
          image: "myapp:${{ github.sha }}"
          fail-build: true
          severity-cutoff: high
          output-format: sarif

      - name: Upload Grype scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'results.sarif'
```

### Jenkins Pipeline: Clair

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'docker build -t myapp:${BUILD_NUMBER} .'
                sh 'docker tag myapp:${BUILD_NUMBER} registry.example.com/myapp:${BUILD_NUMBER}'
            }
        }
        stage('Push to Registry') {
            steps {
                sh 'docker push registry.example.com/myapp:${BUILD_NUMBER}'
            }
        }
        stage('Clair Scan') {
            steps {
                script {
                    def manifestHash = sh(
                        script: "docker inspect --format='{{index .Id}}' myapp:${BUILD_NUMBER} | cut -d: -f2",
                        returnStdout: true
                    ).trim()
                    def report = sh(
                        script: "curl -s http://clair:6060/api/v1/vulnerability_report/${manifestHash}",
                        returnStdout: true
                    )
                    def criticalCount = readJSON text: report |
                        grep { it.severity == 'Critical' } | size()
                    if (criticalCount > 0) {
                        error "Found ${criticalCount} critical vulnerabilities"
                    }
                }
            }
        }
    }
}
```

## Choosing the Right Scanner

Your choice depends on three factors: deployment model, integration depth, and operational complexity.

| Decision Factor | Choose Trivy | Choose Grype | Choose Clair |
|----------------|-------------|-------------|-------------|
| You want all-in-one scanning (containers + IaC + secrets) | ✅ | ❌ | ❌ |
| You need SBOM generation built-in | ✅ | ✅ (via Syft) | ❌ |
| You want automatic registry scanning on push | ❌ | ❌ | ✅ |
| You need the simplest deployment | ✅ | ✅ | ❌ |
| You want Kubernetes admission controller integration | ✅ (Trivy Operator) | ❌ | ❌ |
| You need historical vulnerability tracking | ❌ | ❌ | ✅ |
| You run Project Quay | ❌ | ❌ | ✅ |
| You want misconfiguration detection | ✅ | ❌ | ❌ |
| You need air-gapped / offline scanning | ✅ | ✅ | ❌ (needs DB sync) |

**For most teams**: Start with Trivy. It covers the broadest range of scanning targets, requires minimal setup, and produces excellent CI/CD integration with its official GitHub Action.

**For registry-centric workflows**: Choose Clair if you run your own container registry and want images scanned automatically on push without adding explicit scanning steps to your pipeline.

**For SBOM-first workflows**: Choose Grype if generating and scanning SBOMs is your primary goal. The Syft + Grype combination is the most polished SBOM pipeline in the open-source ecosystem.

## Production Deployment Tips

### Database Freshness

All scanners depend on up-to-date vulnerability databases. Configure automatic updates:

```bash
# Trivy: schedule database refresh
0 */6 * * * docker run --rm aquasec/trivy:latest image --download-db-only

# Grype: database auto-updates on each scan (configurable)
export GRYPE_DB_AUTO_UPDATE=true

# Clair: automatic database updates on startup and interval
# Configure in clair-config.yaml under updater section
```

### Severity Thresholds for Production

Not all vulnerabilities need immediate action. Set practical thresholds:

```bash
# Trivy: block on critical, warn on high
trivy image --exit-code 1 --severity CRITICAL myapp:latest
trivy image --exit-code 0 --severity HIGH myapp:latest

# Grype: fail only on critical
grype myapp:latest --fail-on critical

# Clair: filter results by severity in API queries
curl -s http://clair:6060/api/v1/vulnerability_report/$HASH \
  | jq '.vulnerabilities[] | select(.severity == "Critical")'
```

### Registry Integration with Harbor

For teams running [Harbor container registry](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/), Clair integrates natively as the scanning engine. Trivy is also supported as a pluggable scanner:

```yaml
# Harbor docker-compose (add Trivy as scanner)
trivy-adapter:
  image: goharbor/trivy-adapter-photon:dev
  container_name: trivy-adapter
  restart: always
  environment:
    - SCANNER_TRIVY_CACHE_DIR=/home/scanner/.cache/trivy
    - SCANNER_TRIVY_REPORTS_DIR=/home/scanner/.cache/reports
    - SCANNER_TRIVY_DEBUG_MODE=false
  volumes:
    - trivy-adapter-cache:/home/scanner/.cache/trivy
```

For related reading on container security, see our [Kubernetes hardening guide](../kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/) and [supply chain security best practices](../self-hosted-supply-chain-security-cosign-notation-intoto-2026/).

## FAQ

### Which container image scanner is fastest?

Trivy is generally the fastest for single-image scans because it uses a local BoltDB database and has no network dependency after the initial database download. A typical scan of a medium-sized image (500MB) completes in 5-15 seconds. Grype is comparable for similar images. Clair takes longer on first scan because it must extract and index all image layers through its PostgreSQL pipeline, but subsequent scans of unchanged layers are instant.

### Can I run these scanners offline or in air-gapped environments?

Trivy and Grype both support offline scanning. Download the vulnerability database on a connected machine, transfer it to your air-gapped system, and scan without any network access. Clair requires a PostgreSQL database and periodic updates from vulnerability feeds, making it less suitable for strictly air-gapped environments unless you set up a manual database synchronization process.

### Do these scanners detect zero-day vulnerabilities?

No scanner can detect zero-day vulnerabilities by definition — zero-days are unknown vulnerabilities that have not yet been published to CVE databases. All three scanners rely on known vulnerability databases (NVD, GitHub Advisories, OSV, distro security trackers). For zero-day detection, you need behavioral analysis, runtime security monitoring, or anomaly detection systems like Falco or Tetragon.

### Can I use multiple scanners together?

Yes, and many teams do. A common pattern is running Grype or Trivy in CI/CD pipelines for fast per-commit scanning, combined with Clair for continuous registry-level monitoring. Trivy can also run as a periodic cron job to re-scan all deployed images when its vulnerability database updates, catching new CVEs that were not known at build time.

### How often should I update the vulnerability database?

Daily updates are recommended for production environments. Trivy updates its database automatically every 12 hours by default. Grype checks for updates on each scan. Clair continuously fetches new vulnerability data from configured sources. For compliance requirements (SOC 2, ISO 27001), document your update frequency and verify that scanners are fetching the latest data.

### Which scanner generates the best SBOMs?

Trivy has built-in SBOM generation supporting both CycloneDX and SPDX formats. Grype relies on Syft (a separate Anchore tool) for SBOM generation, but the Syft + Grype combination produces the most detailed SBOMs in the open-source ecosystem, with deep package dependency resolution. Clair does not generate SBOMs — it focuses solely on vulnerability detection.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Scanning: Trivy vs Grype vs Clair Guide 2026",
  "description": "Complete guide to self-hosted container image scanning in 2026. Compare Trivy, Grype, and Clair for Docker image vulnerability detection with Docker Compose setups, CI/CD integration, and registry pipeline configuration.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
