---
title: "Dependency-Track vs Syft vs CycloneDX: Self-Hosted SBOM & Dependency Tracking 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "security", "supply-chain"]
draft: false
description: "Complete guide to self-hosted SBOM generation, analysis, and dependency tracking with OWASP Dependency-Track, Syft, and CycloneDX. Compare features, installation, and real-world usage for supply chain security in 2026."
---

Every modern application pulls in hundreds — sometimes thousands — of third-party packages. Each dependency carries its own dependency tree, licenses, and potential vulnerabilities. Without visibility into what ships inside your software, you cannot answer basic questions: *Does our container include Log4j? Which packages use the GPL license? When was this component last updated?*

The answer is a **Software Bill of Materials (SBOM)** — an inventory of every component in your software supply chain. In 2026, SBOMs are no longer optional. Executive Order 14028, the EU Cyber Resilience Act, and ISO/IEC 5962 all require or strongly recommend SBOM generation.

This guide covers the three leading open-source tools for SBOM generation and dependency tracking, how to self-host them, and how to build a complete supply chain security pipeline.

## Why Self-Host Your SBOM Pipeline?

SBOM data is sensitive. It reveals your full dependency tree, internal component versions, and potential attack surfaces. Sending this information to a third-party SaaS platform creates risks:

- **Data exposure** — Your dependency graph tells attackers exactly which libraries and versions you run, making targeted exploits trivial.
- **Regulatory compliance** — Many frameworks (SOC 2, FedRAMP, ISO 27001) require that security assessment data remain under your control.
- **Offline access** — CI/CD pipelines and air-gapped environments need SBOM tooling that works without internet access.
- **Cost** — Commercial SBOM platforms charge per project or per scan. Self-hosted tools scale with your infrastructure, not your vendor's pricing model.
- **Integration flexibility** — Self-hosted tools integrate directly with your existing CI/CD, ticketing, and monitoring systems without API rate limits or vendor lock-in.

## Understanding the SBOM Ecosystem

Before diving into tools, it helps to understand how SBOM standards and tools fit together:

**SBOM Formats:**
- **CycloneDX** — Lightweight, security-focused format supporting components, vulnerabilities, licenses, and services. Widely adopted by OWASP projects.
- **SPDX** — ISO/IEC 5962 standard format. Strong on license compliance, widely used in enterprise environments.

**Tool Categories:**
- **SBOM Generators** — Scan your code, containers, or filesystems and produce an SBOM document (Syft, Trivy, CycloneDX CLI).
- **SBOM Analyzers** — Ingest SBOM documents, correlate with vulnerability databases, and surface risk (Dependency-Track).
- **Policy Engines** — Enforce rules about allowed licenses, banned components, or maximum vulnerability severity.

The tools covered in this article span both categories, giving you a complete self-hosted SBOM workflow.

## OWASP Dependency-Track: The SBOM Analysis Platform

[Dependency-Track](https://dependencytrack.org/) is an intelligent component analysis platform that ingests SBOMs and continuously monitors your components against vulnerability databases. It is the gold standard for self-hosted dependency tracking.

### Key Features

- **Continuous monitoring** — Automatically re-checks components against NVD, GitHub Advisory Database, OSV, and Snyk when vulnerability databases update.
- **Multi-format support** — Accepts CycloneDX and SPDX SBOMs in JSON and XML formats.
- **Vulnerability correlation** — Maps components to known CVEs with severity scores, CVSS vectors, and remediation advice.
- **License risk analysis** — Flags copyleft, permissive, and proprietary licenses with customizable policy rules.
- **API-first design** — Full REST API and OpenAPI specification for CI/CD integration.
- **Project hierarchy** — Organize SBOMs by team, product line, or environment with parent/child project relationships.
- **Policy management** — Create automated policies (e.g., "block any component with CVSS ≥ 9.0" or "reject GPL-licensed libraries").

### Installation with Docker Compose

Dependency-Track requires a database backend. The recommended setup uses PostgreSQL:

```yaml
# docker-compose.yml
version: "3.8"

services:
  dependency-track:
    image: dependencytrack/apiserver:latest
    ports:
      - "8080:8080"
    environment:
      - ALPINE_DATABASE_MODE=external
      - ALPINE_DATABASE_URL=jdbc:postgresql://postgres:5432/dtrack
      - ALPINE_DATABASE_DRIVER=org.postgresql.Driver
      - ALPINE_DATABASE_USERNAME=dtrack
      - ALPINE_DATABASE_PASSWORD=changeme123
      - ALPINE_DATABASE_POOL_MAX_SIZE=20
    volumes:
      - dt-data:/data
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=dtrack
      - POSTGRES_USER=dtrack
      - POSTGRES_PASSWORD=changeme123
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dtrack -d dtrack"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  dt-data:
  pg-data:
```

For the web frontend, use the dedicated frontend image:

```bash
docker run -d -p 8081:80 dependencytrack/frontend:latest
```

Access the API at `http://localhost:8080` and the frontend at `http://localhost:8081`. Default credentials are `admin` / `admin` — change them immediately.

### Uploading Your First SBOM

Once Dependency-Track is running, you can upload SBOMs via the web UI, REST API, or CI/CD integration:

```bash
# Upload an SBOM via the REST API
curl -X POST "http://localhost:8080/api/v1/bom" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: multipart/form-data" \
  -F "autoCreate=true" \
  -F "projectName=my-application" \
  -F "projectVersion=1.0.0" \
  -F "bom=@bom.json"
```

The `autoCreate=true` flag automatically creates the project if it does not exist, making it ideal for CI/CD pipelines.

### Configuring Vulnerability Sources

Dependency-Track pulls vulnerability data from multiple sources. Configure them under **Administration → Analyzers**:

- **Internal Analyzer (NVD)** — Enabled by default. Fetches CVE data from the National Vulnerability Database.
- **GitHub Advisory** — Connect with a GitHub token for broader coverage including npm, Maven, and PyPI advisories.
- **OSV** — Google's Open Source Vulnerabilities database. Covers Go, Rust, and additional ecosystems.
- **Snyk** — Premium integration (requires Snyk API key) for curated vulnerability data with fix guidance.

Enable the sources you need and configure the analysis interval. A daily update cycle is recommended for most teams.

---

## Syft: Fast SBOM Generation

[Syft](https://github.com/anchore/syft) by Anchore is the leading SBOM generation tool. It scans container images, filesystems, and archives to produce detailed CycloneDX or SPDX documents. Syft excels at breadth — it detects packages across 20+ ecosystems from a single scan.

### Key Features

- **Multi-source scanning** — Container images (Docker, Podman, OCI), local filesystems, tar archives, and SBOM files.
- **Wide ecosystem coverage** — Detects packages from npm, PyPI, RubyGems, Go modules, Rust crates, Java JARs, .NET, Alpine, Debian, RPM, and more.
- **Multiple output formats** — CycloneDX (JSON/XML), SPDX (JSON/Tag-Value), GitHub dependency snapshot, and Syft's own table format.
- **Speed** — Written in Go with parallel cataloging. A typical container image scan completes in 2–10 seconds.
- **Attestation support** — Generates SLSA and in-toto attestations for supply chain verification.
- **CI/CD friendly** — Single static binary, no runtime dependencies, exit codes for policy enforcement.

### Installation

```bash
# Linux/macOS via install script
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Homebrew
brew install syft

# Binary download (latest release)
curl -L "https://github.com/anchore/syft/releases/latest/download/syft_$(uname -s)_$(uname -m).tar.gz" | tar -xz syft
sudo mv syft /usr/local/bin/
```

### Basic Usage

```bash
# Scan a container image and output CycloneDX JSON
syft myapp:latest -o cyclonedx-json > bom.json

# Scan with SPDX format
syft myapp:latest -o spdx-json > bom-spdx.json

# Scan a local directory
syft dir:/opt/myproject -o cyclonedx-json > bom.json

# Scan a tar archive
syft archive:myproject.tar.gz -o cyclonedx-json > bom.json

# Table output for quick inspection
syft nginx:latest
```

### Advanced Scanning Configuration

For production use, tune Syft's behavior through its configuration file:

```yaml
# syft-config.yaml
log:
  level: "info"

search:
  scope: "squashed"        # "squashed" (default layers only) or "all-layers"
  unindexed-archives: true  # Scan archives nested within packages
  indexed-archives: true

relationships:
  exclude-binary-packages-from-file-ownership: true

python:
  guess-unpinned-requirements: true  # Detect requirements.txt even without lock files
```

```bash
# Run with custom config
syft -c syft-config.yaml myapp:latest -o cyclonedx-json > bom.json

# Scope: "all-layers" catches packages in intermediate build layers
syft --scope all-layers myapp:latest -o cyclonedx-json > bom.json
```

### Integrating Syft with Dependency-Track

The most powerful workflow combines Syft's scanning with Dependency-Track's analysis:

```bash
#!/bin/bash
# ci-sbom-pipeline.sh

IMAGE="myapp:${CI_COMMIT_SHA}"
PROJECT="my-application"
VERSION="${CI_COMMIT_SHA}"
DT_URL="http://localhost:8080"
DT_API_KEY="${DEPENDENCY_TRACK_API_KEY}"

# Step 1: Build and scan the image
docker build -t "${IMAGE}" .
syft "${IMAGE}" -o cyclonedx-json > bom.json

# Step 2: Upload to Dependency-Track
curl -s -X POST "${DT_URL}/api/v1/bom" \
  -H "X-API-Key: ${DT_API_KEY}" \
  -F "autoCreate=true" \
  -F "projectName=${PROJECT}" \
  -F "projectVersion=${VERSION}" \
  -F "bom=@bom.json"

echo "SBOM uploaded. Check ${DT_URL} for analysis results."
```

This pipeline generates an SBOM for every build, uploads it to Dependency-Track, and lets the platform continuously monitor for newly discovered vulnerabilities.

---

## CycloneDX CLI: The Swiss Army Knife

The [CycloneDX CLI tool](https://github.com/CycloneDX/cyclonedx-cli) provides a comprehensive suite of commands for working with CycloneDX SBOMs. While Syft generates SBOMs and Dependency-Track analyzes them, the CycloneDX CLI operates on SBOM documents directly — merging, diffing, validating, and converting them.

### Key Features

- **Merge** — Combine multiple SBOMs into a single document (e.g., merge frontend and backend SBOMs).
- **Diff** — Compare two SBOMs to identify added, removed, and updated components between releases.
- **Validate** — Verify SBOM documents against the CycloneDX JSON Schema.
- **Convert** — Transform between CycloneDX JSON, XML, and Protocol Buffers.
- **Analyze** — Perform local vulnerability analysis without a server, using built-in databases.
- **Modify** — Add, remove, or update components in existing SBOMs programmatically.

### Installation

```bash
# .NET global tool (requires .NET 8 SDK)
dotnet tool install --global CycloneDX

# Or use the Docker image
docker run ghcr.io/cyclonedx/cyclonedx-cli --help

# NPM package (JavaScript ecosystem)
npm install -g @cyclonedx/cyclonedx-npm
```

### Practical Commands

```bash
# Validate an SBOM document
cyclonedx-cli validate --input-file bom.json

# Merge multiple SBOMs (e.g., from microservices)
cyclonedx-cli merge --input-files frontend-bom.json backend-bom.json \
  --output-file combined-bom.json

# Diff two releases to see what changed
cyclonedx-cli diff --input-files bom-v1.0.json bom-v1.1.json \
  --type all --output-format markdown > changelog.md

# Convert between formats
cyclonedx-cli convert --input-file bom.json --input-format json \
  --output-format xml --output-file bom.xml

# Analyze vulnerabilities locally (no server needed)
cyclonedx-cli analyze --input-file bom.json --project my-app \
  --output-format markdown > vulnerability-report.md
```

### Release Comparison Workflow

The `diff` command is particularly valuable for release management. It produces structured output showing exactly which components changed between versions:

```bash
# Compare production releases
cyclonedx-cli diff \
  --input-files bom-production-v2.3.0.json bom-production-v2.4.0.json \
  --type added --output-format table

# Output:
# +------------------------+------------+
# | Component              | Version    |
# +------------------------+------------+
# | express                | 4.18.3     |  ← NEW
# | lodash                 | 4.17.22    |  ← NEW
# | typescript             | 5.4.2      |  ← UPDATED (was 5.3.3)
# | webpack                | 5.91.0     |  ← REMOVED
# +------------------------+------------+
```

This enables automatic changelog generation, security review gates, and compliance audits.

---

## Comparison Table

| Feature | Dependency-Track | Syft | CycloneDX CLI |
|---------|-----------------|------|---------------|
| **Primary role** | SBOM analysis & monitoring | SBOM generation | SBOM manipulation |
| **SBOM formats** | CycloneDX, SPDX | CycloneDX, SPDX, Syft | CycloneDX (JSON/XML/PB) |
| **Vulnerability sources** | NVD, GitHub, OSV, Snyk | Via Grype integration | Built-in OSV (limited) |
| **Continuous monitoring** | Yes (scheduled re-analysis) | No (single scan) | No (single analysis) |
| **Policy enforcement** | Yes (customizable rules) | Limited (exit codes) | No |
| **Merge SBOMs** | No | No | Yes |
| **Diff SBOMs** | Via API comparison | No | Yes |
| **CI/CD integration** | REST API | CLI binary | CLI / Docker |
| **Database required** | Yes (PostgreSQL/H2) | No | No |
| **Web UI** | Yes (full-featured) | No | No |
| **Language** | Java | Go | .NET |
| **Docker image size** | ~500 MB | ~80 MB | ~150 MB |
| **Best for** | Centralized SBOM management | Fast SBOM generation in CI | SBOM transformation & auditing |

---

## Building a Complete Self-Hosted SBOM Pipeline

Here is a production-ready architecture that combines all three tools:

### Architecture

```
┌─────────────┐     ┌──────────┐     ┌──────────────────┐
│  CI/CD      │────>│  Syft    │────>│ Dependency-Track │
│  Pipeline   │     │  (scan)  │     │ (analyze/monitor)│
└─────────────┘     └──────────┘     └────────┬─────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │  CycloneDX CLI     │
                                    │  (merge/diff/audit)│
                                    └───────────────────┘
```

### Step 1: Set Up the Infrastructure

```yaml
# Full docker-compose for the SBOM platform
version: "3.8"

services:
  dependency-track:
    image: dependencytrack/apiserver:latest
    ports:
      - "8080:8080"
    environment:
      - ALPINE_DATABASE_MODE=external
      - ALPINE_DATABASE_URL=jdbc:postgresql://postgres:5432/dtrack
      - ALPINE_DATABASE_DRIVER=org.postgresql.Driver
      - ALPINE_DATABASE_USERNAME=dtrack
      - ALPINE_DATABASE_PASSWORD=dtrack_secure_password
    volumes:
      - dt-data:/data
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  dt-frontend:
    image: dependencytrack/frontend:latest
    ports:
      - "8081:80"
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=dtrack
      - POSTGRES_USER=dtrack
      - POSTGRES_PASSWORD=dtrack_secure_password
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dtrack -d dtrack"]
      interval: 10s
      retries: 5
    restart: unless-stopped

volumes:
  dt-data:
  pg-data:
```

### Step 2: CI/CD Integration (GitHub Actions)

```yaml
# .github/workflows/sbom.yml
name: SBOM Generation and Upload

on:
  push:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"  # Weekly scan even without changes

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build container image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Generate SBOM with Syft
        uses: anchore/sbom-action@v0
        with:
          image: myapp:${{ github.sha }}
          format: cyclonedx-json
          output-file: bom.json

      - name: Upload to Dependency-Track
        run: |
          curl -s -X POST "${DT_URL}/api/v1/bom" \
            -H "X-API-Key: ${DT_API_KEY}" \
            -F "autoCreate=true" \
            -F "projectName=${{ github.repository }}" \
            -F "projectVersion=${{ github.sha }}" \
            -F "bom=@bom.json"
        env:
          DT_URL: ${{ secrets.DEPENDENCY_TRACK_URL }}
          DT_API_KEY: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}

      - name: Fail on critical vulnerabilities
        run: |
          VULNS=$(curl -s "${DT_URL}/api/v1/vulnerability/component" \
            -H "X-API-Key: ${DT_API_KEY}" \
            -G --data-urlencode "project=${PROJECT_UUID}" \
            -G --data-urlencode "severity=9")
          CRITICAL=$(echo "$VULNS" | jq '[.[] | select(.cvssV3BaseScore >= 9.0)] | length')
          if [ "$CRITICAL" -gt 0 ]; then
            echo "::error::$CRITICAL critical vulnerabilities found"
            exit 1
          fi
```

### Step 3: Automated Alerting

Dependency-Track supports webhook notifications. Configure alerts under **Administration → Alerts**:

- **New vulnerability alert** — Webhook to Slack, Discord, or your incident management system.
- **Policy violation** — Email or webhook when a new component violates license or security policies.
- **BOM consumption** — Notification when a new SBOM is processed.

Example webhook payload for Slack integration:

```json
{
  "title": "Dependency-Track Alert",
  "content": {
    "notification": "A new vulnerability was identified in a monitored component",
    "component": "log4j-core 2.14.1",
    "vulnerability": "CVE-2021-44228",
    "severity": "CRITICAL",
    "project": "my-application v1.0.0"
  }
}
```

### Step 4: SBOM Diffing for Release Reviews

Before each production release, generate an SBOM diff to understand what changed:

```bash
#!/bin/bash
# release-review.sh

PREV_TAG=$(git describe --tags --abbrev=0 HEAD^)
CURR_TAG=$(git describe --tags --abbrev=0)

# Generate SBOMs for both releases
docker build -t "myapp:${PREV_TAG}" --target runtime .
syft "myapp:${PREV_TAG}" -o cyclonedx-json > "bom-${PREV_TAG}.json"

docker build -t "myapp:${CURR_TAG}" --target runtime .
syft "myapp:${CURR_TAG}" -o cyclonedx-json > "bom-${CURR_TAG}.json"

# Generate diff report
cyclonedx-cli diff \
  --input-files "bom-${PREV_TAG}.json" "bom-${CURR_TAG}.json" \
  --type all \
  --output-format markdown \
  > "release-sbom-diff-${PREV_TAG}-to-${CURR_TAG}.md"

echo "Release SBOM diff saved. Review before deploying."
```

---

## Advanced: License Compliance Automation

Dependency-Track can enforce license policies across all projects. Create license groups under **Administration → License Groups**:

1. **Allowed licenses** — MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC
2. **Review required** — LGPL-2.1, LGPL-3.0, MPL-2.0, CDDL-1.0
3. **Denied licenses** — GPL-2.0, GPL-3.0, AGPL-3.0, SSPL-1.0

Then create a policy that fails the build when denied licenses are detected:

```bash
# Check for denied licenses after SBOM upload
curl -s "${DT_URL}/api/v1/policy/violation/project/${PROJECT_UUID}" \
  -H "X-API-Key: ${DT_API_KEY}" | \
  jq -r '.[] | select(.policy.name == "License Policy") | "\(.component.name): \(.component.license)"'
```

This approach prevents GPL-licensed code from accidentally shipping into proprietary products and creates an auditable compliance trail.

---

## Performance and Scaling Considerations

For organizations managing hundreds of projects:

- **PostgreSQL tuning** — Increase `shared_buffers` to 25% of RAM, set `effective_cache_size` to 75%. Dependency-Track benefits significantly from proper PostgreSQL configuration.
- **Memory allocation** — The Java API server needs at least 4 GB heap for moderate workloads. Set `-Xmx8g` in `JAVA_OPTS` for 500+ projects.
- **Vulnerability source sync** — Stagger analyzer schedules to avoid simultaneous database fetches. NVD sync at 2 AM, GitHub Advisory at 4 AM, OSV at 6 AM.
- **Horizontal scaling** — Run multiple Dependency-Track API server instances behind a reverse proxy. They share the same PostgreSQL database and coordinate via the database lock mechanism.
- **SBOM retention** — Configure automated project version cleanup to remove old SBOMs. Retain the last 10 versions per project to manage database growth.

---

## Conclusion

A complete self-hosted SBOM pipeline gives you full visibility and control over your software supply chain:

- **Syft** generates detailed SBOMs quickly across 20+ package ecosystems — ideal for CI/CD integration.
- **Dependency-Track** provides continuous vulnerability and license monitoring with a powerful web interface, policy engine, and REST API — the central hub for SBOM analysis.
- **CycloneDX CLI** handles SBOM manipulation — merging microservice SBOMs, diffing releases, and validating documents against the specification.

Together, these tools form a production-grade supply chain security platform that costs nothing in licensing, runs entirely on your infrastructure, and keeps your dependency data under your control. With increasing regulatory requirements around software transparency in 2026, implementing this stack is both a security best practice and a compliance necessity.

Start with Syft to generate SBOMs for your most critical applications, connect them to Dependency-Track for continuous monitoring, and use CycloneDX CLI to automate release reviews. Your future self — and your security auditor — will thank you.
