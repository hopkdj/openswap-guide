---
title: "Self-Hosted Container Registry Garbage Collection: Harbor vs Distribution vs Zot (2026)"
date: "2026-05-22"
tags: ["docker", "containers", "registry", "garbage-collection", "self-hosted"]
draft: false
description: "Compare garbage collection strategies across self-hosted container registries — Harbor, Docker Distribution, and Zot. Complete guide with configuration and automation examples."
---

Container registries accumulate unused image layers over time. Every build pushes new layers; old layers from deleted tags, overwritten images, and abandoned projects remain in storage. Without garbage collection, registry storage grows unbounded, increasing costs and degrading performance. This guide compares garbage collection capabilities across three popular self-hosted registries.

## Why Registry Garbage Collection Matters

A typical CI/CD pipeline produces dozens of image builds per day. Each build creates new layers, and even after deleting old tags, the underlying blob data persists until garbage collection reclaims it.

**Key challenges:**
- **Storage costs**: Unused layers can consume 70-90% of registry storage
- **Performance**: Large registries with millions of unreferenced blobs suffer slower pull times
- **Backup size**: Uncollected garbage inflates backup storage and recovery time
- **Compliance**: Data retention policies require automatic cleanup of old images

## Registry GC Comparison

| Feature | Harbor | Docker Distribution | Zot |
|---------|--------|---------------------|-----|
| GC mechanism | Built-in scheduler | CLI command (`garbage-collect`) | Built-in scheduler + API |
| Scheduling | Web UI + API | Manual or cron | Web UI + API + config |
| Online GC | Yes (read-only mode) | No (requires registry downtime) | Yes (no downtime) |
| Selective cleanup | By project, by tag pattern | All unreferenced blobs | By repository, by tag age |
| Retention policies | Yes (keep N latest tags) | No (all or nothing) | Yes (keep N latest, keep by age) |
| Dry-run mode | Yes | Yes | Yes |
| Storage backend | PostgreSQL + filesystem/S3 | filesystem/S3/Azure/GCS | filesystem/S3 |
| GitHub stars | 28,500+ | 10,400+ | 2,200+ |
| CNCF status | Graduated | Original Docker project | Sandbox |

## Registry 1: Harbor

Harbor is a CNCF Graduated container registry with enterprise-grade garbage collection. It runs GC on a schedule while the registry remains available (blobs are marked read-only during GC).

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  harbor-core:
    image: goharbor/harbor-core:v2.11.0
    depends_on:
      - harbor-db
      - harbor-redis
    environment:
      - CORE_SECRET=changeme
      - DATABASE_TYPE=postgresql
      - POSTGRESQL_HOSTNAME=harbor-db
      - REDIST_URL=harbor-redis:6379
    ports:
      - "8080:8080"

  harbor-registry:
    image: goharbor/registry-photon:v2.11.0
    volumes:
      - registry-data:/storage
    depends_on:
      - harbor-core

  harbor-db:
    image: goharbor/harbor-db:v2.11.0
    environment:
      - POSTGRESQL_PASSWORD=changeme
    volumes:
      - db-data:/var/lib/postgresql/data

  harbor-redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  registry-data:
  db-data:
  redis-data:
```

### Configure GC Schedule via API

```bash
# Set GC to run daily at 2 AM
curl -X PUT "http://localhost:8080/api/v2.0/system/gc/schedule"   -H "Content-Type: application/json"   -u "admin:Harbor12345"   -d '{
    "schedule": {
      "type": "Daily",
      "cron": "0 0 2 * * *"
    },
    "parameters": {
      "delete_untagged": true,
      "workers": 3
    }
  }'
```

### Configure GC via Web UI

1. Navigate to **Administration** → **Garbage Collection**
2. Set schedule: Daily, Weekly, or Custom cron
3. Enable **Delete untagged artifacts** to clean up layers from deleted tags
4. Set **Workers** to control parallelism (higher = faster, more I/O)

### Harbor GC Behavior

During garbage collection:
1. Harbor marks the registry as read-only
2. Scans all repositories for unreferenced blobs
3. Deletes unreferenced blobs from storage
4. Updates the database to reflect reclaimed space
5. Removes read-only mode

The read-only window typically lasts 5-30 minutes depending on registry size.

## Registry 2: Docker Distribution

Docker Distribution (the original registry v2) provides a CLI-based garbage collection tool. It requires stopping the registry before running GC, making it less suitable for high-availability environments.

### Running GC

```bash
# Stop the registry first
docker stop registry

# Run GC in dry-run mode
docker run --rm   -v /var/lib/registry:/var/lib/registry   registry:2 garbage-collect /etc/docker/registry/config.yml --dry-run

# Run GC (actual deletion)
docker run --rm   -v /var/lib/registry:/var/lib/registry   registry:2 garbage-collect /etc/docker/registry/config.yml

# Restart the registry
docker start registry
```

### Configuration

```yaml
# /etc/docker/registry/config.yml
version: 0.1
storage:
  filesystem:
    rootdirectory: /var/lib/registry
  maintenance:
    uploadpurging:
      enabled: true
      age: 168h       # Delete incomplete uploads after 7 days
      interval: 24h   # Check every 24 hours
      dryrun: false
    readonly:
      enabled: false
```

### Automating with Cron

```bash
#!/bin/bash
# /etc/cron.daily/registry-gc.sh
docker stop registry
docker run --rm   -v /var/lib/registry:/var/lib/registry   registry:2 garbage-collect /etc/docker/registry/config.yml
docker start registry
```

### Pros and Cons

**Pros:**
- Simple and reliable — single command cleans all unreferenced blobs
- Dry-run mode to preview what will be deleted
- Works with all storage backends (filesystem, S3, Azure Blob, GCS)
- No additional dependencies

**Cons:**
- Requires registry downtime during GC (read-only mode)
- No selective cleanup — deletes ALL unreferenced blobs
- No retention policies — cannot keep N latest tags per repository
- No built-in scheduling — requires external cron or orchestration

## Registry 3: Zot

Zot is a CNCF Sandbox OCI-native registry with modern garbage collection features including online GC, retention policies, and API-driven management.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  zot:
    image: ghcr.io/project-zot/zot:v2.0.3
    ports:
      - "5000:5000"
    volumes:
      - ./zot-config.json:/etc/zot/config.json:ro
      - zot-data:/var/lib/registry
    environment:
      - ZOT_LOG_LEVEL=info

volumes:
  zot-data:
```

### Zot Configuration with GC

```json
{
  "distSpecVersion": "1.1.0",
  "storage": {
    "rootDirectory": "/var/lib/registry",
    "gc": true,
    "gcDelay": "2h",
    "gcInterval": "24h",
    "dedupe": true,
    "retention": {
      "repos": ["*"],
      "deleteReferrers": true,
      "keepTags": [
        {
          "patterns": ["latest", "stable"],
          "pinned": true
        },
        {
          "patterns": ["v*"],
          "maxAge": "90d",
          "maxCount": 10
        }
      ]
    }
  },
  "http": {
    "address": "0.0.0.0",
    "port": "5000"
  },
  "log": {
    "level": "info"
  }
}
```

### GC via API

```bash
# Trigger GC for a specific repository
curl -X POST "http://localhost:5000/v2/_zot/ext/gc?repo=myproject/myapp"

# Check GC status
curl "http://localhost:5000/v2/_zot/ext/gc/status"
```

### Retention Policies

Zot's retention system supports:
- **Pinned tags**: Never delete tags matching specific patterns (e.g., `latest`, `stable`)
- **Age-based cleanup**: Delete tags older than N days
- **Count-based cleanup**: Keep only the N most recent tags
- **Pattern matching**: Use glob patterns to match tag names

### Pros and Cons

**Pros:**
- Online garbage collection — no registry downtime
- Fine-grained retention policies (age, count, patterns)
- OCI-native — supports OCI Distribution Spec 1.1
- API-driven GC management
- Content deduplication reduces storage usage

**Cons:**
- Smaller community compared to Harbor (2,200 vs 28,500 stars)
- Fewer enterprise features (no built-in vulnerability scanning, RBAC is basic)
- Newer project — less production-hardened than Harbor or Distribution

## Choosing the Right Registry for GC

### For Enterprise Environments

Use **Harbor**. It provides the most comprehensive GC features including scheduled GC, retention policies, web UI management, and integration with vulnerability scanning. The CNCF Graduated status means it's production-ready for critical workloads.

### For Simple Self-Hosted Setups

Use **Docker Distribution** if you have a small registry and can tolerate brief downtime during GC. It's the simplest option with zero configuration beyond the initial setup.

### For Modern OCI-Native Deployments

Use **Zot** if you want online GC, retention policies, and OCI 1.1 compliance without the overhead of Harbor's PostgreSQL dependency. Zot's lightweight architecture is ideal for edge deployments and resource-constrained environments.

For related reading, see our [container registry comparison](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/) and [container image lazy pulling guide](../2026-05-10-container-image-lazy-pulling-stargz-nydus-soci-guide/).


For additional container infrastructure guidance, see our [container registry comparison](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/) and [container image lazy pulling strategies](../2026-05-10-container-image-lazy-pulling-stargz-nydus-soci-guide/). For registry security best practices, our [supply chain security guide](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-20/) covers image signing and verification workflows.

## Storage Optimization Beyond Garbage Collection

Garbage collection is one piece of registry storage management. Several complementary strategies reduce storage requirements before GC even runs:

**Layer deduplication**: Many registries store identical layers from different images multiple times. Zot supports content-level deduplication natively, reducing storage by 30-50% for registries with many images sharing base layers. Harbor also supports deduplication through its underlying storage backend configuration.

**Compression**: All three registries support gzip-compressed layer storage. For registries with large images (ML models, database containers), enabling compression can reduce storage by 40-60%.

**Remote storage backends**: For large registries, offloading blobs to S3-compatible storage (MinIO, Ceph, AWS S3) reduces local disk requirements. Harbor and Zot both support S3 storage backends with configurable retention policies that automatically expire old objects.

**Image squashing**: During the build process, squashing multiple layers into a single layer reduces the number of blobs stored in the registry. This is particularly effective for images with many small intermediate layers from multi-stage Dockerfiles.

## FAQ

### How often should I run garbage collection?

For active CI/CD registries, daily GC is recommended. For development registries with infrequent pushes, weekly GC is sufficient. The key metric is storage growth rate — if your registry grows more than 10% per week, increase GC frequency.

### What is "dry-run" mode in garbage collection?

Dry-run mode scans the registry for unreferenced blobs without deleting them. It reports how much space would be reclaimed and which blobs would be deleted. Always run dry-run first to verify GC won't accidentally remove needed data.

### Does garbage collection affect running containers?

No. GC only removes blobs that are not referenced by any image manifest. Running containers reference their image layers through the registry, so their blobs will never be marked as unreferenced.

### Can I configure GC to keep specific tags?

Harbor and Zot support retention policies that keep specific tags. Harbor keeps tags matching configured patterns; Zot supports pinned tags, age-based, and count-based retention. Docker Distribution does not support selective retention.

### How do I monitor registry storage usage?

Harbor provides storage metrics in its web UI and API. Zot exposes storage metrics via its API. Docker Distribution requires external monitoring (e.g., checking filesystem usage with `du -sh /var/lib/registry`).

### What happens if GC is interrupted mid-process?

Both Harbor and Zot are designed to handle interruptions gracefully. They maintain a transaction log and resume from the last checkpoint on the next run. Docker Distribution's GC is atomic — if interrupted, it leaves the registry in a consistent state (either all deleted or none).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Registry Garbage Collection: Harbor vs Distribution vs Zot (2026)",
  "description": "Compare garbage collection strategies across self-hosted container registries — Harbor, Docker Distribution, and Zot.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
