---
title: "Self-Hosted Container Registry Lifecycle Management: Harbor vs CNCF Distribution vs Zot"
date: "2026-05-19"
tags: ["container-registry", "harbor", "docker", "oci", "devops", "lifecycle-management"]
draft: false
---

Container registries are a critical part of any container-native infrastructure, but as teams push more images, storage costs spiral and registries become bloated with unused layers, outdated tags, and abandoned projects. Without proper lifecycle management, you end up paying for storage you don't need and slowing down pull operations. This guide compares three leading open-source container registry solutions — **Harbor**, **CNCF Distribution** (formerly Docker Registry), and **Zot** — focused specifically on their image lifecycle management capabilities: garbage collection, retention policies, tag immutability, and automated cleanup workflows.

## Understanding Container Registry Lifecycle Management

A container registry lifecycle management strategy covers the full lifespan of container images from initial push through eventual deletion. Key capabilities include:

- **Garbage collection (GC)** — reclaiming storage from deleted or overwritten images by removing unreferenced blobs and manifests
- **Retention policies** — automatically keeping only the N most recent tags per repository, or retaining images matching specific patterns
- **Tag immutability** — preventing tags from being overwritten to ensure build reproducibility
- **Vulnerability-based cleanup** — quarantining or deleting images that fail security scans
- **Replication lifecycle** — managing image lifecycle across replicated registry instances
- **Storage quota enforcement** — setting per-project or per-repository storage limits

Each of the three registries we compare approaches these challenges differently, with varying levels of automation, UI support, and operational complexity.

## Harbor

[Harbor](https://goharbor.io/) is the most feature-rich open-source container registry, originally developed by VMware and now a CNCF graduated project. It provides enterprise-grade lifecycle management with a web-based UI, making it ideal for teams that need policy-driven image governance without relying on CLI automation.

**Stars:** 28,447+ | **Last updated:** May 2026 | **License:** Apache 2.0

### Key Lifecycle Features

- **Built-in garbage collection** — Harbor supports online GC that runs without downtime, using a blob deletion API that marks unreferenced layers for removal and cleans them up asynchronously
- **Tag retention rules** — configure rules based on tag patterns, age, count, or vulnerability status (e.g., "keep latest 5 tags matching `v*`", "delete tags older than 90 days")
- **Immutable tags** — enforce tag immutability at the project level, preventing accidental overwrites of production image tags
- **Storage quotas** — set per-project storage limits with configurable actions when thresholds are reached (warning, block push)
- **Vulnerability-based policies** — automatically prevent deployment or flag images exceeding a defined severity threshold
- **Scheduled cleanup** — all retention and GC policies can run on a cron-like schedule

### Docker Compose Deployment

Harbor provides an official installer with Docker Compose:

```yaml
version: '2.3'
services:
  harbor-core:
    image: goharbor/harbor-core:v2.12.0
    container_name: harbor-core
    restart: always
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    volumes:
      - /data/harbor/core/config:/etc/core/config:z
      - /data/harbor/core/secrets:/etc/core/secrets:z
      - /data/harbor/core/certs:/etc/core/certs:z
    networks:
      - harbor
    depends_on:
      - registry
      - redis
      - harbor-db
    logging:
      driver: "json-file"
      options:
        max-file: "10"
        max-size: "200m"

  registry:
    image: goharbor/registry-photon:v2.12.0
    container_name: registry
    restart: always
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    volumes:
      - /data/registry:/storage:z
    networks:
      - harbor
    depends_on:
      - redis
    logging:
      driver: "json-file"
      options:
        max-file: "10"
        max-size: "200m"

  redis:
    image: goharbor/redis-photon:v2.12.0
    container_name: redis
    restart: always
    cap_drop:
      - ALL
    volumes:
      - /data/redis:/var/lib/redis
    networks:
      - harbor

  harbor-db:
    image: goharbor/harbor-db:v2.12.0
    container_name: harbor-db
    restart: always
    cap_drop:
      - ALL
    volumes:
      - /data/database:/var/lib/postgresql/data
    networks:
      - harbor
    environment:
      - POSTGRES_PASSWORD=harbor_db_password

networks:
  harbor:
    driver: bridge
```

Harbor's garbage collection can be triggered via the UI or API:

```bash
# Trigger GC via Harbor API
curl -X POST "https://harbor.example.com/api/v2.0/system/gc/schedule" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"schedule":{"type":"Daily","cron":"0 0 2 * * *"},"parameters":{"delete_untagged": true}}'

# List retention policies
curl "https://harbor.example.com/api/v2.0/projects/myproject/retention/policies" \
  -H "Authorization: Bearer $TOKEN"
```

## CNCF Distribution

[CNCF Distribution](https://github.com/distribution/distribution) is the reference implementation of the OCI Distribution Specification. It powers Docker Hub and many private registries. Unlike Harbor, Distribution is a minimal, single-purpose registry without a built-in web UI — lifecycle management is handled through its API and the `registry garbage-collect` CLI command.

**Stars:** 10,405+ | **Last updated:** May 2026 | **License:** Apache 2.0

### Key Lifecycle Features

- **Offline garbage collection** — Distribution's GC requires stopping the registry service, running the `garbage-collect` command against the storage backend, then restarting. This means scheduled maintenance windows are necessary
- **No built-in retention policies** — image retention must be managed externally via scripts, CI/CD pipelines, or third-party tools like `regclient` or `crane`
- **Blob deletion API** — supports the OCI blob deletion API, allowing individual manifests and blobs to be marked for deletion (though actual storage reclamation requires GC)
- **Minimal overhead** — with no database or UI layer, Distribution has a smaller attack surface and lower resource footprint
- **Storage drivers** — supports S3, Azure Blob, GCS, filesystem, and Swift backends, with GC working across all of them

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  registry:
    image: registry:2.8
    container_name: distribution-registry
    restart: always
    ports:
      - "5000:5000"
    volumes:
      - ./config.yml:/etc/distribution/config.yml:ro
      - registry-data:/var/lib/registry
    environment:
      - REGISTRY_STORAGE_DELETE_ENABLED=true
    networks:
      - registry-net

networks:
  registry-net:
    driver: bridge

volumes:
  registry-data:
    driver: local
```

Configuration for enabling deletion and GC:

```yaml
version: 0.1
log:
  level: info
storage:
  delete:
    enabled: true
  cache:
    blobdescriptor: inmemory
  filesystem:
    rootdirectory: /var/lib/registry
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
```

Running garbage collection (requires stopping the registry first):

```bash
# Stop the registry
docker compose down

# Run garbage collection
docker run --rm \
  -v registry-data:/var/lib/registry \
  registry:2.8 garbage-collect /etc/distribution/config.yml

# Restart the registry
docker compose up -d

# For automated GC, use a cron job wrapper:
#!/bin/bash
docker compose -f /opt/registry/docker-compose.yml down
docker run --rm \
  -v registry-data:/var/lib/registry \
  registry:2.8 garbage-collect /etc/distribution/config.yml --delete-untagged
docker compose -f /opt/registry/docker-compose.yml up -d
```

External retention policy management using `regclient`:

```bash
# Install regclient
curl -sL https://github.com/regclient/regclient/releases/latest/download/regctl-linux-amd64 \
  -o /usr/local/bin/regctl && chmod +x /usr/local/bin/regctl

# List all tags in a repository
regctl tag list registry.example.com/myproject/myimage

# Delete tags older than 30 days (requires external script)
regctl tag delete registry.example.com/myproject/myimage:v1.0.0

# Script to keep only the latest N tags
#!/bin/bash
REPO="registry.example.com/myproject/myimage"
KEEP=5
TAGS=$(regctl tag list $REPO | sort -r)
DELETE_TAGS=$(echo "$TAGS" | tail -n +$((KEEP + 1)))
for tag in $DELETE_TAGS; do
  echo "Deleting $REPO:$tag"
  regctl tag delete "$REPO:$tag"
done
```

## Zot

[Zot](https://zotregistry.dev/) is a vendor-neutral, OCI-native container registry designed for cloud-native environments. It's a newer entrant compared to Harbor and Distribution but has quickly gained traction for its lightweight design and built-in lifecycle management features that don't require external tooling.

**Stars:** 2,152+ | **Last updated:** May 2026 | **License:** Apache 2.0

### Key Lifecycle Features

- **Native garbage collection** — Zot supports GC via its API without requiring a service restart, making it suitable for production environments that need continuous availability
- **Referrer API support** — implements the OCI Referrers API, enabling artifact indexing and cleanup of associated artifacts (SBOMs, signatures) alongside their parent images
- **Image retention by age** — built-in support for deleting images older than a configurable threshold
- **Storage notifications** — webhook-based notifications for storage threshold events, enabling automated remediation workflows
- **Multi-tenancy** — native support for repository namespaces with per-namespace storage quotas
- **Deduplication** — automatic blob deduplication across repositories to minimize storage usage

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  zot:
    image: ghcr.io/project-zot/zot-linux-amd64:v2.1.0
    container_name: zot-registry
    restart: always
    ports:
      - "5000:5000"
    volumes:
      - ./zot-config.json:/etc/zot/config.json:ro
      - zot-data:/var/lib/registry
    networks:
      - zot-net

networks:
  zot-net:
    driver: bridge

volumes:
  zot-data:
    driver: local
```

Zot configuration with lifecycle management:

```json
{
  "distSpecVersion": "1.1.0",
  "storage": {
    "rootDirectory": "/var/lib/registry",
    "dedupe": true,
    "remoteCache": true,
    "storageDriver": {
      "name": "s3",
      "rootdirectory": "/zot",
      "region": "us-east-1",
      "bucket": "zot-registry-storage",
      "secure": true
    },
    "gc": true,
    "gcDelay": "2h",
    "gcInterval": "24h",
    "subPaths": {
      "/org-a": {
        "rootDirectory": "/var/lib/registry/org-a",
        "dedupe": true,
        "gc": true,
        "retention": {
          "refs": true,
          "untagged": true,
          "dryRun": false
        }
      }
    }
  },
  "http": {
    "address": "0.0.0.0",
    "port": "5000",
    "realm": "zot",
    "tls": {
      "cert": "/etc/zot/tls/server.crt",
      "key": "/etc/zot/tls/server.key"
    }
  },
  "log": {
    "level": "info",
    "output": "/var/log/zot.log"
  }
}
```

Triggering GC via Zot API:

```bash
# Trigger garbage collection via API
curl -X POST "https://zot.example.com/v2/_zot/ext/mgc" \
  -H "Authorization: Bearer $TOKEN"

# Check GC status
curl "https://zot.example.com/v2/_zot/ext/mgc" \
  -H "Authorization: Bearer $TOKEN"

# List repository tags with creation dates
curl "https://zot.example.com/v2/myimage/tags/list" \
  -H "Authorization: Bearer $TOKEN"
```

## Comparison Table

| Feature | Harbor | CNCF Distribution | Zot |
|---------|--------|-------------------|-----|
| **Garbage Collection** | Online (no downtime) | Offline (service restart required) | Online (no downtime) |
| **Retention Policies** | Built-in UI + API | External tools required | Built-in config + API |
| **Tag Immutability** | Yes (per project) | No (native) | Yes (per repo) |
| **Storage Quotas** | Per-project limits | No | Per-namespace limits |
| **Web UI** | Full-featured | None (API only) | Basic (via zot-ui extension) |
| **Vulnerability Scanning** | Built-in (Trivy) | External integration | External integration |
| **Replication** | Multi-registry sync | Third-party tools | Pull-based replication |
| **OCI Referrers API** | Partial | Partial | Full support |
| **Blob Deduplication** | Yes | No | Yes |
| **Database Required** | PostgreSQL | No | No |
| **Resource Footprint** | High (~4GB RAM) | Low (~256MB RAM) | Low (~512MB RAM) |
| **Authentication** | LDAP, OIDC, DB, OIDC | Basic, Token, HTPasswd | LDAP, OIDC, API Key, HTPasswd |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Choosing the Right Registry Lifecycle Strategy

**Choose Harbor** if you need a complete enterprise registry platform with built-in lifecycle policies, vulnerability scanning, and a web UI for non-technical users. Harbor's retention rules are the most mature, supporting complex pattern matching, age-based deletion, and vulnerability-driven quarantine. The online GC means you can schedule cleanup without service interruptions. The trade-off is operational complexity — Harbor requires PostgreSQL, Redis, and multiple microservices.

**Choose CNCF Distribution** if you want a minimal, battle-tested registry that integrates well with existing automation pipelines. Distribution's simplicity is its strength — fewer moving parts means easier troubleshooting and lower resource consumption. The offline GC requirement is the biggest limitation, but for registries with predictable maintenance windows, this is manageable. You'll need to build retention logic using `regclient`, `crane`, or custom scripts.

**Choose Zot** if you want modern OCI-native features with minimal overhead. Zot's online GC and built-in retention configuration make it a compelling middle ground — simpler than Harbor but more capable than raw Distribution. The Referrers API support makes it future-proof for SBOM and signature management. Zot is still maturing and lacks Harbor's enterprise features, but for teams that need lifecycle management without the operational burden of a full platform, Zot is an excellent choice.

## Why Self-Host Your Container Registry?

Self-hosting your container registry gives you complete control over image lifecycle policies, retention rules, and storage costs. When you rely on managed registries like Docker Hub, you're constrained by their retention policies and pricing tiers. With a self-hosted registry, you can:

- **Enforce custom retention policies** — keep exactly the images you need, delete everything else automatically. No vendor-imposed limits on tag counts or storage duration.
- **Reduce storage costs** — garbage collection and blob deduplication can reduce registry storage by 40-60% compared to naive image pushing. Harbor's online GC alone can reclaim terabytes of unused layers without any downtime.
- **Comply with data residency requirements** — keeping images on your own infrastructure ensures they never leave your network, meeting regulatory requirements for healthcare, finance, and government workloads.
- **Integrate with existing security tooling** — self-hosted registries can connect to your internal LDAP/Active Directory, vulnerability scanners, and SIEM systems without relying on vendor-specific integrations.
- **Support air-gapped environments** — for teams operating in disconnected environments, a self-hosted registry with replication capabilities is the only viable option for container image distribution.

For teams already using Kubernetes, our [Kubernetes CSI drivers comparison](../2026-05-08-kubernetes-csi-drivers-ceph-csi-vs-longhorn-vs-kadalu-guide/) covers the storage backends that can support registry persistence. If you need image distribution across multiple sites, the [P2P container image distribution guide](../2026-04-28-spegel-vs-kraken-vs-dragonfly-self-hosted-p2p-container-image-distribution-guide-2026/) covers Spegel, Kraken, and Dragonfly. For container security hardening, check our [container security guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/).

## FAQ

### What is container registry garbage collection?

Garbage collection (GC) is the process of reclaiming storage space in a container registry by removing image layers (blobs) and manifests that are no longer referenced by any tag. When you delete an image tag, the manifest is removed but the underlying blobs remain until GC runs. Online GC (Harbor, Zot) runs without stopping the registry, while offline GC (Distribution) requires a maintenance window.

### How often should I run garbage collection?

For most teams, running GC weekly is sufficient. High-volume registries with hundreds of daily pushes may benefit from daily GC. Harbor and Zot support online GC, so you can schedule it during low-traffic periods without service disruption. Distribution requires stopping the registry, so schedule GC during planned maintenance windows.

### Can I automate image retention policies?

Yes. Harbor provides the most mature retention policy system with a web UI for configuring rules based on tag patterns, age, count, and vulnerability status. Zot supports retention through its configuration file with options for untagged image cleanup and age-based deletion. Distribution requires external automation using tools like `regclient` or `crane` combined with cron jobs.

### How much storage can garbage collection reclaim?

In practice, GC typically reclaims 30-60% of registry storage, depending on how frequently images are rebuilt and pushed. Registries with CI/CD pipelines pushing on every commit see the most benefit. Blob deduplication (available in Harbor and Zot) further reduces storage by sharing common layers across repositories.

### Do deleted images immediately free up storage?

No. When you delete an image tag, only the manifest reference is removed. The underlying blobs remain on disk until garbage collection runs. This two-step process prevents corruption if an image is pushed again before GC completes. The `delete_untagged` option in Harbor and `--delete-untagged` flag in Distribution's GC command can clean up untagged blobs in a single pass.

### Which registry is best for production use?

For enterprise environments with compliance requirements and non-technical users, Harbor is the best choice due to its mature lifecycle management, built-in vulnerability scanning, and web UI. For lightweight deployments where operational simplicity matters most, Distribution or Zot are better options. Zot is recommended if you need online GC and built-in retention without Harbor's complexity.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Registry Lifecycle Management: Harbor vs CNCF Distribution vs Zot",
  "description": "Compare container registry lifecycle management in Harbor, CNCF Distribution, and Zot — garbage collection, retention policies, and automated cleanup for self-hosted registries.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
