---
title: "ScanCode vs FOSSology vs ORT: Self-Hosted License Compliance Scanners 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "compliance", "devops", "security"]
draft: false
description: "Compare the best open-source license compliance scanning tools — ScanCode Toolkit, FOSSology, and ORT — with Docker setup guides, feature comparisons, and CI/CD integration."
---

Every modern software project depends on dozens — sometimes hundreds — of third-party open-source packages. Each dependency ships with its own license, and mixing incompatible licenses can create legal liabilities, force code disclosure, or block commercial distribution entirely. Commercial SaaS platforms like FOSSA and Black Duck solve this problem, but they require sending your complete dependency tree to a third-party server.

For organizations that need to keep their source code and bill of materials on-premise, self-hosted license scanners provide full compliance scanning without data leaving your infrastructure. This guide compares the three most capable open-source options: **ScanCode Toolkit**, **FOSSology**, and the **OSS Review Toolkit (ORT)**.

## Why Self-Host Your License Scanning

Running license scanning infrastructure on your own servers offers several advantages over SaaS alternatives:

- **Data privacy** — Your complete dependency graph, including proprietary code paths, never leaves your network
- **Unlimited scans** — No per-project or per-developer licensing caps that SaaS vendors impose
- **CI/CD integration** — Native Docker containers fit into any pipeline without API rate limits
- **Custom rulesets** — Define organization-specific license policies that proprietary platforms won't accommodate
- **Offline operation** — Scan air-gapped build environments without internet connectivity
- **Regulatory compliance** — Meet data residency requirements in regulated industries

For teams already managing [supply chain security with cosign and in-toto](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/), adding self-hosted license scanning completes the full software composition analysis (SCA) stack.

## ScanCode Toolkit

ScanCode Toolkit, developed by nexB (the same company behind AboutCode), is the most widely deployed open-source license detection engine. Written in Python, it identifies licenses, copyrights, and package manifests across codebases of any size.

### Key Features

- Detects **3,500+ license variants** and **1,000+ license categories** using pattern matching and text analysis
- Identifies **copyright holders**, **email addresses**, and **URLs** embedded in source files
- Scans **package manifests** for npm, pip, Maven, Gradle, NuGet, Go modules, and more
- Outputs results in **JSON, HTML, CSV, SPDX, and CycloneDX** formats
- Provides a **license classification system** (permissive, copyleft, proprietary, public domain)
- Supports **binary file scanning** for compiled artifacts

### Installation

ScanCode runs on Python 3.8+. The recommended installation uses a virtual environment:

```bash
# Clone and set up ScanCode Toolkit
git clone https://github.com/nexB/scancode-toolkit.git
cd scancode-toolkit
python3 -m venv .
source bin/activate
pip install -e .

# Scan a project directory
scancode --license --copyright --package --info \
  --json-pp scan-results.json \
  --html scan-results.html \
  --generated-by "compliance-team" \
  /path/to/project/
```

### Docker Deployment

ScanCode provides an official Docker image for containerized scanning:

```dockerfile
# Dockerfile.scanner
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    bzip2 xz-utils zlib1g libgomp1 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install scancode-toolkit

WORKDIR /scan
ENTRYPOINT ["scancode"]
CMD ["--help"]
```

Build and run the scanner container:

```bash
docker build -t scancode-scanner -f Dockerfile.scanner .

# Scan a local project by mounting it as a volume
docker run --rm \
  -v "$(pwd)/project:/scan/src:ro" \
  -v "$(pwd)/output:/scan/out" \
  scancode-scanner \
  --license --copyright --package \
  --json-pp /scan/out/results.json \
  /scan/src/
```

### Strengths

- **Most comprehensive license database** in the open-source ecosystem
- **SPDX-compliant** output for regulatory reporting
- **Fast scanning** with multiprocessing support (`--processes` flag)
- **Active development** — 2,522 GitHub stars, updated April 2026
- **AboutCode ecosystem** integration with ScanPipe for continuous monitoring

### Limitations

- Command-line only — no built-in web interface for team collaboration
- Scanning large codebases (>1M files) requires significant memory (8GB+ recommended)
- License detection can produce false positives on boilerplate text that resembles license headers

## FOSSology

FOSSology is the oldest and most feature-complete open-source license compliance platform. Originally developed by HP and now maintained by the Linux Foundation, it provides a full web-based workflow for license analysis, obligation tracking, and report generation.

### Key Features

- **Web-based UI** for multi-user license review workflows
- **Three-stage analysis pipeline**: scanner → mono agent (copyright/URL/email detection) → decision engine
- **Obligation tracking** — maps detected licenses to specific compliance requirements (attribution, source distribution, etc.)
- **SPDX 2.3 and SPDX 3.0** report generation
- **Reusable analysis results** — share scan results across projects and teams
- **REST API** for CI/CD pipeline integration
- **Role-based access control** — assign reviewer, admin, and read-only permissions

### Docker Compose Setup

FOSSology ships with an official Docker Compose configuration that deploys the web frontend, scheduler, and PostgreSQL database:

```yaml
version: "3.8"
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      - POSTGRES_DB=fossology
      - POSTGRES_USER=fossy
      - POSTGRES_PASSWORD=your-secure-password
      - POSTGRES_INITDB_ARGS='-E SQL_ASCII'
    volumes:
      - fossology-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready --dbname fossology --username fossy"]
      interval: 10s
      timeout: 5s
      retries: 5

  scheduler:
    image: fossology/fossology:latest
    restart: unless-stopped
    environment:
      - FOSSOLOGY_DB_HOST=db
      - FOSSOLOGY_DB_NAME=fossology
      - FOSSOLOGY_DB_USER=fossy
      - FOSSOLOGY_DB_PASSWORD=your-secure-password
    command: scheduler
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - fossology-repo:/srv/fossology/repository/

  web:
    image: fossology/fossology:latest
    restart: unless-stopped
    environment:
      - FOSSOLOGY_DB_HOST=db
      - FOSSOLOGY_DB_NAME=fossology
      - FOSSOLOGY_DB_USER=fossy
      - FOSSOLOGY_DB_PASSWORD=your-secure-password
      - FOSSOLOGY_SCHEDULER_HOST=scheduler
    command: web
    ports:
      - "8081:80"
    depends_on:
      db:
        condition: service_healthy
      scheduler:
        condition: service_started
    volumes:
      - fossology-repo:/srv/fossology/repository/

volumes:
  fossology-db:
  fossology-repo:
```

Deploy with `docker compose up -d` and access the web UI at `http://localhost:8081`. Default credentials are `fossy/fossy` — change them immediately.

### REST API Integration

FOSSology's REST API enables automated scanning from CI/CD pipelines:

```bash
# Authenticate and get a token
TOKEN=$(curl -s -X POST "http://localhost:8081/repo/api/v1/tokens" \
  -H "Content-Type: application/json" \
  -d '{"username":"fossy","password":"your-secure-password"}' | jq -r '.Token')

# Upload a source archive for scanning
UPLOAD_ID=$(curl -s -X POST "http://localhost:8081/repo/api/v1/uploads" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@my-project.tar.gz" \
  -F "folder=1" \
  -F "description=CI scan of my-project v2.1" | jq -r '.message' | grep -o '[0-9]\+')

# Check scan status
curl -s "http://localhost:8081/repo/api/v1/uploads/$UPLOAD_ID/status" \
  -H "Authorization: Bearer $TOKEN"

# Download SPDX report when complete
curl -s "http://localhost:8081/repo/api/v1/uploads/$UPLOAD_ID/spdx" \
  -H "Authorization: Bearer $TOKEN" \
  -o spdx-report.spdx
```

### Strengths

- **Only option with a full web UI** — essential for legal team review workflows
- **Obligation tracking** goes beyond simple license detection to tell you *what to do*
- **Linux Foundation backing** provides institutional stability
- **981 GitHub stars**, active development with regular releases
- Supports **bulk upload** of entire artifact repositories

### Limitations

- **Resource-heavy** — the PostgreSQL backend and multi-container setup require 4GB+ RAM
- **Slower initial scans** compared to CLI-only tools due to the database write path
- **Web UI can feel dated** — the interface is functional but not modern
- License detection is less granular than ScanCode for uncommon or custom licenses

## OSS Review Toolkit (ORT)

ORT, developed by HERE Technologies and Now an open-source project under its own organization, takes a fundamentally different approach. Rather than focusing only on license detection, ORT orchestrates the entire open-source compliance workflow: dependency resolution, license scanning, vulnerability checking, and policy evaluation.

### Key Features

- **Multi-language analyzer** — natively supports Gradle, Maven, npm, Yarn, Go, Cargo, CocoaPods, pip, NuGet, SBT, Composer, Bundler, and more
- **Integrated vulnerability scanning** — checks dependencies against OSV and advisory databases
- **Policy evaluation engine** — define rules in HOCON format to fail builds on prohibited licenses
- **Reporter generation** — outputs SPDX, CycloneDX, Web App, and static HTML reports
- **Curations mechanism** — override incorrect license detections with organization-approved metadata
- **Evaluator** — automated pass/fail decisions based on configurable license policies

### Installation

ORT runs on the JVM. The recommended approach uses the pre-built CLI:

```bash
# Download the latest ORT release
curl -LO https://github.com/oss-review-toolkit/ort/releases/latest/download/ort.zip
unzip ort.zip -d /opt/ort
export PATH="/opt/ort/bin:$PATH"

# Analyze a project (detects package manager automatically)
ort analyze -i /path/to/project/ -o analyzer-result.json

# Run license scanner on analyzer results
ort scan -i analyzer-result.json -o scan-result.json

# Evaluate results against a license policy
ort evaluate \
  --license-file /path/to/license-policy.hocon \
  -i scan-result.json \
  -o evaluation-result.json

# Generate an SPDX report
ort report \
  -i scan-result.json \
  -o report-dir/ \
  --report-formats spdx,cyclonedx,static-html
```

### Docker Setup

ORT provides an official Docker image that includes all supported package managers:

```dockerfile
# Dockerfile.ort
FROM ossreviewtoolkit/ort:latest

# Optional: Add your organization's license policy
COPY license-policy.hocon /etc/ort/

# Optional: Add curated license data
COPY curations.yml /etc/ort/

WORKDIR /project
ENTRYPOINT ["ort"]
```

Run a complete compliance pipeline in a single container:

```bash
docker run --rm \
  -v "$(pwd)/project:/project:ro" \
  -v "$(pwd)/output:/output" \
  ossreviewtoolkit/ort:latest \
  --info analyze -i /project -o /output/analyzer.json && \
  ort --info scan -i /output/analyzer.json -o /output/scan.json && \
  ort --info evaluate \
    --license-file /etc/ort/license-policy.hocon \
    -i /output/scan.json -o /output/eval.json && \
  ort --info report \
    -i /output/scan.json \
    -o /output/reports/ \
    --report-formats spdx,cyclonedx,static-html
```

### Sample License Policy

Define which licenses are allowed, prohibited, or require review:

```hocon
// license-policy.hocon
rules {
  // Allowed without restriction
  licenses {
    "Apache-2.0"    { license_status = ALLOWED }
    "MIT"           { license_status = ALLOWED }
    "BSD-2-Clause"  { license_status = ALLOWED }
    "BSD-3-Clause"  { license_status = ALLOWED }
    "ISC"           { license_status = ALLOWED }
    "CC0-1.0"       { license_status = ALLOWED }
    "Unlicense"     { license_status = ALLOWED }

    // Requires legal team review
    "LGPL-2.1-only" { license_status = REVIEW }
    "MPL-2.0"       { license_status = REVIEW }
    "CDDL-1.0"      { license_status = REVIEW }

    // Prohibited — will fail the build
    "GPL-2.0-only"  { license_status = PROHIBITED }
    "GPL-3.0-only"  { license_status = PROHIBITED }
    "AGPL-3.0-only" { license_status = PROHIBITED }
    "SSPL-1.0"      { license_status = PROHIBITED }
    "EUPL-1.1"      { license_status = PROHIBITED }
  }
}
```

### Strengths

- **End-to-end pipeline** — the only tool that handles analysis, scanning, evaluation, and reporting in one framework
- **Policy enforcement** — can fail CI builds automatically when prohibited licenses are detected
- **1,988 GitHub stars**, updated April 2026, backed by HERE Technologies
- **Curations** let you correct false positives once and reuse across projects
- **Vulnerability integration** combines license and security scanning in one pass

### Limitations

- **Steeper learning curve** — HOCON policy files and multi-stage pipeline require initial investment
- **JVM-based** — heavier resource footprint than Python-based alternatives
- **No web UI** — results are file-based reports, not interactive dashboards
- **Kotlin codebase** — harder to contribute to compared to Python projects

## Comparison Table

| Feature | ScanCode Toolkit | FOSSology | ORT |
|---|---|---|---|
| **License** | Apache 2.0 | GPL 2.0 | Apache 2.0 |
| **Language** | Python | PHP + C + Bash | Kotlin (JVM) |
| **GitHub Stars** | 2,522 | 981 | 1,988 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Web UI** | No | Yes | No |
| **License Detection** | 3,500+ variants | 1,500+ variants | Via integrated ScanCode |
| **Copyright Detection** | Yes | Yes | No (relies on scanners) |
| **Package Manifest Scan** | 30+ formats | Via upload | 14 package managers |
| **SPDX Output** | Yes (2.2/2.3) | Yes (2.3/3.0) | Yes (2.3) |
| **CycloneDX Output** | Yes | Via plugin | Yes |
| **CI/CD Integration** | CLI + JSON output | REST API | Full pipeline CLI |
| **Policy Enforcement** | No (external) | Obligation tracking | Built-in evaluator |
| **Vulnerability Scanning** | No | No | Yes (OSV database) |
| **Multi-user Workflow** | No | Yes (RBAC) | No |
| **Docker Support** | Yes | Docker Compose | Official image |
| **RAM Requirement** | 8GB+ for large repos | 4GB+ | 2GB+ (JVM) |
| **Best For** | Deep license audits | Legal team workflows | CI/CD automation |

## Choosing the Right Tool

### Use ScanCode Toolkit When

- You need the **most accurate and comprehensive** license detection available
- Your team works primarily with **CLI tools** and JSON output pipelines
- You need to detect **copyrights and package manifests** alongside licenses
- You want to integrate with **AboutCode tools** like ScanPipe for ongoing monitoring

### Use FOSSology When

- Your **legal team needs a web interface** to review and classify scan results
- You need **multi-user workflows** with role-based permissions
- **Obligation tracking** is a requirement — knowing not just *what* licenses exist, but *what actions* they require
- You need to manage **large artifact repositories** with shared scan results

### Use ORT When

- You want to **automate compliance checks in CI/CD** with automatic pass/fail decisions
- Your project uses **multiple languages** and needs a unified analysis tool
- You want **license scanning and vulnerability checking** in a single pipeline
- You need **curations** to handle false positives at organizational scale

### Using All Three Together

A common enterprise pattern combines the strengths of each tool:

1. **ORT** runs in CI/CD as the first gate — analyzing dependencies, running quick scans, and enforcing policies
2. **ScanCode Toolkit** performs deep scans on release artifacts for thorough compliance audits
3. **FOSSology** provides the web interface where legal teams review complex cases and track obligations

This layered approach catches 95% of issues automatically in CI while reserving manual review for edge cases.

## CI/CD Integration Example

Here is a GitHub Actions workflow that runs ORT as a compliance gate:

```yaml
name: License Compliance Check
on:
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"  # Weekly scan every Monday

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run ORT analyze
        uses: oss-review-toolkit/ort-ci@main
        with:
          arguments: "--info analyze -i . -o ort-results/analyzer.json"

      - name: Run ORT scan
        uses: oss-review-toolkit/ort-ci@main
        with:
          arguments: "--info scan -i ort-results/analyzer.json -o ort-results/scan.json"

      - name: Evaluate license policy
        uses: oss-review-toolkit/ort-ci@main
        with:
          arguments: >
            --info evaluate
            --license-file license-policy.hocon
            -i ort-results/scan.json
            -o ort-results/evaluation.json

      - name: Generate reports
        uses: oss-review-toolkit/ort-ci@main
        if: always()
        with:
          arguments: >
            --info report
            -i ort-results/scan.json
            -o ort-results/reports/
            --report-formats static-html,spdx,cyclonedx

      - name: Upload compliance reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: license-compliance-reports
          path: ort-results/reports/
```

For teams also managing [dependency update automation with Renovate](../2026-04-19-renovate-vs-dependabot-vs-updatecli-self-hosted-dependency-automation-guide-2026/), combining automated dependency updates with license compliance scanning creates a complete open-source governance pipeline.

## FAQ

### What is the difference between license scanning and vulnerability scanning?

License scanning identifies the legal terms under which each dependency can be used (e.g., MIT, GPL, Apache 2.0). Vulnerability scanning identifies security flaws (CVEs) in those dependencies. Both are critical for software supply chain security, but they address different risks. ORT is the only tool in this comparison that performs both functions in a single pipeline.

### Can these tools detect custom or proprietary licenses?

ScanCode Toolkit has the most comprehensive database with 3,500+ known license patterns and can also flag unknown licenses for manual review. FOSSology allows you to add custom license texts to its detection database through the admin interface. ORT inherits ScanCode's detection capabilities when using it as the integrated scanner.

### Which tool is best for CI/CD automation?

ORT is purpose-built for CI/CD integration. Its evaluator component can automatically fail a build when prohibited licenses are detected, and its reporter generates compliance artifacts without any manual intervention. ScanCode can also be integrated into CI pipelines via its CLI, but it lacks built-in policy enforcement. FOSSology's REST API enables CI integration but is better suited for asynchronous scanning workflows rather than build-time gates.

### Do any of these tools support SPDX 3.0?

FOSSology supports SPDX 3.0 for report generation. ScanCode Toolkit supports SPDX 2.2 and 2.3. ORT supports SPDX 2.3. SPDX 3.0 adoption is still emerging, so 2.3 remains the most widely compatible version across the ecosystem.

### How much disk space and RAM do these tools require?

ScanCode Toolkit requires 8GB+ RAM for scanning large codebases (1M+ files) and its Python virtual environment takes approximately 3GB of disk space. FOSSology's Docker Compose stack requires 4GB+ RAM due to PostgreSQL and the multi-container architecture. ORT needs 2GB+ for the JVM heap and its Docker image is approximately 1.5GB. All three tools require additional disk space for scan results and reports.

### Can I use these tools with private or internal repositories?

All three tools work with private repositories since they run entirely on your infrastructure. ScanCode and ORT scan local file paths, so you check out the private repository and scan it directly. FOSSology accepts file uploads through its web UI or REST API, keeping all data within your network. None of these tools send your code or dependency data to external services.

### How do these compare to commercial tools like FOSSA or Black Duck?

Commercial tools offer hosted infrastructure, support contracts, and sometimes broader license databases. However, self-hosted tools eliminate per-developer licensing costs, avoid sending dependency data to third parties, and can be customized to match internal policies exactly. ScanCode's license detection database is comparable to commercial offerings, and FOSSology's obligation tracking is unique among both open-source and commercial tools.

For organizations already running [vulnerability scanners like Trivy and Grype](../openvas-trivy-grype-self-hosted-vulnerability-scanner-guide/), adding a self-hosted license scanner completes the open-source compliance picture without introducing additional SaaS dependencies.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ScanCode vs FOSSology vs ORT: Self-Hosted License Compliance Scanners 2026",
  "description": "Compare the best open-source license compliance scanning tools — ScanCode Toolkit, FOSSology, and ORT — with Docker setup guides, feature comparisons, and CI/CD integration.",
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
