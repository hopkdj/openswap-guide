---
title: "Container Registry Replication: Skopeo vs Regsync vs Harbor (2026)"
date: "2026-05-08"
tags: ["containers", "docker", "registry", "replication", "skopeo", "harbor", "regclient", "devops", "supply-chain"]
draft: false
---

In a multi-cluster or multi-region Kubernetes deployment, keeping container images synchronized across registries is a critical operational challenge. Whether you're mirroring Docker Hub images to an internal registry for air-gapped environments, replicating images between regional registries for low-latency pulls, or building a disaster recovery strategy for your container infrastructure — you need reliable registry replication tooling.

In this guide, we compare three leading open-source approaches: **Skopeo** (the Red Hat image management CLI), **Regsync** (part of the Regclient suite by regclient), and **Harbor's built-in replication engine**. Each serves different use cases, and understanding their strengths is key to building a robust image distribution pipeline.

## Comparison Table

| Feature | Skopeo | Regsync | Harbor Replication |
|---------|--------|---------|-------------------|
| **Type** | CLI tool | Scheduled sync daemon | Web UI + API |
| **Stars** | 10,826+ | 1,829+ (regclient) | 28,444+ |
| **Push/Pull** | Yes | Yes | Yes |
| **Image Copy** | Yes (cross-registry) | Yes (scheduled) | Yes (rule-based) |
| **Signature Verification** | Yes (cosign, notation) | Yes | Yes |
| **OCI Support** | Yes | Yes | Yes |
| **Scheduling** | Manual / cron | Built-in (YAML) | Built-in (UI/API) |
| **Filtering** | By tag pattern | By regex rules | By name/tag/project |
| **Delta Sync** | No (full copy) | Yes (layer dedup) | Yes |
| **Web UI** | No | No | Yes |
| **API** | CLI only | CLI + config | REST API |
| **Multi-target** | Manual | Yes (config) | Yes (endpoints) |
| **Auth Providers** | Docker config, CLI flags | Docker config | Built-in RBAC |
| **Project URL** | [github.com/containers/skopeo](https://github.com/containers/skopeo) | [github.com/regclient/regclient](https://github.com/regclient/regclient) | [github.com/goharbor/harbor](https://github.com/goharbor/harbor) |

## Skopeo

Skopeo is a command-line utility from the containers project (formerly part of Project Atomic) that lets you inspect, copy, and delete container images across different storage mechanisms. It works with Docker registries, Docker daemon storage, OCI-layout directories, and tarball archives — all without requiring a running Docker daemon.

### Architecture

Skopeo operates as a single binary that communicates directly with registry APIs. It uses the containers/image Go library to handle image transport between sources and destinations. Unlike a daemon-based solution, Skopeo is designed to be invoked per-operation, making it ideal for CI/CD pipelines and manual administration tasks.

### Installation and Usage

```bash
# Install on Ubuntu/Debian
sudo apt install skopeo

# Install on RHEL/Fedora
sudo dnf install skopeo

# Copy an image from Docker Hub to a private registry
skopeo copy \
  docker://nginx:1.25 \
  docker://registry.internal.io/library/nginx:1.25 \
  --src-tls-verify=true \
  --dest-tls-verify=true \
  --preserve-digests

# Copy all tags matching a pattern
skopeo copy \
  docker://docker.io/library/alpine \
  docker://registry.internal.io/library/alpine \
  --all \
  --src-creds user:pass \
  --dest-creds user:pass

# Inspect image metadata without pulling
skopeo inspect docker://registry.internal.io/library/nginx:1.25
```

### Automating with Cron

```bash
# /etc/cron.d/skopeo-sync
# Mirror critical images every 6 hours
0 */6 * * * root skopeo copy docker://docker.io/library/nginx:latest docker://registry.internal.io/library/nginx:latest --all
0 */6 * * * root skopeo copy docker://docker.io/library/redis:latest docker://registry.internal.io/library/redis:latest --all
```

### When to Choose Skopeo

Skopeo is ideal for **scripted, one-off image transfers** and **CI/CD pipeline integration**. It's lightweight (single binary), requires no daemon or configuration files, and supports the widest range of image formats and transports. If you need to copy images between registries as part of a build or deployment script, Skopeo is the go-to tool.

## Regsync (Regclient)

Regsync is a synchronization daemon from the Regclient project that continuously keeps registries in sync based on a YAML configuration file. It polls source registries on a schedule, detects new or updated images, and copies them to target registries with layer-level deduplication.

### Architecture

Regsync runs as a persistent process that reads a configuration file defining sync rules. Each rule specifies a source registry, target registry, repository pattern, and schedule. Regsync compares image digests between source and target, and only transfers layers that don't already exist on the destination — minimizing bandwidth usage.

```yaml
# regsync.yaml
version: 1
creds:
  - registry: registry.internal.io
    user: admin
    pass: "${REGISTRY_PASSWORD}"
  - registry: docker.io
    user: "${DOCKER_USERNAME}"
    pass: "${DOCKER_PASSWORD}"

sync:
  # Mirror all nginx tags
  - source: docker.io/library/nginx
    target: registry.internal.io/library/nginx
    type: repository
    schedule: "0 */4 * * *"
    tags:
      allow:
        - "1.25.*"
        - "1.26.*"
      deny:
        - "*-alpine-perl"

  # Mirror specific images
  - source: docker.io/library/redis
    target: registry.internal.io/library/redis
    type: repository
    schedule: "0 2 * * *"
    tags:
      allow:
        - "7.*"

  # Mirror an entire project
  - source: docker.io/library
    target: registry.internal.io/library
    type: repository
    schedule: "0 3 * * 0"
    tags:
      allow:
        - "alpine:.*"
        - "busybox:.*"
        - "ubuntu:2[2-4].*"
```

### Docker Compose

```yaml
version: "3.8"
services:
  regsync:
    image: regclient/regsync:latest
    volumes:
      - ./regsync.yaml:/etc/regsync/regsync.yaml:ro
      - /etc/localtime:/etc/localtime:ro
    environment:
      - REGISTRY_PASSWORD=${REGISTRY_PASSWORD}
      - DOCKER_USERNAME=${DOCKER_USERNAME}
      - DOCKER_PASSWORD=${DOCKER_PASSWORD}
    command: ["once"]
    restart: on-failure
```

### When to Choose Regsync

Regsync shines when you need **continuous, automated image synchronization** with intelligent delta detection. Its YAML configuration supports complex tag patterns, scheduling, and rate limiting. If you maintain a private registry that mirrors a subset of Docker Hub or need to keep multiple registries in sync across regions, Regsync is purpose-built for this.

## Harbor Replication

Harbor is a full-featured container registry platform with a built-in replication engine. Beyond storing images, Harbor provides vulnerability scanning, image signing, project-based access control, and policy-based replication to other Harbor instances or external registries.

### Architecture

Harbor runs as a set of microservices behind an Nginx reverse proxy. The replication service monitors configured policies and triggers image transfers based on triggers (manual, scheduled, or event-driven). It supports both push-based (Harbor pushes to target) and pull-based (target pulls from Harbor) replication modes.

### Docker Compose

```yaml
version: "3.8"
services:
  harbor-core:
    image: goharbor/harbor-core:v2.12.0
    restart: always
    environment:
      - CORE_SECRET=your-secret-key
      - HARBOR_ADMIN_PASSWORD=Harbor12345
    volumes:
      - ./common/config/core:/etc/core
      - /data/harbor/core:/var/lib/core
  harbor-jobservice:
    image: goharbor/harbor-jobservice:v2.12.0
    restart: always
    environment:
      - CORE_URL=http://harbor-core:8080
    volumes:
      - /data/harbor/job_logs:/var/log/jobs
  registry:
    image: goharbor/registry-photon:v2.12.0
    restart: always
    volumes:
      - /data/harbor/registry:/storage
```

### Harbor Replication Policy (via API)

```bash
# Create a replication endpoint
curl -X POST "https://harbor.internal.io/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  -u "admin:Harbor12345" \
  -d '{
    "name": "Mirror Docker Hub Nginx",
    "src_registry": {"id": 1},
    "dest_registry": {
      "type": "docker-hub",
      "url": "https://hub.docker.com",
      "credential": {"username": "user", "password": "pass"}
    },
    "filters": [
      {"type": "name", "value": "library/nginx"},
      {"type": "tag", "value": "1.25.*"}
    ],
    "trigger": {"type": "scheduled", "trigger_settings": {"cron": "0 */6 * * *"}},
    "replicate_deletion": false,
    "override": true
  }'
```

### When to Choose Harbor

Harbor is the right choice when you need a **complete registry platform** — not just replication, but also scanning, signing, role-based access control, and audit logging. Its replication engine is feature-rich and integrates with the rest of the platform. If you're building an enterprise container registry that serves multiple teams, Harbor provides the governance features that Skopeo and Regsync lack.

For broader container image lifecycle management, see our [Harbor registry UI guide](../2026-05-02-self-hosted-container-image-lifecycle-management-harbor-registry-ui/). For container registry proxy caching, our [Docker registry proxy comparison](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/) covers the tools that complement your replication pipeline. For container security scanning, our [Docker Bench vs Trivy vs Checkov guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-scanning-guide-2026/) covers the tools that integrate with your replicated images.

## Why Self-Host Your Registry Replication?

Self-hosting your registry replication pipeline gives you complete control over image distribution. When you mirror images to a local registry, you eliminate dependency on external registries like Docker Hub, which has introduced rate limiting for anonymous pulls. This is critical for CI/CD pipelines that pull hundreds of images daily.

For air-gapped environments — common in finance, healthcare, and defense — local registry replication is the only way to get container images into the network. Tools like Skopeo can copy images through a data diode, while Regsync can run on a jump host that bridges classified networks.

Self-hosted replication also provides a disaster recovery layer. By replicating images between geographically distributed registries, you ensure that a regional outage doesn't block deployments. Harbor's built-in replication makes this straightforward with its endpoint and policy configuration.

For broader container image lifecycle management, see our [Harbor registry UI guide](../2026-05-02-self-hosted-container-image-lifecycle-management-harbor-registry-ui/) and [Docker registry proxy comparison](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/). For container security scanning, our [Docker Bench vs Trivy vs Checkov guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-scanning-guide-2026/) covers the tools that integrate with your replicated images.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Container Registry Replication: Skopeo vs Regsync vs Harbor (2026)",
  "description": "Compare three open-source container registry replication tools. Learn when to use Skopeo, Regsync, or Harbor's built-in replication engine for your image distribution needs.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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

## FAQ

### What is container registry replication?

Container registry replication is the process of copying container images from a source registry to one or more target registries. This is used for creating local mirrors of public registries, distributing images across multi-region deployments, maintaining disaster recovery copies, and air-gapping environments that cannot access the public internet.

### How does Skopeo differ from docker pull/push?

Skopeo can copy images directly between registries without downloading them to local disk first. When you run `skopeo copy docker://source docker://target`, it streams layers from the source registry to the target registry. Docker pull/push requires downloading to the local Docker daemon first, which uses more disk space and is slower for cross-registry transfers.

### Can Regsync handle large-scale image mirroring?

Yes. Regsync supports concurrent transfers, rate limiting, and layer deduplication. When mirroring hundreds of repositories, it only transfers layers that don't already exist on the target, significantly reducing bandwidth. Its YAML configuration supports tag filtering with regex patterns, allowing you to mirror only the tags you need.

### Does Harbor support replication to non-Harbor registries?

Yes. Harbor supports replication to and from Docker Hub, Docker Registry (distribution), AWS ECR, Google GCR, Azure ACR, Quay, and other Harbor instances. You configure each target as a "replication endpoint" and create policies that define which images to replicate and when.

### How do I verify image integrity during replication?

All three tools support digest-based verification. When you copy an image, the manifest digest (sha256:...) is computed at the source and verified at the target. If the digests don't match, the transfer is rejected. Skopeo additionally supports `--preserve-digests` to ensure the exact same image is copied. For cryptographic signatures, Skopeo works with cosign and notation to verify signed images before replication.

### What happens when the source image is updated?

With Skopeo, you need to re-run the copy command (manually or via cron). Regsync polls on its configured schedule and automatically detects digest changes, copying only updated layers. Harbor's scheduled replication policies work similarly — they check for updates at the configured interval and replicate new images automatically.
