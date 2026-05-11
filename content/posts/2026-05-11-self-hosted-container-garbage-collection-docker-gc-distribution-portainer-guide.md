---
title: "Self-Hosted Container Garbage Collection: docker-gc vs Distribution GC vs Portainer Image Pruning"
date: "2026-05-11"
tags: ["docker", "containers", "image-management", "garbage-collection", "self-hosted"]
draft: false
---

Running containers and building images over time causes disk space to balloon. Without regular cleanup, a Docker host can accumulate hundreds of dangling images, unused volumes, and stopped containers that silently consume gigabytes of storage. Container garbage collection automates this cleanup, keeping your infrastructure lean and predictable.

This guide compares three approaches to self-hosted container garbage collection: **spotify/docker-gc**, the **Distribution (Docker Registry) built-in garbage collector**, and **Portainer's image pruning** system. Each targets a different layer of the container lifecycle — from local Docker hosts to centralized registries to GUI-managed environments.

## Understanding Container Garbage Collection

Container garbage collection removes unused resources — images, volumes, networks, and build cache — that accumulate over time. Unlike simple `docker system prune`, a proper GC solution runs on a schedule, applies retention policies, and avoids deleting images currently referenced by running containers.

The problem is universal: a CI/CD server pushing nightly builds, a development workstation pulling test images, or a registry storing hundreds of tagged versions. Without automated cleanup, disk usage grows linearly with activity.

## Comparison: Container Garbage Collection Tools

| Feature | spotify/docker-gc | Distribution Registry GC | Portainer Image Pruning |
|---------|-------------------|-------------------------|------------------------|
| **Stars** | 5,025 | 10,412 | 37,396 |
| **Scope** | Local Docker daemon | Docker Registry storage | Multi-host Docker |
| **Scheduling** | Cron-based | Manual/API trigger | GUI scheduling |
| **Retention Policy** | Time-based (age) | Tag-based (untagged) | Label + age-based |
| **Dry Run Mode** | Yes | Yes (gc --dry-run) | No |
| **Registry Cleanup** | No | Yes (native) | No |
| **Multi-Host Support** | No | N/A (single registry) | Yes |
| **Web UI** | No | No | Yes |
| **Docker Compose** | Yes | Yes | Yes |
| **Last Active** | 2021 (archived) | Active | Active |

## Deploying docker-gc

docker-gc is a lightweight Bash script that runs as a cron job or one-shot Docker container. It removes containers exited more than an hour ago and images older than a configurable threshold, while protecting images used by running containers.

```yaml
# docker-compose.yml for docker-gc
version: "3"
services:
  docker-gc:
    image: spotify/docker-gc:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - REMOVE_EXITED_CONTAINERS=true
      - REMOVE_IMAGES=true
      - MINIMUM_CONTAINER_AGE_SECONDS=3600
      - IMAGE_MINIMUM_AGE_SECONDS=604800
      - CLEAN_UP_VOLUMES=true
      - DRY_RUN=0
    restart: "no"
```

Deploy with a systemd timer or cron entry to run daily:

```bash
# Run docker-gc daily at 2 AM
0 2 * * * docker run --rm -v /var/run/docker.sock:/var/run/docker.sock   -e REMOVE_IMAGES=true -e IMAGE_MINIMUM_AGE_SECONDS=604800   spotify/docker-gc:latest
```

**Note:** docker-gc has been archived since 2021. While still functional, consider it for simple setups. For active development, explore alternatives like Portainer's pruning features.

## Distribution Registry Garbage Collector

The Docker Distribution (registry) project includes a built-in garbage collector that removes unreferenced blobs from the registry storage backend. This is essential for registries that accumulate untagged images after repeated pushes.

```yaml
# docker-compose.yml for Docker Registry with GC
version: "3"
services:
  registry:
    image: registry:2
    ports:
      - "5000:5000"
    volumes:
      - registry-data:/var/lib/registry
      - ./config.yml:/etc/docker/registry/config.yml
    environment:
      - REGISTRY_STORAGE_DELETE_ENABLED=true
    restart: unless-stopped

  registry-gc:
    image: registry:2
    volumes:
      - registry-data:/var/lib/registry
    entrypoint: ["registry", "garbage-collect", "/etc/docker/registry/config.yml"]
    environment:
      - REGISTRY_STORAGE_DELETE_ENABLED=true
    # Run manually or via cron
```

```yaml
# config.yml for the registry
version: 0.1
log:
  fields:
    service: registry
storage:
  delete:
    enabled: true
  filesystem:
    rootdirectory: /var/lib/registry
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
```

Run the garbage collector manually after deleting manifests:

```bash
docker compose run --rm registry-gc
# Or with dry-run first:
docker compose run --rm registry-gc --dry-run
```

The GC process has two phases: (1) mark all blobs referenced by manifests, (2) delete unreferenced blobs. Always run with `--dry-run` first to verify what will be deleted.

## Portainer Image Pruning

Portainer provides a GUI-driven approach to container garbage collection through its image management interface. You can prune unused images, set up automated cleanup schedules, and manage resources across multiple Docker hosts from a single dashboard.

```yaml
# docker-compose.yml for Portainer
version: "3"
services:
  portainer:
    image: portainer/portainer-ce:latest
    ports:
      - "9000:9000"
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer-data:/data
    restart: unless-stopped

volumes:
  portainer-data:
```

After deploying Portainer, navigate to **Endpoints > docker-host > Images** to view all images and their usage status. The prune function removes all dangling and unused images in one click. For automation, Portainer Business Edition supports scheduled tasks, but the Community Edition requires manual triggers or API calls:

```bash
# Prune unused images via Portainer API
curl -X POST "http://localhost:9000/api/endpoints/1/docker/images/prune"   -H "Authorization: Bearer $PORTAINER_TOKEN"
```

## Choosing the Right Approach

| Scenario | Recommended Tool |
|----------|-----------------|
| Single Docker host, simple cleanup | docker-gc |
| Private registry with tag accumulation | Distribution GC |
| Multi-host environment with GUI | Portainer |
| CI/CD server image cleanup | docker-gc + cron |
| Enterprise registry management | Distribution GC + automation |
| Team-managed Docker infrastructure | Portainer |

For most home lab setups, docker-gc provides the simplest path to automated cleanup. Registry operators should pair their registry deployment with periodic GC runs. Teams managing multiple hosts benefit from Portainer's centralized view and pruning capabilities.

## Why Self-Host Container Garbage Collection?

Managing container lifecycle manually is error-prone and time-consuming. When disk fills unexpectedly, services crash — there's no warning. Automated garbage collection prevents these failures before they happen.

Self-hosted GC tools run entirely within your infrastructure, with no data leaving your network. Unlike cloud-based container platforms that handle cleanup automatically, self-hosted Docker environments require explicit GC strategies. The tools above give you full control over retention policies — decide exactly how long to keep exited containers, untagged images, and unused volumes.

For registry operators, the Distribution GC is critical: without it, every `docker push` adds blobs that persist even after the manifest is deleted. A weekly GC cycle keeps registry storage proportional to actual usage.

If you're managing Kubernetes clusters, check our [Kubernetes CNI comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) for networking considerations. For container image lifecycle beyond GC, our [registry proxy and cache guide](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/) covers pulling strategies. And for container OS hardening, see our [immutable container OS guide](../2026-04-21-talos-linux-vs-flatcar-vs-bottlerocket-immutable-container-os-guide-2026/).

## FAQ

### What is container garbage collection?

Container garbage collection is the automated process of removing unused Docker resources — exited containers, dangling images, unused volumes, and build cache — to reclaim disk space and maintain system performance.

### Is docker-gc still maintained?

No, spotify/docker-gc has been archived since February 2021. It still works for basic cleanup tasks, but for active development and multi-host support, consider Portainer or writing custom pruning scripts.

### How do I run the Docker Registry garbage collector safely?

Always run `registry garbage-collect --dry-run` first to preview what will be deleted. Then run without `--dry-run` during a maintenance window. Ensure `REGISTRY_STORAGE_DELETE_ENABLED=true` is set in your config.

### Can Portainer automatically prune images on a schedule?

Portainer Business Edition supports scheduled pruning tasks. The Community Edition requires manual triggering via the UI or API calls. You can automate CE pruning with a cron job calling the Portainer API.

### How often should I run container garbage collection?

For development environments, weekly cleanup is usually sufficient. For CI/CD servers and production registries, daily GC prevents excessive disk growth. Monitor disk usage trends to find the right frequency.

### Will garbage collection delete images used by running containers?

docker-gc explicitly checks for running containers before deleting images. The Distribution GC only removes blobs unreferenced by any manifest. Portainer's pruning targets dangling and unused images. None should delete images actively in use.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Garbage Collection: docker-gc vs Distribution GC vs Portainer Image Pruning",
  "description": "Compare self-hosted container garbage collection tools — docker-gc, Distribution Registry GC, and Portainer image pruning — with Docker Compose configs and deployment guides.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
