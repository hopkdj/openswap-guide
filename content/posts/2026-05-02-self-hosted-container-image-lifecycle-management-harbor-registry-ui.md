---
title: "Self-Hosted Container Image Lifecycle Management — Harbor, Registry UI & Image Promotion Tools"
date: 2026-05-02
draft: false
tags:
  - containers
  - docker
  - devops
  - security
  - self-hosted
---

Running a container registry is only the beginning. As your container footprint grows, you need tools to manage the full image lifecycle — from build and scan, through staging and promotion, to production deployment and garbage collection. Self-hosted container image lifecycle management platforms provide the governance, security, and automation that bare registries lack.

In this guide, we compare three approaches: **Harbor** (the enterprise-grade CNCF registry platform), **Registry UI tools** (lightweight management layers on top of Docker Distribution), and **Image Promotion Pipeline tools** (automated image scanning, signing, and deployment workflows).

## Why Image Lifecycle Management Matters

A basic Docker registry stores images. A lifecycle management platform answers critical operational questions:

- Which images have known vulnerabilities?
- Has this image been scanned and approved for production?
- How do I promote an image from staging to production?
- When should I delete old image tags to save storage?
- Are all images cryptographically signed?
- Which registry holds which image across multiple clusters?

## Comparison Table

| Feature | Harbor | Registry UI | Image Promotion Pipeline |
|---------|--------|-------------|-------------------------|
| **GitHub Stars** | 22,000+ | 100–800 | 500–2,000 |
| **Image Scanning** | Trivy, Clair | Via external tools | Trivy, Grype, Snyk |
| **Image Signing** | Cosign, Notary | No | Cosign, Notation |
| **Tag Retention** | Built-in policies | No | Custom rules |
| **Replication** | Multi-registry sync | No | Pipeline-based |
| **RBAC** | Project-based | Basic | Pipeline-based |
| **Vulnerability DB** | Automatic updates | External | Your choice |
| **Docker Support** | Yes (official) | Yes | Yes |
| **Best For** | Enterprise registry | Simple web UI | CI/CD-integrated workflows |

## Harbor — Enterprise Container Registry Platform

Harbor is the most feature-rich open-source container registry platform, graduated from the CNCF. It extends the Docker Distribution registry with enterprise capabilities including vulnerability scanning, image signing, replication, RBAC, and tag retention policies.

### Key Features

- **Vulnerability scanning**: Integrated Trivy and Clair scanners with automatic CVE database updates
- **Image signing**: Cosign and Notary v2 support for supply chain security
- **Tag retention**: Automatic cleanup of old images based on configurable policies
- **Replication**: Push/pull replication between Harbor instances and external registries
- **RBAC**: Project-based access control with LDAP/AD integration
- **Audit logging**: Complete audit trail of all registry operations
- **Image promotion**: Promote images between projects (dev → staging → prod) with approval gates

### Docker Compose Deployment

```yaml
# Harbor uses its own installer which generates docker-compose.yml
# Download and configure:
# wget https://github.com/goharbor/harbor/releases/latest/download/harbor-offline-installer-latest.tgz
# tar xzvf harbor-offline-installer-latest.tgz
# cd harbor && cp harbor.yml.tmpl harbor.yml

# Edit harbor.yml with your hostname and certificate paths:
# hostname: registry.example.com
# https:
#   port: 443
#   certificate: /etc/harbor/ssl/server.crt
#   private_key: /etc/harbor/ssl/server.key

# Install:
# ./install.sh
```

Key configuration in `harbor.yml`:

```yaml
hostname: registry.example.com

http:
  port: 80

https:
  port: 443
  certificate: /etc/harbor/ssl/server.crt
  private_key: /etc/harbor/ssl/server.key

harbor_admin_password: Harbor12345

database:
  password: your-db-password
  max_idle_conns: 100
  max_open_conns: 900

data_volume: /data

trivy:
  ignore_unfixed: false
  skip_update: false
  offline_scan: false
  insecure: false

jobservice:
  max_job_workers: 10

notification:
  webhook_job_max_retry: 10

log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200M
    location: /var/log/harbor
```

### Tag Retention Policy

Harbor's retention policies automatically clean up old images:

```yaml
# Via Harbor API — keep only the 5 most recent tags per repository
curl -X POST "https://registry.example.com/api/v2/projects/1/retentions" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "or",
    "rules": [
      {
        "disabled": false,
        "action": "retain",
        "params": {
          "n_latest": 5
        },
        "tag_selectors": [
          {
            "kind": "doublestar",
            "decoration": "matches",
            "pattern": "**"
          }
        ],
        "scope_selectors": {
          "repository": [
            {
              "kind": "doublestar",
              "decoration": "repoMatches",
              "pattern": "**"
            }
          ]
        }
      }
    ],
    "trigger": {
      "kind": "Schedule",
      "settings": {
        "cron": "0 0 2 * * *"
      }
    }
  }'
```

### GitHub Stats

| Metric | Value |
|--------|-------|
| Stars | 22,000+ |
| CNCF Status | Graduated |
| Last Updated | Active (2026) |

## Lightweight Registry UI Tools

For teams running Docker Distribution (registry:2) or Docker Registry who need a simple web interface without Harbor's full stack, lightweight UI tools provide a middle ground:

| Tool | Features | Docker | Stars |
|------|----------|--------|-------|
| **docker-registry-frontend** | Browse, search, delete images | Yes | 1,500+ |
| **Portus** | SUSE's registry UI with security | Yes | 1,900+ |
| **Registry UI** | Modern UI, tag management | Yes | 300+ |
| **Reg** | CLI + API tool for registry management | Binary | 800+ |

### Registry UI Deployment

```yaml
version: '3'
services:
  registry-ui:
    image: joxit/docker-registry-ui:latest
    ports:
      - "8080:80"
    environment:
      - REGISTRY_URL=https://registry.example.com
      - DELETE_IMAGES=true
      - REGISTRY_TITLE="My Registry"
    restart: unless-stopped
```

## Image Promotion Pipeline — Automated Workflows

For teams that want lifecycle management integrated directly into CI/CD pipelines, image promotion tools automate the flow from build to production:

### Cosign Image Signing Pipeline

```bash
#!/bin/bash
# Image promotion pipeline: build → scan → sign → push

REGISTRY="registry.example.com"
IMAGE="myapp"
TAG="${CI_COMMIT_SHA}"

# Step 1: Build
docker build -t "${REGISTRY}/${IMAGE}:${TAG}" .

# Step 2: Scan with Trivy
trivy image --severity CRITICAL,HIGH --exit-code 1 \
  "${REGISTRY}/${IMAGE}:${TAG}"

# Step 3: Sign with Cosign
cosign sign --key env://COSIGN_PRIVATE_KEY \
  "${REGISTRY}/${IMAGE}:${TAG}"

# Step 4: Promote to production
cosign copy "${REGISTRY}/${IMAGE}:${TAG}" \
  "${REGISTRY}/${IMAGE}:latest"

# Step 5: Verify before deployment
cosign verify --key env://COSIGN_PUBLIC_KEY \
  "${REGISTRY}/${IMAGE}:latest"
```

### Automated Garbage Collection

```yaml
# Kubernetes CronJob for registry cleanup
apiVersion: batch/v1
kind: CronJob
metadata:
  name: registry-gc
spec:
  schedule: "0 3 * * 0"  # Weekly at 3 AM Sunday
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: registry-gc
            image: distribution/registry:2.8
            command:
            - /bin/registry
            - garbage-collect
            - /etc/docker/registry/config.yml
            volumeMounts:
            - name: registry-storage
              mountPath: /var/lib/registry
          restartPolicy: OnFailure
          volumes:
          - name: registry-storage
            persistentVolumeClaim:
              claimName: registry-pvc
```

## When to Choose Each Approach

| Scenario | Recommended |
|----------|-------------|
| Enterprise with compliance requirements | Harbor |
| Need vulnerability scanning out of the box | Harbor |
| Simple web UI for existing registry | Registry UI |
| CI/CD-integrated image promotion | Cosign + pipeline scripts |
| Multi-registry replication | Harbor |
| Minimal overhead, small team | Docker Registry + Registry UI |
| Supply chain security (signing) | Harbor + Cosign |

## For Related Reading

For a complete container management strategy, see our related guides:

- [Container Registry Comparison](../harbor-vs-distribution-vs-zot-self-hosted-container-registry/) — Harbor vs Distribution vs Zot
- [Container Security Scanning](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-cont/) — Docker Bench vs Trivy vs Checkov
- [Container Orchestration](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernet/) — Rancher vs Kubespray vs Kind


## Container Registry Governance Best Practices

Managing container images at scale requires more than just storing them. These governance practices help teams maintain security, compliance, and operational efficiency across their container infrastructure.

**Implement mandatory vulnerability scanning**: Configure your registry to reject images that exceed a defined vulnerability threshold. Harbor supports this through webhook-based policies that block image pushes when scanning detects critical CVEs. This prevents vulnerable images from entering your deployment pipeline in the first place.

**Establish image promotion workflows**: Define clear stages for image lifecycle: development builds go to a dev project, approved builds are promoted to staging, and only signed, scanned images reach production. Harbor's project-based RBAC supports this model by restricting who can push to production projects.

**Set retention policies per project**: Different projects have different retention needs. Development projects might keep only the last 10 tags, while production images should be retained indefinitely for rollback capability. Configure retention policies at the project level in Harbor to automate cleanup without manual intervention.

**Enable audit logging for compliance**: Every image pull, push, delete, and scan result should be logged. Harbor's audit log captures all registry operations with user attribution, enabling compliance reporting and security investigations. Forward these logs to your centralized logging system for long-term retention.

**Sign all production images**: Implement image signing with Cosign as a mandatory step in your CI/CD pipeline. Unsigned images should be blocked from production deployment by your Kubernetes admission controller or Harbor's content trust policy.

For container security scanning, see our [Docker Bench vs Trivy vs Checkov comparison](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-cont/).

## FAQ

### What is container image lifecycle management?

Container image lifecycle management covers the entire journey of a container image from creation to deletion. This includes building images, scanning for vulnerabilities, signing for integrity verification, promoting through environments (dev → staging → production), managing tag retention, and garbage collecting unused images to reclaim storage space.

### How does Harbor differ from Docker Registry?

Docker Registry (distribution/distribution) is the basic open-source registry for storing and serving container images. Harbor extends Docker Registry with enterprise features: vulnerability scanning, image signing, RBAC, replication, tag retention policies, audit logging, and a web UI. Harbor uses Docker Registry as its storage backend but adds a complete management layer on top.

### Can Harbor automatically delete old container images?

Yes, Harbor has built-in tag retention policies that automatically clean up images based on configurable rules. You can keep the N most recent tags, retain images matching specific patterns, or set schedules for automatic cleanup. This is essential for preventing registry storage from growing indefinitely.

### What vulnerability scanners does Harbor support?

Harbor supports Trivy (default, recommended) and Clair for vulnerability scanning. Trivy is maintained by Aqua Security and provides comprehensive scanning against multiple vulnerability databases. Harbor automatically updates the vulnerability database and scans images on push or on a schedule.

### How do I sign container images for supply chain security?

Use Cosign (from Sigstore) or Notary v2. Cosign is the simpler option — it signs images using public-key cryptography and stores signatures as OCI artifacts alongside the image. Harbor supports both Cosign and Notary natively. The typical workflow is: build → scan → sign → push → verify before deployment.

### Is Harbor production-ready for large registries?

Yes, Harbor is a CNCF-graduated project used by many large organizations. It supports horizontal scaling, external databases (PostgreSQL), Redis caching, and S3-compatible storage backends for production deployments. The Harbor installer configures all components (registry, database, Redis, scanner, core API, jobservice) via Docker Compose or Helm for Kubernetes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Lifecycle Management — Harbor, Registry UI & Image Promotion Tools",
  "description": "Compare self-hosted container image lifecycle management solutions. Harbor, Registry UI tools, and automated image promotion pipelines for secure container governance.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
