---
title: "Self-Hosted Container Image Lifecycle: Harbor vs Distribution vs Zot (2026)"
date: "2026-05-10"
tags: ["containers", "registry", "lifecycle", "harbor", "image-management"]
draft: false
---

Container registries accumulate artifacts quickly. Every CI build pushes new image tags, every deployment promotes images between environments, and over time, your registry fills with outdated layers, unused tags, and orphaned manifests. Without lifecycle management, storage costs grow linearly and image discovery becomes impossible.

This guide compares the image lifecycle management capabilities of three open-source container registries — **Harbor** (CNCF graduated), **CNCF Distribution** (the Docker Registry), and **Zot** (OCI-native, CNCF sandbox) — focusing on how each handles retention policies, garbage collection, image promotion, and cleanup automation.

## Why Image Lifecycle Management Matters

A container registry without lifecycle policies is a ticking time bomb. Untagged images accumulate from failed builds, old versions persist long after deployments have moved on, and multi-architecture images multiply storage usage across every supported platform. The result is wasted storage, slower pull times, and compliance risk from unscanned or unpatched images sitting in production registries.

Proper lifecycle management automates retention (deleting images older than N days or beyond tag count limits), garbage collection (removing unreferenced layers), image promotion (moving verified images from staging to production), and cleanup scheduling (running these operations during maintenance windows without disrupting active deployments).

## Quick Comparison

| Feature | Harbor | Distribution | Zot |
|---------|--------|--------------|-----|
| **Retention Policies** | Yes (rule-based) | No (manual) | Yes (via config) |
| **Garbage Collection** | Yes (scheduled) | Yes (manual/API) | Yes (on-demand) |
| **Image Promotion** | Yes (project-based) | No | Yes (repo sync) |
| **Tag Immutability** | Yes | No | Yes |
| **Vulnerability Scanning** | Yes (Trivy) | No | Yes (Trivy) |
| **Replication** | Yes (multi-target) | Via mirror/proxy | Yes (sync) |
| **Web UI** | Full-featured | Minimal | Basic |
| **OCI 1.1 Support** | Yes | Yes | Yes (native) |
| **GitHub Stars** | 28,400+ | 10,400+ | 2,800+ |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Harbor: Enterprise-Grade Lifecycle Management

[Harbor](https://github.com/goharbor/harbor) is the most feature-rich open-source container registry. Its lifecycle management system is designed for enterprise environments where image governance, compliance, and automated cleanup are mandatory.

### Lifecycle Policy Engine

Harbor's retention policies use a rule-based engine that evaluates images against multiple criteria:

- **Repository matching** — Apply policies to specific repos or glob patterns
- **Tag filtering** — Match by tag pattern (regex), age, or count
- **Artifact type** — Apply different rules to images vs Helm charts
- **Keep rules** — Always keep N most recent tags, or tags matching a pattern
- **Schedule** — Run retention policies on a cron schedule

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  harbor-core:
    image: goharbor/harbor-core:v2.12.0
    container_name: harbor-core
    restart: unless-stopped
    environment:
      - CORE_SECRET=your-secret-key
      - HARBOR_ADMIN_PASSWORD=Harbor12345
    volumes:
      - harbor-data:/data
      - ./harbor.yml:/etc/harbor/harbor.yml:ro
    ports:
      - "80:8080"
      - "443:8443"
    depends_on:
      - harbor-db
      - harbor-redis
      - registry

  registry:
    image: goharbor/registry-photon:v2.12.0
    container_name: harbor-registry
    restart: unless-stopped
    volumes:
      - harbor-data:/storage:z

  harbor-db:
    image: goharbor/harbor-db:v2.12.0
    container_name: harbor-db
    restart: unless-stopped
    environment:
      - POSTGRESQL_PASSWORD=harbor-db-pass

  harbor-redis:
    image: goharbor/redis-photon:v2.12.0
    container_name: harbor-redis
    restart: unless-stopped

volumes:
  harbor-data:
```

### Lifecycle Management Operations

```bash
# Configure retention policy via API
curl -X POST "https://harbor.example.com/api/v2.0/projects/myproject/metadatas"   -H "Content-Type: application/json"   -d '{
    "auto_scan": "true",
    "retention_id": "1"
  }'

# Create retention rule: keep latest 5 tags matching "v*"
curl -X POST "https://harbor.example.com/api/v2.0/retentions"   -H "Content-Type: application/json"   -d '{
    "algorithm": "or",
    "rules": [
      {
        "disabled": false,
        "action": "retain",
        "params": {
          "latestPushedK": 5,
          "latestPulledN": 0
        },
        "tag_selectors": [{"kind": "doublestar", "decoration": "matches", "pattern": "v*"}],
        "scope_selectors": {
          "repository": [{"kind": "doublestar", "decoration": "repoMatches", "pattern": "**"}]
        }
      }
    ],
    "schedule": {"type": "Daily", "cron": "0 0 2 * * *"}
  }'

# Trigger garbage collection
curl -X POST "https://harbor.example.com/api/v2.0/system/gc/schedule"   -H "Content-Type: application/json"   -d '{
    "delete_untagged": true,
    "schedule": {"type": "Custom", "cron": "0 0 3 * * 0"}
  }'
```

### When to Choose Harbor

Harbor is the right choice for organizations that need comprehensive image governance. Its retention policy engine, scheduled garbage collection, vulnerability scanning integration, and project-based access control make it the gold standard for enterprise container registry management.

## CNCF Distribution: Minimalist Registry with Manual Lifecycle

[CNCF Distribution](https://github.com/distribution/distribution) (formerly Docker Registry) is the foundational container registry implementation. It provides a clean, minimal API for storing and serving container images but leaves lifecycle management to operators and external tooling.

### Lifecycle Approach

Distribution takes a "provide the primitives, let operators compose" philosophy:

- **Garbage collection** — `registry garbage-col` command removes unreferenced blobs
- **No built-in retention** — Operators must write scripts or use external tools
- **No image promotion** — Images are copied manually or via external sync tools
- **Delete API** — Individual manifests and blobs can be deleted via the API

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  registry:
    image: registry:2.8
    container_name: distribution-registry
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - registry-data:/var/lib/registry
      - ./config.yml:/etc/distribution/config.yml:ro
    environment:
      - REGISTRY_STORAGE_DELETE_ENABLED=true

volumes:
  registry-data:
```

### Configuration

```yaml
# config.yml
version: 0.1
log:
  level: info
storage:
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
  maintenance:
    uploadpurging:
      enabled: true
      age: 168h
      interval: 24h
      dryrun: false
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
```

### Manual Garbage Collection

```bash
# Delete a manifest by digest
curl -X DELETE "https://registry.example.com/v2/myrepo/manifests/sha256:abc123"

# Run garbage collection (removes unreferenced blobs)
docker exec registry bin/registry garbage-collect   /etc/distribution/config.yml --delete-untagged

# Dry-run to see what would be deleted
docker exec registry bin/registry garbage-collect   /etc/distribution/config.yml --dry-run
```

### When to Choose Distribution

Distribution is ideal when you want a minimal registry and handle lifecycle management through external tooling like Skopeo, custom scripts, or CI/CD pipeline steps. It's the right choice for platform teams that build their own registry management workflows and don't need a full enterprise feature set.

## Zot: OCI-Native with Built-In Lifecycle

[Zot](https://github.com/project-zot/zot) is a production-ready, OCI-native container registry built from the ground up for the OCI Distribution Specification. It includes built-in image lifecycle features without requiring external tooling.

### Lifecycle Features

- **Storage deduplication** — Automatically deduplicates shared layers across images
- **Garbage collection** — On-demand and scheduled GC via configuration
- **Retention policies** — Keep N latest tags, delete by age, or filter by pattern
- **Image sync** — Pull and mirror images from upstream registries
- **OCI artifact support** — Store any OCI artifact type alongside images

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  zot:
    image: ghcr.io/project-zot/zot-minimal:latest
    container_name: zot-registry
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - zot-data:/var/lib/registry
      - ./config-zot.json:/etc/zot/config.json:ro
    user: "1000:1000"

volumes:
  zot-data:
```

### Configuration

```json
{
  "distSpecVersion": "1.1.1",
  "storage": {
    "rootDirectory": "/var/lib/registry",
    "dedupe": true,
    "storageDriver": {
      "name": "s3",
      "rootdirectory": "/zot",
      "region": "us-east-1",
      "regionendpoint": "minio.example.com:9000",
      "bucket": "zot-registry",
      "secure": false
    },
    "gc": true,
    "gcDelay": "2h",
    "gcInterval": "24h",
    "subPaths": {
      "/infra": {
        "rootDirectory": "/var/lib/registry-infra",
        "dedupe": true,
        "gc": true
      }
    }
  },
  "http": {
    "address": "0.0.0.0",
    "port": "5000"
  },
  "extensions": {
    "search": {
      "enable": true,
      "cve": {
        "scanner": "trivy",
        "updateInterval": "2h"
      }
    },
    "lint": {
      "enabled": true
    }
  }
}
```

### Lifecycle Operations

```bash
# Sync images from upstream registry
# config.json sync section
{
  "extensions": {
    "sync": {
      "credentialsFile": "/etc/zot/registries.json",
      "configs": [{
        "urls": ["https://docker.io"],
        "content": [{
          "type": "image",
          "names": ["library/nginx", "library/redis"],
          "tags": {"regex": "latest|1.25.*"}
        }]
      }]
    }
  }
}

# Trigger garbage collection via API
curl -X POST "https://zot.example.com/v2/_zot/ext/maintenance"   -H "Content-Type: application/json"   -d '{"action": "gc"}'

# Check storage usage
curl "https://zot.example.com/v2/_zot/ext/monitor"
```

### When to Choose Zot

Zot is ideal for teams that want an OCI-native registry with built-in lifecycle features but don't need Harbor's full enterprise feature set. Its storage deduplication, automatic garbage collection scheduling, and sync capabilities make it a strong middle ground between Distribution's minimalism and Harbor's comprehensiveness.

## Choosing the Right Registry for Lifecycle Management

| Requirement | Best Choice | Rationale |
|-------------|-------------|-----------|
| Rule-based retention policies | **Harbor** | Most flexible policy engine with scheduling |
| Scheduled garbage collection | **Harbor** | Built-in cron-based GC scheduling |
| Minimal registry + custom scripts | **Distribution** | Clean API, external tooling ecosystem |
| OCI-native with auto-dedup | **Zot** | Layer deduplication built into storage |
| Image sync/mirroring | **Zot** | Native sync from upstream registries |
| Vulnerability scanning integration | **Harbor** / **Zot** | Both include Trivy scanning |
| Multi-project governance | **Harbor** | Project-level RBAC and policies |
| Lightweight deployment | **Zot** | Single binary, no database required |

## Self-Hosted Registry Lifecycle Benefits

Managing container image lifecycle in your own registry eliminates dependency on cloud provider retention policies, ensures compliance with internal image retention requirements, and provides full audit visibility into which images are retained and why. Automated garbage collection reclaims storage from deleted images, while retention policies prevent unbounded growth from CI/CD pipelines that push images on every commit.

For related infrastructure, see our [container image management tools guide](../2026-05-10-container-image-management-skopeo-oras-crane-guide/) and [registry proxy cache setup](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/).

## FAQ

### How often should I run garbage collection?

For active registries, weekly garbage collection during maintenance windows is a good starting point. Harbor supports scheduled GC through its API. Distribution requires manual or cron-triggered execution. Zot can run GC on a configurable interval automatically.

### What happens to images during garbage collection?

Garbage collection removes blob layers that are no longer referenced by any manifest. Untagged images (images with no tags pointing to their manifests) are typically cleaned up first. Running with `--dry-run` first shows what would be deleted without actually removing anything.

### Can I prevent certain images from being deleted?

Yes. Harbor's retention policies support "keep" rules that always retain images matching specific tag patterns (e.g., `release-*`, `v1.*`). Zot's sync configuration can pin specific tags. With Distribution, you implement this logic in your cleanup scripts.

### Does garbage collection affect running containers?

No. Garbage collection removes layers from the registry storage, not from running containers. Running containers have already pulled their layers locally. However, if a running container needs to pull an additional layer from a deleted image, that pull will fail.

### How much storage does garbage collection typically reclaim?

This depends on your image update frequency and tag management practices. Registries with frequent CI/CD builds can see 30-60% storage reduction after the first GC run. Ongoing GC typically reclaims 10-20% of accumulated storage per cycle.

### Should I enable storage deduplication?

Yes, if your registry supports it. Zot's deduplication identifies identical layers across images and stores them only once. This is especially valuable for multi-architecture images where the same base layers appear across multiple platform variants. Harbor also benefits from underlying storage-level deduplication.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Lifecycle: Harbor vs Distribution vs Zot",
  "description": "Compare container registry lifecycle management capabilities — Harbor, CNCF Distribution, and Zot — for image retention, garbage collection, and cleanup automation.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
