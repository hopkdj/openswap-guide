---
title: "Self-Hosted SBOM Analysis: Dependency-Track vs ORT vs Syft 2026"
date: 2026-05-01
tags: ["sbom", "dependency-analysis", "security", "supply-chain", "dependency-track", "syft", "comparison", "guide"]
draft: false
description: "Compare self-hosted SBOM analysis platforms — OWASP Dependency-Track, OSS Review Toolkit, and Anchore Syft. Generate, analyze, and monitor software bills of materials with Docker configs."
---

Every modern application depends on hundreds of third-party packages. When a new vulnerability is disclosed, you need to know exactly which projects are affected. Software Bills of Materials (SBOMs) provide this inventory — a structured list of every component, its version, and its dependencies.

This guide compares three self-hosted SBOM analysis platforms: **OWASP Dependency-Track**, **OSS Review Toolkit (ORT)**, and **Anchore Syft**. We cover how each tool generates and analyzes SBOMs, provide Docker Compose deployment configs, and help you choose the right tool for your security workflow.

## What Is an SBOM and Why Does It Matter?

An SBOM is a formal record of all components used in a software product. Think of it as an ingredient list for your application. When a new CVE is published, an SBOM lets you instantly answer: "Are we using this vulnerable library?"

The two dominant SBOM formats are:

- **CycloneDX** — lightweight, focused on security and license compliance. Supported by OWASP tools.
- **SPDX** — broader scope, includes licensing and provenance data. Backed by the Linux Foundation.

Having an SBOM is also becoming a regulatory requirement. Executive Order 14028 in the US mandates SBOMs for all software sold to the federal government. The EU Cyber Resilience Act has similar requirements.

## OWASP Dependency-Track

Dependency-Track is an intelligent Component Analysis platform that ingests SBOMs, correlates components with known vulnerabilities from the National Vulnerability Database (NVD), GitHub Advisories, and other sources, and provides a web dashboard for tracking risk across your portfolio.

### Dependency-Track Docker Compose

```yaml
version: "3.8"
services:
  dtrack-apiserver:
    image: dependencytrack/apiserver:latest
    ports:
      - "8081:8080"
    environment:
      - ALPINE_DATABASE_MODE=external
      - ALPINE_DATABASE_URL=jdbc:postgresql://dtrack-postgres:5432/dtrack
      - ALPINE_DATABASE_USERNAME=dtrack
      - ALPINE_DATABASE_PASSWORD=changeme
      - ALPINE_DATABASE_DRIVER=org.postgresql.Driver
    depends_on:
      dtrack-postgres:
        condition: service_healthy
    volumes:
      - dtrack-data:/data
    networks:
      - sbom-net

  dtrack-frontend:
    image: dependencytrack/frontend:latest
    ports:
      - "8080:80"
    environment:
      - API_BASE_URL=http://localhost:8081
    depends_on:
      - dtrack-apiserver
    networks:
      - sbom-net

  dtrack-postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=dtrack
      - POSTGRES_USER=dtrack
      - POSTGRES_PASSWORD=changeme
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dtrack"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - sbom-net

volumes:
  dtrack-data:
  postgres-data:

networks:
  sbom-net:
    driver: bridge
```

Dependency-Track features:

| Feature | Details |
|---------|---------|
| SBOM formats | CycloneDX (JSON, XML, Protobuf) |
| Vulnerability sources | NVD, GitHub Advisories, OSV, VulnDB |
| Analysis engine | Real-time component matching against known CVEs |
| Portfolio management | Track multiple projects and versions |
| Policy engine | Define custom risk policies and violations |
| API | Full REST API for CI/CD integration |
| Docker Hub pulls | 27M+ (API server), 17M+ (frontend) |
| GitHub stars | 3,777 |

## OSS Review Toolkit (ORT)

ORT is a suite of tools for automating open source compliance checks. It scans your codebase, identifies dependencies, resolves license information, checks for known vulnerabilities, and produces detailed reports. ORT is language-agnostic and supports over 30 package managers.

### ORT Docker Compose

```yaml
version: "3.8"
services:
  ort:
    image: ghcr.io/oss-review-toolkit/ort:latest
    volumes:
      - ./project:/project:ro
      - ./ort-config:/etc/ort/config:ro
      - ./ort-output:/output
    entrypoint: ["ort"]
    # Run analyzer:
    # command: ["analyze", "-i", "/project", "-o", "/output/analyzer"]
    # Run scanner:
    # command: ["scan", "-i", "/output/analyzer/ort-analyzer-results.yml", "-o", "/output/scanner"]
    # Run evaluator:
    # command: ["evaluate", "-i", "/output/scanner/ort-scanner-results.yml", "-c", "/etc/ort/config/eval-rules.yml", "-o", "/output/evaluator"]

networks:
  default:
    driver: bridge
```

ORT features:

| Feature | Details |
|---------|---------|
| Language support | 30+ package managers (Maven, Gradle, npm, pip, Go, Cargo, etc.) |
| Analysis | Dependency resolution with transitive dependency tree |
| Scanning | License and copyright detection via ScanCode, Licensee |
| Evaluation | Rule-based compliance checking with customizable rule sets |
| Reporting | Static HTML, PDF, and CycloneDX reports |
| CI integration | Jenkins, GitLab CI, GitHub Actions pipelines |
| GitHub stars | 1,995 |

## Anchore Syft

Syft is a CLI tool for generating SBOMs from container images, filesystems, and archives. It detects packages across 20+ language ecosystems and outputs in CycloneDX, SPDX, and Syft's own JSON format. Syft is often paired with Grype for vulnerability scanning.

### Syft Docker Compose

```yaml
version: "3.8"
services:
  syft:
    image: anchore/syft:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./sbom-output:/output
    entrypoint: ["syft"]
    # Generate SBOM from container image:
    # command: ["myapp:latest", "-o", "cyclonedx-json=/output/sbom.json"]
    # Generate SBOM from filesystem:
    # command: ["dir:/app", "-o", "spdx-json=/output/sbom-spdx.json"]
    # Generate SBOM with all ecosystems:
    # command: ["myapp:latest", "-o", "cyclonedx-json=/output/sbom.json", "-o", "spdx-json=/output/sbom-spdx.json"]

networks:
  default:
    driver: bridge
```

Syft features:

| Feature | Details |
|---------|---------|
| Scan targets | Container images, filesystems, archives, SBOM files |
| Package ecosystems | 20+ (Alpine, Debian, Python, Java, JavaScript, Go, Rust, etc.) |
| Output formats | CycloneDX (JSON, XML), SPDX (tag-value, JSON, XML), Syft JSON |
| Integration | Pairs with Grype for vulnerability scanning |
| GitHub stars | 8,852 |
| Docker pulls | Widely used in CI/CD pipelines |

## Comparison: SBOM Analysis Tools

| Feature | Dependency-Track | ORT | Syft |
|---------|-----------------|-----|------|
| Primary role | SBOM management + vulnerability tracking | Full compliance audit suite | SBOM generation |
| SBOM ingestion | CycloneDX only | CycloneDX + SPDX (output) | CycloneDX + SPDX (output) |
| Vulnerability scanning | Yes (built-in, multiple sources) | Yes (via OSS Index, vulnerable code scanning) | No (pairs with Grype) |
| License compliance | Via policy engine | Yes (full license detection and evaluation) | Limited (package-level only) |
| Web dashboard | Yes (full UI) | No (CLI only, generates HTML reports) | No (CLI only) |
| Portfolio tracking | Yes (multiple projects/versions) | No (per-scan focus) | No |
| CI/CD integration | REST API for pipeline uploads | Native pipeline orchestrator | CLI for pipeline SBOM generation |
| Deployment | Docker Compose with Postgres | Docker container (stateless) | Docker container (stateless) |
| Best for | Ongoing SBOM management | One-time compliance audits | Fast SBOM generation in CI |

## When to Use Each Tool

**Use Dependency-Track** when you need a centralized platform to manage SBOMs across your entire organization. It ingests CycloneDX SBOMs from any source, continuously monitors for new vulnerabilities, and provides a web dashboard for risk assessment. It is ideal for security teams who need ongoing visibility into component risk.

**Use ORT** when you need comprehensive open source compliance auditing. ORT goes beyond SBOM generation — it resolves the full dependency tree, detects licenses and copyrights, evaluates them against your policies, and produces audit-ready reports. It is ideal for legal and compliance teams.

**Use Syft** when you need fast, reliable SBOM generation as part of your CI/CD pipeline. Syft scans container images and filesystems in seconds, outputs in multiple formats, and pairs naturally with Grype for vulnerability scanning. It is ideal for DevOps teams who want to embed SBOM generation into every build.

## Why Self-Host Your SBOM Pipeline?

Generating and managing SBOMs internally means your component inventory never leaves your infrastructure. Cloud-based SBOM services require you to upload your dependency lists to external servers — information that reveals your technology stack and potential attack surface.

Self-hosted tools keep this sensitive data under your control. You can correlate SBOM data with internal asset management, integrate with your existing vulnerability management workflow, and ensure compliance with data residency requirements. For organizations handling regulated workloads, self-hosted SBOM analysis is not optional — it is a security requirement.

For more on container security, see our [Kube Bench Vs Trivy Vs Kubescape Container Kube...](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/), and [Kyverno Vs Opa Gatekeeper Vs Trivy Operator Kub...](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/).
For vulnerability scanning guides, check our [Renovate Vs Dependabot Vs Updatecli Self Hosted...](../2026-04-19-renovate-vs-dependabot-vs-updatecli-self-hosted-dependency-automation-guide-2026/), and [Defectdojo Vs Greenbone Vs Faraday Self Hosted ...](../2026-04-20-defectdojo-vs-greenbone-vs-faraday-self-hosted-vulnerability-management-2026/).

## FAQ

### What is an SBOM and why do I need one?

An SBOM (Software Bill of Materials) is a structured inventory of all components in your software. It lists every library, framework, and dependency with its version. You need one to quickly identify which projects are affected when a new vulnerability is disclosed, to comply with regulatory requirements, and to manage open source license obligations.

### What is the difference between CycloneDX and SPDX?

CycloneDX is a lightweight SBOM format focused on security use cases — vulnerability tracking, exploitability assessment, and license compliance. SPDX is broader, covering licensing, provenance, and software supply chain data. CycloneDX is preferred for security workflows; SPDX is preferred for legal and licensing compliance.

### Can Dependency-Track scan for vulnerabilities automatically?

Yes. Dependency-Track continuously synchronizes with vulnerability databases including the NVD, GitHub Advisories, and OSV. When you upload a CycloneDX SBOM, it immediately correlates every component against these databases and flags any matches. It also monitors for new vulnerabilities and alerts you when a component in your portfolio becomes vulnerable.

### How does ORT differ from Syft?

ORT is a comprehensive compliance audit suite — it analyzes dependencies, detects licenses and copyrights, evaluates them against custom rules, and generates audit reports. Syft is focused on SBOM generation — it quickly scans container images and filesystems to produce CycloneDX or SPDX documents. ORT is broader; Syft is faster and more focused.

### Can I use Syft with Docker Compose?

Yes. Syft runs as a Docker container and can access the Docker daemon socket to scan images on your host. Mount the Docker socket as a volume and run Syft commands through docker compose exec or as a one-off container. The output SBOM can be written to a shared volume for downstream processing.

### Do I need both SBOM generation and SBOM management tools?

In practice, yes. Syft generates the SBOM (the ingredient list). Dependency-Track manages it over time (tracking which ingredients become recalled). Generate SBOMs at build time with Syft, upload them to Dependency-Track, and let Dependency-Track continuously monitor for new vulnerabilities. This combination covers the full lifecycle.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SBOM Analysis: Dependency-Track vs ORT vs Syft 2026",
  "description": "Compare self-hosted SBOM analysis platforms — OWASP Dependency-Track, OSS Review Toolkit, and Anchore Syft. Generate, analyze, and monitor software bills of materials with Docker configs.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
