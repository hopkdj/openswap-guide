---
title: "OWASP Dependency-Check vs Trivy vs Grype: Best Self-Hosted Dependency Scanning 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "security", "devsecops"]
draft: false
description: "Compare OWASP Dependency-Check, Trivy, and Grype for self-hosted dependency vulnerability scanning. Complete guide with Docker setups, configuration examples, and feature comparison for multi-language projects."
---

Modern applications rely on hundreds — sometimes thousands — of third-party libraries. Every dependency is a potential attack vector. The 2024 Sonatype State of the Software Supply Chain report found that **68% of codebases contain at least one known vulnerability** in their direct or transitive dependencies. Running your own dependency vulnerability scanner gives you full control over scan frequency, data privacy, and integration with your CI/CD pipeline — without sending your dependency trees to cloud services.

In this guide, we compare three leading open-source dependency scanning tools: **OWASP Dependency-Check**, **Trivy**, and **Grype**. Each can scan your project's language dependencies (Maven, npm, pip, NuGet, Go modules, and more) for known CVEs, and each can be self-hosted via Docker.

## Why Self-Hosted Dependency Scanning?

Commercial Software Composition Analysis (SCA) platforms like Snyk, Mend (formerly WhiteSource), and GitHub Dependabot offer convenience — but they come with trade-offs:

- **Data privacy**: Cloud SCA tools upload your full dependency trees (and sometimes source code) to their servers. Self-hosted scanners keep everything on your infrastructure.
- **Cost**: Per-developer pricing for commercial SCA scales quickly. Self-hosted tools are free and unlimited.
- **Customization**: Run scans on any schedule, integrate with internal vulnerability databases, and enforce custom severity thresholds.
- **Air-gapped environments**: Self-hosted scanners work in isolated networks where cloud services are unreachable.

For teams that need full control over their supply-chain security posture, self-hosted dependency scanning is the right choice.

## Tool Overview

### OWASP Dependency-Check

[OWASP Dependency-Check](https://github.com/dependency-check/DependencyCheck) is the longest-running open-source SCA tool, first released in 2012. It identifies project dependencies and checks them against the National Vulnerability Database (NVD), generating HTML, XML, and JSON reports with CVE findings.

- **GitHub**: `dependency-check/DependencyCheck` — 7,525 stars, Apache 2.0 license
- **Languages supported**: Java (Maven, Gradle, Ant), .NET, Node.js, Python, Ruby, PHP, Go, Swift, Rust
- **Data sources**: NVD CPE/CVE, OSS Index, RetireJS, Node Audit, Bundle Audit, Central Analyzer
- **Output formats**: HTML, XML, JSON, CSV, JUnit, SARIF

Dependency-Check is a **dedicated SCA tool** — it focuses exclusively on dependency vulnerability detection and does not scan containers, IaC, or cloud configurations.

### Trivy

[Trivy](https://github.com/aquasecurity/trivy) by Aqua Security is a comprehensive security scanner that covers dependencies, containers, IaC, Kubernetes, and cloud configurations. Originally focused on container scanning, it has evolved into a full-spectrum DevSecOps tool.

- **GitHub**: `aquasecurity/trivy` — 34,729 stars, Apache 2.0 license
- **Languages supported**: Go, Java, Node.js, Python, Ruby, .NET, PHP, Rust, C/C++, Swift, Dart, Elixir, Julia, R
- **Data sources**: GitHub Advisory Database, GitLab Advisory Database, OSV, Red Hat Security Data, AlmaLinux, Rocky Linux
- **Output formats**: Table, JSON, CycloneDX, SPDX, SARIF, JUnit

Trivy's key advantage is **breadth** — one tool scans dependencies, container images, IaC files, Kubernetes clusters, and AWS/GCP/Azure configurations.

### Grype

[Grype](https://github.com/anchore/grype) by Anchore is a vulnerability scanner for container images and filesystems, with strong SBOM integration. It pairs naturally with Syft (Anchore's SBOM generator) to create a full supply-chain security pipeline.

- **GitHub**: `anchore/grype` — 12,095 stars, Apache 2.0 license
- **Languages supported**: Go, Java, Node.js, Python, Ruby, .NET, PHP, Rust, C/C++, Swift, Dart, Haskell, Erlang
- **Data sources**: Anchore vulnerability feeds (aggregated from NVD, GitHub Advisories, and distro-specific sources)
- **Output formats**: Table, JSON, CycloneDX, SARIF, templated text

Grype's strength is its **SBOM-first workflow**: generate an SBOM with Syft, then scan it with Grype for vulnerabilities. This creates a clean audit trail.

## Feature Comparison

| Feature | OWASP Dependency-Check | Trivy | Grype |
|---|---|---|---|
| **Primary focus** | Dependency scanning only | Full-spectrum security scanning | Container + dependency scanning |
| **Java/Maven** | ✅ Excellent (CPE matching) | ✅ Good | ✅ Good |
| **npm/Node.js** | ✅ Via RetireJS + Node Audit | ✅ Via GitHub Advisories | ✅ Via GitHub Advisories |
| **Python/pip** | ✅ Via OSS Index | ✅ Via OSV + GitHub Advisories | ✅ Via OSV + GitHub Advisories |
| **.NET/NuGet** | ✅ Good | ✅ Good | ✅ Good |
| **Go modules** | ✅ Basic | ✅ Excellent | ✅ Excellent |
| **Ruby/Gem** | ✅ Via OSS Index | ✅ Good | ✅ Good |
| **PHP/Composer** | ✅ Via OSS Index | ✅ Via OSV | ✅ Via OSV |
| **Rust/Cargo** | ✅ Via OSV | ✅ Via OSV | ✅ Excellent |
| **C/C++** | ❌ | ✅ Via OSV | ✅ Via Conan/vcpkg |
| **Container scanning** | ❌ | ✅ Excellent | ✅ Excellent |
| **IaC scanning** | ❌ | ✅ (Terraform, Dockerfile, K8s) | ❌ |
| **SBOM generation** | ❌ | ✅ (CycloneDX, SPDX) | ❌ (consumes SBOM from Syft) |
| **SBOM consumption** | ❌ | ✅ | ✅ (CycloneDX, SPDX) |
| **False positive rate** | Higher (CPE-based matching) | Lower | Lower |
| **Scan speed** | Slow (database downloads) | Fast | Fast |
| **NVD API support** | ✅ Direct | ❌ (uses aggregated feeds) | ❌ (uses Anchore feeds) |
| **Offline scanning** | ⚠️ Requires cached NVD data | ✅ Full offline mode | ✅ Full offline mode |
| **CI/CD plugins** | Maven, Gradle, Jenkins, Azure DevOps | GitHub Action, GitLab CI, CircleCI | GitHub Action, Jenkins |
| **Report formats** | HTML, XML, JSON, CSV, SARIF | Table, JSON, SARIF, CycloneDX | Table, JSON, SARIF, CycloneDX |
| **Stars** | 7,525 | 34,729 | 12,095 |
| **Last updated** | April 2026 | April 2026 | April 2026 |

## Installation and Setup

### Docker Installation — OWASP Dependency-Check

OWASP Dependency-Check provides an official Docker image. The scanner downloads the NVD database on first run (this can take several minutes), then scans your project directory:

```bash
# Create a local directory for the NVD data cache (speeds up subsequent scans)
mkdir -p ~/.owasp-dependency-check/data

# Run a scan against your project directory
docker run --rm \
  -v ~/.owasp-dependency-check/data:/usr/share/dependency-check/data \
  -v $(pwd):/src:ro \
  owasp/dependency-check:latest \
  --scan /src \
  --format ALL \
  --out /src/dependency-check-reports \
  --project "my-project"
```

The `--format ALL` flag generates HTML, XML, JSON, and CSV reports. Reports are written to `dependency-check-reports/` in your project directory.

**Docker Compose** — for a persistent scanning service:

```yaml
services:
  dependency-check:
    image: owasp/dependency-check:latest
    volumes:
      - ./ncdata:/usr/share/dependency-check/data
      - ./project:/src:ro
      - ./reports:/src/reports
    command: >
      --scan /src
      --format JSON
      --out /src/reports
      --project "my-project"
      --enableRetired
    restart: "no"
```

### Docker Installation — Trivy

Trivy's Docker image is lightweight and includes pre-cached vulnerability databases:

```bash
# Scan a local project directory for dependency vulnerabilities
docker run --rm \
  -v $(pwd):/src:ro \
  aquasec/trivy:latest \
  fs /src \
  --scanners vuln \
  --severity HIGH,CRITICAL \
  --format table
```

The `--scanners vuln` flag limits Trivy to dependency vulnerability scanning (excluding misconfiguration and secret scanning). Add `--skip-dirs node_modules --skip-dirs .cache` to speed up scans on large projects.

**Docker Compose** — Trivy as a CI scanning service:

```yaml
services:
  trivy-scan:
    image: aquasec/trivy:latest
    volumes:
      - ./project:/src:ro
      - ./reports:/reports
      - trivy-cache:/root/.cache/trivy
    command: >
      fs /src
      --scanners vuln
      --severity HIGH,CRITICAL
      --format json
      --output /reports/trivy-results.json
    restart: "no"

volumes:
  trivy-cache:
```

### Docker Installation — Grype

Grype's Docker image provides fast filesystem and SBOM scanning:

```bash
# Scan a local project directory
docker run --rm \
  -v $(pwd):/src:ro \
  anchore/grype:latest \
  dir:/src \
  --scope all-layers \
  --only-fixed
```

The `--scope all-layers` flag ensures Grype scans all filesystem layers, catching dependencies installed in Docker build stages. The `--only-fixed` flag filters to show only vulnerabilities with available fixes.

**Docker Compose** — Grype with Syft for SBOM-first scanning:

```yaml
services:
  syft:
    image: anchore/syft:latest
    volumes:
      - ./project:/src:ro
      - ./sbom:/output
    command: >
      /src
      -o cyclonedx-json
      --file /output/sbom.json
    restart: "no"

  grype:
    image: anchore/grype:latest
    volumes:
      - ./sbom:/sbom:ro
      - ./reports:/reports
    command: >
      sbom:/sbom/sbom.json
      --output json
      --file /reports/grype-results.json
    depends_on:
      - syft
    restart: "no"
```

This two-service pipeline first generates a CycloneDX SBOM with Syft, then scans it with Grype — creating a reproducible, auditable scan record.

## CI/CD Integration

### GitHub Actions — Trivy

```yaml
name: Dependency Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  trivy-dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy dependency scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scanners: 'vuln'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - name: Upload results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

### Jenkins Pipeline — OWASP Dependency-Check

```groovy
pipeline {
    agent any
    stages {
        stage('Dependency Check') {
            steps {
                sh '''
                    docker run --rm \
                        -v ${WORKSPACE}/dc-data:/usr/share/dependency-check/data \
                        -v ${WORKSPACE}:/src:ro \
                        owasp/dependency-check:latest \
                        --scan /src \
                        --format JSON \
                        --out /src/reports \
                        --project "${JOB_NAME}" \
                        --failOnCVSS 7
                '''
            }
            post {
                always {
                    dependencyCheckPublisher pattern: 'reports/dependency-check-report.json'
                }
            }
        }
    }
}
```

### GitLab CI — Grype

```yaml
dependency-scan:
  image: anchore/grype:latest
  script:
    - grype dir:. --scope all-layers --fail-on high --output json > grype-results.json
  artifacts:
    reports:
      dependency_scanning: grype-results.json
    when: always
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

## Performance Comparison

Scan speed matters in CI/CD pipelines where every minute adds to feedback time. Here's how the tools compare on a typical Java + Node.js project (~500 dependencies):

| Metric | OWASP Dependency-Check | Trivy | Grype |
|---|---|---|---|
| **First-run time** | 5-10 min (NVD download) | ~30 sec | ~20 sec |
| **Subsequent runs** | 2-4 min (cached NVD) | ~15 sec | ~10 sec |
| **Database size** | ~1-2 GB (NVD + mirrors) | ~200 MB (embedded feeds) | ~150 MB (Anchore feeds) |
| **Memory usage** | 1-2 GB (Java runtime) | ~100 MB | ~80 MB |
| **False positives** | Moderate-High (CPE matching) | Low | Low |

**Key insight**: OWASP Dependency-Check's NVD database download is the biggest bottleneck on first run. Trivy and Grype embed their vulnerability feeds in the Docker image, making them significantly faster for CI/CD pipelines.

## When to Use Each Tool

### Choose OWASP Dependency-Check when:

- You need **deep Java ecosystem coverage** — its CPE-based matching catches vulnerabilities that advisory-based scanners miss
- Your compliance framework **requires NVD-based reporting** — Dependency-Check maps directly to NVD CVEs
- You want **build tool integration** (Maven plugin, Gradle plugin, Ant task) — it has the most mature plugin ecosystem
- You need **SonarQube integration** — the official Dependency-Check Sonar plugin feeds results directly into quality gates

### Choose Trivy when:

- You want **one tool for everything** — dependencies, containers, IaC, Kubernetes, and cloud configs
- **Scan speed is critical** — Trivy is the fastest of the three for most project types
- You need **SARIF output** for GitHub Code Scanning — Trivy's SARIF integration is the most complete
- You want **offline scanning** without manual database management

### Choose Grype when:

- You already use **Syft for SBOM generation** — the Syft + Grype pipeline is seamless
- You need **SBOM-first vulnerability management** — scan CycloneDX/SPDX SBOMs directly
- You want **lightweight scanning** — Grype has the smallest memory footprint
- You use **Anchore Engine** for container policy enforcement — Grype feeds directly into Anchore's policy engine

## For related reading

If you're building a comprehensive self-hosted security pipeline, check out our guides on [SBOM generation with Dependency-Track and Syft](../self-hosted-sbom-dependency-tracking-dependency-track-syft-cyclonedx-guide-2026/) for upstream supply-chain visibility, the [Python dependency scanning guide covering pip-audit, Safety, and OSV-Scanner](../2026-04-27-pip-audit-vs-safety-vs-osv-scanner-self-hosted-dependency-vulnerability-scanning-guide/) for language-specific tools, and our [code quality scanning comparison with SonarQube and Semgrep](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/) for static analysis integration.

## FAQ

### Which dependency scanner has the lowest false positive rate?

Trivy and Grype both use advisory-based databases (GitHub Advisories, OSV) which tend to produce fewer false positives than OWASP Dependency-Check's CPE-based matching. CPE matching can misidentify libraries when version strings don't align perfectly with NVD entries. For production CI/CD pipelines where false positives cause alert fatigue, Trivy or Grype are better choices.

### Can these tools scan transitive (indirect) dependencies?

Yes. All three tools resolve and scan transitive dependencies. OWASP Dependency-Check uses Maven/Gradle resolution for Java projects. Trivy and Grype parse lock files (package-lock.json, poetry.lock, Gemfile.lock, go.sum) to find the complete dependency tree including transitive packages. Grype's `--scope all-layers` flag is particularly useful for finding dependencies installed during Docker build stages.

### Do these tools require internet access to work?

OWASP Dependency-Check needs periodic internet access to update its NVD database cache. Trivy and Grype can run fully offline after initial setup — their Docker images include embedded vulnerability feeds. For air-gapped environments, you can download Trivy's vulnerability database separately (`trivy image --download-db-only`) and mount it into the container.

### Which tool supports the most programming languages?

Trivy supports the widest range of languages (15+ ecosystems including C/C++, Julia, Elixir, and Dart). Grype supports 13+ ecosystems. OWASP Dependency-Check covers 9 primary ecosystems but has the deepest Java integration via its native Maven, Gradle, and Ant plugins.

### How do I enforce a build failure when critical vulnerabilities are found?

All three tools support exit-code-based failure modes. OWASP Dependency-Check uses `--failOnCVSS 7` to fail on HIGH+ severity. Trivy uses `--exit-code 1 --severity CRITICAL,HIGH`. Grype uses `--fail-on high`. In CI/CD pipelines, these flags cause the build to fail when vulnerabilities above your threshold are detected, preventing vulnerable code from reaching production.

### Can I use these tools with private artifact repositories (Nexus, Artifactory)?

Yes. OWASP Dependency-Check can be configured with `--centralUrl` and `--nexusUrl` flags to authenticate against private Maven repositories. Trivy supports private registries via `--registry-username` and `--registry-password` flags. Grype can scan packages from private repositories when provided with appropriate credentials through its `grype config` configuration file.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OWASP Dependency-Check vs Trivy vs Grype: Best Self-Hosted Dependency Scanning 2026",
  "description": "Compare OWASP Dependency-Check, Trivy, and Grype for self-hosted dependency vulnerability scanning. Complete guide with Docker setups, configuration examples, and feature comparison for multi-language projects.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
