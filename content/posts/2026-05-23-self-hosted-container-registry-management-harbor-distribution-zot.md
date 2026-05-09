---
title: "Self-Hosted Container Registry Management: Harbor vs Distribution vs Zot 2026"
date: "2026-05-23T10:00:00+00:00"
draft: false
tags: ["containers", "registry", "self-hosted", "docker", "devops"]
---

Container registries store and distribute Docker and OCI images for your infrastructure. As teams push more images, registries grow rapidly — a few hundred images can consume hundreds of gigabytes. Effective registry management includes garbage collection, image lifecycle policies, vulnerability scanning, and access control. Three open-source registry solutions address these needs: **Harbor**, **Distribution** (Docker Registry), and **Zot**.

## Why Self-Host a Container Registry?

Public registries like Docker Hub have rate limits, bandwidth costs, and no control over image retention. Self-hosting provides:

- **No rate limits** — pull images as fast as your network allows
- **Full control** — set retention policies, scan for vulnerabilities, manage access
- **Air-gapped support** — operate without internet connectivity
- **Cost savings** — eliminate egress fees for large image pulls
- **Compliance** — keep images within your network boundary for regulatory requirements
- **Faster builds** — local registry eliminates network latency for image pulls

## Harbor

Harbor is an open-source container registry with enterprise features including vulnerability scanning, image signing, replication, and role-based access control. It is a CNCF graduated project.

**GitHub**: [goharbor/harbor](https://github.com/goharbor/harbor) — actively maintained, CNCF graduated project

### Key Features

- **Vulnerability scanning** — integrated Trivy scanning for every pushed image
- **Image garbage collection** — built-in GC with scheduling and soft-delete support
- **Image retention policies** — automatically delete old images based on tags, age, or count
- **Replication** — push/pull images between multiple Harbor instances or to external registries
- **RBAC** — fine-grained access control with project-level permissions
- **Image signing** — Notary integration for content trust
- **Audit logging** — track all registry operations
- **LDAP/AD integration** — enterprise authentication

### Docker Compose Configuration

Harbor provides an official installer, but can be deployed via Docker Compose:

```yaml
services:
  harbor-core:
    image: goharbor/harbor-core:latest
    container_name: harbor-core
    restart: unless-stopped
    depends_on:
      - harbor-db
      - harbor-redis
    environment:
      - CORE_SECRET=changeme
      - CSRF_KEY=changeme
      - DATABASE_URL=postgresql://harbor:harbor@harbor-db:5432/registry
      - REDIST_URL=redis://harbor-redis:6379/0
    ports:
      - "8080:8080"

  harbor-registry:
    image: goharbor/registry-photon:latest
    container_name: harbor-registry
    restart: unless-stopped
    volumes:
      - registry_data:/storage
    environment:
      - REGISTRY_STORAGE_DELETE_ENABLED=true
      - REGISTRY_HTTP_ADDR=0.0.0.0:5000

  harbor-db:
    image: goharbor/harbor-db:latest
    container_name: harbor-db
    restart: unless-stopped
    environment:
      - POSTGRES_PASSWORD=harbor
    volumes:
      - db_data:/var/lib/postgresql/data

  harbor-redis:
    image: redis:7-alpine
    container_name: harbor-redis
    restart: unless-stopped

volumes:
  registry_data:
  db_data:
```

Garbage collection configuration via Harbor API:

```bash
# Trigger garbage collection
curl -X POST "http://localhost:8080/api/v2.0/system/gc/schedule" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"schedule":{"type":"Daily","cron":"0 0 2 * * *"}}'

# Set retention policy
curl -X POST "http://localhost:8080/api/v2.0/projects/1/metadatas" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"image_auto_scan":"true","prevent_vul":"true"}'
```

## Distribution (Docker Registry)

Distribution is the reference implementation of the OCI Distribution Specification. It is the engine behind Docker Hub and many other registries, providing a minimal, high-performance registry core.

**GitHub**: [distribution/distribution](https://github.com/distribution/distribution) — 10,405 stars

### Key Features

- **OCI-compliant** — fully implements the OCI Distribution Specification
- **Minimal footprint** — single binary, no database required
- **Storage drivers** — supports local filesystem, S3, Azure Blob, GCS, Swift, and more
- **Garbage collection** — built-in GC command for reclaiming unused layers
- **Token authentication** — integrates with external auth providers
- **Notifications** — webhook notifications for push/pull events
- **Content trust** — supports Notary for image signing

### Docker Compose Configuration

```yaml
services:
  registry:
    image: registry:2
    container_name: docker-registry
    ports:
      - "5000:5000"
    environment:
      - REGISTRY_STORAGE_DELETE_ENABLED=true
      - REGISTRY_HTTP_SECRET=a-long-random-secret
      - REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY=/var/lib/registry
    volumes:
      - registry_data:/var/lib/registry
      - ./config.yml:/etc/docker/registry/config.yml:ro
      - ./auth:/auth:ro
    restart: unless-stopped

volumes:
  registry_data:
```

Configuration file for garbage collection:

```yaml
version: 0.1
log:
  level: info
storage:
  delete:
    enabled: true
  filesystem:
    rootdirectory: /var/lib/registry
  maintenance:
    uploadpurging:
      enabled: true
      age: 168h
      interval: 24h
      dryrun: false
http:
  addr: 0.0.0.0:5000
  secret: a-long-random-secret
auth:
  htpasswd:
    realm: Registry Realm
    path: /auth/htpasswd
```

Running garbage collection:

```bash
# Stop the registry first
docker compose stop registry

# Run garbage collection
docker compose run --rm registry garbage-collect /etc/docker/registry/config.yml

# Or dry-run to see what would be deleted
docker compose run --rm registry garbage-collect --dry-run /etc/docker/registry/config.yml

# Restart the registry
docker compose start registry
```

## Zot

Zot is a next-generation OCI-native container registry designed for simplicity and performance. It is written in Go and focuses on being lightweight while providing essential registry features.

**GitHub**: [project-zot/zot](https://github.com/project-zot/zot) — actively maintained, CNCF sandbox project

### Key Features

- **OCI-native** — fully compliant with OCI Distribution and Image specs
- **Single binary** — no external dependencies, no database required
- **Built-in garbage collection** — automatic and manual GC modes
- **Image scanning** — integrated Trivy scanning
- **Storage deduplication** — shared blob storage across repositories
- **Multi-architecture support** — native manifest list handling
- **S3-compatible storage** — direct backend support for S3, MinIO
- **Low resource usage** — designed for edge and resource-constrained environments

### Docker Compose Configuration

```yaml
services:
  zot:
    image: ghcr.io/project-zot/zot-linux-amd64:latest
    container_name: zot-registry
    ports:
      - "5000:5000"
    volumes:
      - ./zot-config.json:/etc/zot/config.json:ro
      - zot_data:/var/lib/registry
    restart: unless-stopped

volumes:
  zot_data:
```

Configuration file:

```json
{
  "distSpecVersion": "1.1.1",
  "storage": {
    "rootDirectory": "/var/lib/registry",
    "dedupe": true,
    "remoteCache": true,
    "gc": true,
    "gcDelay": "1h",
    "gcInterval": "24h",
    "storageDriver": {
      "name": "s3",
      "rootdirectory": "/zot",
      "region": "us-east-1",
      "bucket": "my-registry-bucket",
      "regionendpoint": "http://minio:9000",
      "accesskey": "admin",
      "secretkey": "password",
      "secure": false
    }
  },
  "http": {
    "address": "0.0.0.0",
    "port": "5000"
  },
  "log": {
    "level": "info"
  },
  "extensions": {
    "search": {
      "enable": true,
      "cve": {
        "updateInterval": "24h"
      }
    },
    "ui": {
      "enable": true
    },
    "scrub": {
      "enable": true,
      "interval": "24h"
    }
  }
}
```

## Feature Comparison

| Feature | Harbor | Distribution | Zot |
|---------|--------|-------------|-----|
| OCI compliant | ✅ Yes | ✅ Yes (reference impl) | ✅ Yes |
| Garbage collection | ✅ Scheduled + API | ✅ CLI command | ✅ Automatic + manual |
| Vulnerability scanning | ✅ Trivy built-in | ❌ External | ✅ Trivy built-in |
| Web UI | ✅ Full-featured | ❌ None | ✅ Basic UI |
| RBAC | ✅ Project-level | ❌ Token-based | ✅ API keys |
| Image retention policies | ✅ Configurable | ❌ Manual GC only | ✅ Configurable |
| Replication | ✅ Multi-registry | ❌ Pull-through only | ✅ Planned |
| Storage backends | Local, S3 | Local, S3, Azure, GCS | Local, S3, MinIO |
| Storage deduplication | ✅ | ❌ | ✅ Native |
| Database required | ✅ PostgreSQL | ❌ | ❌ |
| Resource usage | High (multi-service) | Low (single binary) | Low (single binary) |
| LDAP/AD integration | ✅ Yes | Via token auth | Planned |
| Audit logging | ✅ Comprehensive | Via notifications | Basic |
| CNCF status | Graduated | Graduated | Sandbox |
| Best for | Enterprise teams | Minimal setups | Edge/cloud-native |

## Why Registry Management Matters

As container adoption grows, registries become critical infrastructure. Without proper management:

**Storage costs explode** — each image layer is stored separately. A single multi-stage build can produce dozens of layers. Without garbage collection, deleted tags leave orphaned layers consuming disk space indefinitely.

**Security risks increase** — old images may contain known vulnerabilities. Without automated scanning and retention policies, your registry becomes a repository of insecure base images that teams unknowingly deploy.

**Build performance degrades** — large registries with millions of blobs slow down manifest lookups and layer downloads. Regular cleanup and deduplication keep response times low.

**Compliance gaps appear** — regulatory requirements often mandate image provenance tracking, vulnerability reporting, and access audit trails. Unmanaged registries cannot provide these guarantees.

For container image security, see our [container security scanning guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-scanning-guide-2026/) and [supply chain security article](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-in-toto-guide-2026/). If you need container orchestration alongside your registry, our [Kubernetes comparison](../kubernetes-vs-docker-swarm-vs-nomad/) covers the options.

## FAQ

### What is container registry garbage collection?

Garbage collection (GC) removes unreferenced image layers from the registry storage. When you delete an image tag, the manifest reference is removed, but the underlying layers (blobs) remain on disk. GC identifies blobs that no manifest references and deletes them, reclaiming disk space.

### How often should I run garbage collection?

For active development registries, run GC weekly or daily during low-traffic periods. For production registries with stable images, monthly GC is usually sufficient. The frequency depends on your push/delete volume — high-velocity CI/CD pipelines generate more orphaned layers and need more frequent cleanup.

### Does garbage collection affect running containers?

No. Garbage collection only removes layers that are no longer referenced by any manifest in the registry. Running containers have already pulled their layers locally and do not depend on the registry for continued operation. However, if you need to re-pull a deleted image, it will no longer be available.

### What is storage deduplication in container registries?

Storage deduplication identifies identical image layers across different repositories and stores only one copy. For example, if 10 different images are based on the same Ubuntu base image, deduplication stores the Ubuntu layers once instead of 10 times. This can reduce storage usage by 30-70% in registries with many related images.

### Can I use a self-hosted registry with Kubernetes?

Yes. Configure your Kubernetes cluster to use your self-hosted registry by adding it as an insecure registry (for HTTP) or configuring TLS certificates. In Docker-based setups, add the registry URL to the Docker daemon configuration. For containerd, configure the registry mirror in `/etc/containerd/config.toml`.

### What is the difference between Harbor and Distribution?

Distribution is the minimal OCI registry implementation — it stores and serves images with basic authentication. Harbor is a full-featured registry platform built on top of Distribution, adding a web UI, vulnerability scanning, RBAC, replication, audit logging, and project management. Choose Distribution for minimal setups and Harbor for enterprise requirements.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Registry Management: Harbor vs Distribution vs Zot 2026",
  "description": "Compare Harbor, Docker Distribution, and Zot for self-hosted container registry management with garbage collection and vulnerability scanning.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
