---
title: "Self-Hosted API Breaking Change Detection: oasdiff vs openapi-diff vs Azure API Diff"
date: "2026-05-16"
tags: ["api", "developer-tools", "ci-cd", "openapi"]
draft: false
---

When managing REST APIs across multiple microservices or teams, breaking changes can silently cascade through your infrastructure and break consumer applications before you even notice. Self-hosted API breaking change detection tools compare OpenAPI specifications between versions and flag incompatible modifications — removed endpoints, changed response types, new required parameters, and deprecated fields — before they reach production.

In this guide, we compare three leading open-source tools for detecting API breaking changes: **oasdiff** (originally from Tufin), **OpenAPITools/openapi-diff**, and **Azure/openapi-diff**. Each offers a different approach to spec comparison, CI/CD integration, and change classification, making them suitable for different stages of the API development lifecycle.

## Why API Breaking Change Detection Matters

API contracts are the glue between services in modern architectures. A single breaking change — removing a required field, changing a response schema from integer to string, or deleting an endpoint entirely — can bring down dependent services, break mobile app clients, and trigger cascading failures across your platform.

Traditional version control systems like Git detect textual differences but cannot distinguish between breaking and non-breaking changes. Adding a new optional endpoint is safe; removing an existing one is not. Breaking change detection tools parse OpenAPI specifications semantically and classify each modification according to its impact on API consumers.

For teams practicing API-first development, integrating breaking change detection into the CI/CD pipeline provides an automated safety net. Specs are compared on every pull request, and builds fail when incompatible changes are introduced, forcing developers to either bump the API version or reconsider the modification.

If you are building a complete API governance pipeline, see our [API lifecycle management guide](../2026-04-26-self-hosted-api-lifecycle-management-kong-apisix-tyk-gravitee-krakend-guide/) and [API specification validation tools](../self-hosted-api-schema-validation-governance-spectral-prism-dredd-guide-2026/) for complementary tooling.

## oasdiff

**Repository**: [oasdiff/oasdiff](https://github.com/oasdiff/oasdiff) · **Stars**: 1,196+ · **Language**: Go

oasdiff is a fast, lightweight CLI tool written in Go that compares two OpenAPI 3.x specifications and produces a detailed changelog. Originally developed by Tufin for internal API management, it was open-sourced and quickly gained adoption due to its speed and comprehensive breaking change detection rules.

### Key Features

- **Comprehensive breaking change detection**: Identifies 50+ types of breaking changes including removed paths, changed operation methods, modified response schemas, new required parameters, and tightened constraints
- **Non-breaking change classification**: Distinguishes between additive changes (new optional fields, new endpoints) and destructive changes
- **JSON and text output**: Machine-readable JSON output for CI/CD integration alongside human-readable text summaries
- **GitHub Action**: Official `oasdiff/oasdiff-action` for seamless PR-level API diff checking
- **Semantic versioning suggestions**: Recommends version bump types (major, minor, patch) based on detected changes

### Docker Compose Deployment

oasdiff is primarily a CLI tool, but you can containerize it for CI/CD pipeline integration:

```yaml
version: "3.8"
services:
  oasdiff:
    image: ghcr.io/oasdiff/oasdiff:latest
    volumes:
      - ./specs:/specs:ro
    entrypoint: ["/bin/sh", "-c"]
    command: |
      oasdiff breaking /specs/v1.yaml /specs/v2.yaml --fail-on ERR
```

For a persistent service that watches a Git repository for spec changes:

```yaml
version: "3.8"
services:
  api-diff-watcher:
    image: alpine/git:latest
    volumes:
      - ./specs:/specs
      - ./scripts:/scripts:ro
    command: |
      sh -c "while true; do
        git pull origin main
        oasdiff breaking /specs/main.yaml /specs/branch.yaml --format json > /results/diff.json
        sleep 60
      done"
```

### CI/CD Integration

In GitHub Actions, oasdiff runs as a PR check that fails the build when breaking changes are detected:

```yaml
- name: Check API Breaking Changes
  uses: oasdiff/oasdiff-action@main
  with:
    base: "main"
    revision: "${{ github.head_ref }}"
    fail-on: "ERR"
    format: "yaml"
```

## OpenAPITools/openapi-diff

**Repository**: [OpenAPITools/openapi-diff](https://github.com/OpenAPITools/openapi-diff) · **Stars**: 1,077+ · **Language**: Java

OpenAPITools/openapi-diff is a Java-based library and CLI tool maintained by the OpenAPI Tools community. It provides deep semantic analysis of OpenAPI specifications, with a focus on detailed change classification and HTML report generation.

### Key Features

- **Rich HTML reports**: Generates visual diff reports with color-coded change indicators (green for additions, red for removals, yellow for modifications)
- **Maven and Gradle plugins**: Native integration with Java build systems for automated spec validation during compilation
- **Three-way comparison**: Supports comparing base, old, and new versions simultaneously to track evolution over time
- **Backward compatibility modes**: Configurable strictness levels for breaking change thresholds
- **Swagger 2.0 and OpenAPI 3.x support**: Handles both legacy and modern specification formats

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  openapi-diff:
    image: openapitools/openapi-diff:latest
    volumes:
      - ./specs:/specs:ro
      - ./reports:/reports
    command: >
      /specs/v1.yaml
      /specs/v2.yaml
      --html /reports/diff.html
      --markdown /reports/diff.md
```

For a web-accessible report server:

```yaml
version: "3.8"
services:
  openapi-diff:
    image: openapitools/openapi-diff:latest
    volumes:
      - ./specs:/specs:ro
      - ./reports:/reports
    command: /specs/v1.yaml /specs/v2.yaml --html /reports/diff.html

  report-server:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./reports:/usr/share/nginx/html:ro
```

### Maven Integration

```xml
<plugin>
    <groupId>org.openapitools</groupId>
    <artifactId>openapi-diff-maven</artifactId>
    <version>2.1.0</version>
    <configuration>
        <oldSpec>src/main/resources/openapi-v1.yaml</oldSpec>
        <newSpec>src/main/resources/openapi-v2.yaml</newSpec>
        <failOnIncompatible>true</failOnIncompatible>
    </configuration>
</plugin>
```

## Azure/openapi-diff

**Repository**: [Azure/openapi-diff](https://github.com/Azure/openapi-diff) · **Stars**: 286+ · **Language**: TypeScript/Node.js

Azure/openapi-diff is the diffing engine used internally by Microsoft Azure for validating ARM (Azure Resource Manager) API specifications. It focuses on enterprise-grade API governance with rule-based breaking change detection and policy enforcement.

### Key Features

- **Rule-based validation**: Customizable ruleset for defining what constitutes a breaking change in your organization
- **Azure ARM API support**: Specialized handling for Azure Resource Manager specification patterns
- **Pipeline integration**: Designed for Azure DevOps Pipelines with native task support
- **Error categorization**: Classifies changes as errors (breaking), warnings (potentially breaking), and info (non-breaking)
- **Policy enforcement**: Integrates with API governance frameworks to enforce organizational standards

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  azure-api-diff:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ./specs:/specs:ro
      - ./scripts:/scripts:ro
    command: >
      sh -c "npm install -g @azure/openapi-diff &&
      openapi-diff /specs/v1.yaml /specs/v2.yaml
      --json /specs/diff-result.json"
```

For an automated pipeline runner:

```yaml
version: "3.8"
services:
  api-diff-pipeline:
    image: node:18-alpine
    volumes:
      - ./specs:/specs
      - ./results:/results
    environment:
      - BASE_SPEC=/specs/stable.yaml
      - TARGET_SPEC=/specs/candidate.yaml
    command: >
      sh -c "npm install -g @azure/openapi-diff &&
      openapi-diff $BASE_SPEC $TARGET_SPEC
      --text /results/diff.txt
      --json /results/diff.json --html /results/diff.html"
```

## Comparison Table

| Feature | oasdiff | openapi-diff | Azure/openapi-diff |
|---------|---------|-------------|-------------------|
| **Language** | Go | Java | TypeScript/Node.js |
| **Stars** | 1,196+ | 1,077+ | 286+ |
| **OpenAPI 3.x** | Yes | Yes | Yes |
| **Swagger 2.0** | No | Yes | Partial |
| **HTML Reports** | No | Yes | Yes |
| **JSON Output** | Yes | Yes | Yes |
| **GitHub Action** | Yes (official) | Community | Community |
| **Maven Plugin** | No | Yes | No |
| **Custom Rules** | Limited | Yes | Yes |
| **CI/CD Integration** | Excellent | Good | Good (Azure DevOps) |
| **Docker Image** | GHCR | Docker Hub | NPM package |
| **Speed** | Very fast (Go) | Moderate (JVM) | Moderate (Node.js) |
| **Best For** | CI/CD pipelines | Enterprise reporting | Azure ecosystems |

## Choosing the Right Tool

**Choose oasdiff if** you need fast, reliable breaking change detection in CI/CD pipelines. Its Go implementation means near-instant comparison times, and the official GitHub Action makes it the easiest to integrate into PR workflows. It is the best choice for teams that prioritize speed and automation over visual reporting.

**Choose OpenAPITools/openapi-diff if** you need rich HTML reports and Maven/Gradle integration. The visual diff output is excellent for stakeholder reviews and documentation. It is ideal for Java-based projects and organizations that require detailed, human-readable change reports alongside automated checks.

**Choose Azure/openapi-diff if** you operate within the Azure ecosystem or need customizable rule-based validation. Its policy enforcement capabilities make it suitable for enterprise API governance programs where different teams may have different breaking change thresholds. For API schema validation beyond diffing, check our [API schema validation guide](../self-hosted-api-schema-validation-governance-spectral-prism-dredd-guide-2026/).

## FAQ

### What is a breaking change in an API?

A breaking change is any modification to an API that causes existing client applications to fail. Common examples include removing an endpoint, deleting a required request parameter, changing a response field's data type, or adding a new required field to a response object. Non-breaking changes include adding new optional fields, new endpoints, or relaxing validation constraints.

### Can API breaking change detection replace versioning?

No. Breaking change detection is a safety net, not a replacement for API versioning. It helps you catch unintentional breaking changes before they reach production, but intentional breaking changes still require proper versioning (v1 → v2), deprecation notices, and migration guides for consumers.

### How do I integrate API diff checking into my CI/CD pipeline?

Most tools offer GitHub Actions, GitLab CI templates, or CLI interfaces that can be added as pipeline steps. The typical workflow is: store your OpenAPI spec in version control, configure the diff tool to compare the current branch's spec against the main branch, and fail the pipeline if breaking changes are detected without a version bump.

### Does oasdiff support OpenAPI 2.0 (Swagger)?

No, oasdiff only supports OpenAPI 3.x specifications. If you need Swagger 2.0 support, use OpenAPITools/openapi-diff, which handles both formats. You can also migrate your specs to OpenAPI 3.x using conversion tools like `swagger2openapi`.

### What happens when a breaking change is detected in production?

Breaking change detection tools operate pre-deployment — they catch issues before they reach production. If a breaking change does slip through to production, you need an API gateway (like Kong or APISIX) to handle versioning, deprecation headers, and backward compatibility routing. See our [API lifecycle management guide](../2026-04-26-self-hosted-api-lifecycle-management-kong-apisix-tyk-gravitee-krakend-guide/) for strategies on managing API versions in production.

### Can these tools detect semantic breaking changes?

Semantic breaking changes — where the API behavior changes but the specification does not — cannot be detected by spec comparison tools. Tools like oasdiff and openapi-diff only analyze the OpenAPI specification document. For behavioral testing, you need contract testing tools like Pact or consumer-driven testing frameworks.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted API Breaking Change Detection: oasdiff vs openapi-diff vs Azure API Diff",
  "description": "Compare oasdiff, openapi-diff, and Azure API Diff for detecting breaking changes in OpenAPI specifications. Self-hosted CI/CD integration with Docker.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
