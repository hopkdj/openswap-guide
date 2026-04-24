---
title: "Docker Registry Proxy Cache: Distribution vs Harbor vs Zot 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "docker", "registry", "cache"]
draft: false
description: "Compare Docker registry proxy caching with Distribution, Harbor, and Zot. Learn how to set up local Docker image caches to avoid rate limits, save bandwidth, and speed up deployments."
---

If you run Docker containers across multiple hosts or CI/CD pipelines, pulling images from Docker Hub repeatedly is wasteful. You hit [rate limits](https://docs.docker.com/docker-hub/download-rate-limit/), waste bandwidth, and slow down deployments. A self-hosted Docker registry proxy cache solves all three problems.

This guide compares three mature solutions for caching Docker images locally: **Docker Distribution** (the official registry software), **Harbor** (CNCF-graduated enterprise registry), and **Zot Registry** (lightweight OCI-native registry). By the end, you'll know which proxy cache fits your infrastructure and how to deploy it.

For a broader look at container registries beyond just proxy caching, see our [Harbor vs Distribution vs Zot container registry guide](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/) and our [self-hosted package registry comparison](../self-hosted-package-registry-nexus-verdaccio-pulp-guide-2026/).

## Why Use a Docker Registry Proxy Cache

A Docker registry proxy cache sits between your Docker hosts and upstream registries (Docker Hub, Quay, GHCR). When a host requests an image:

1. The proxy checks its local cache
2. If the image exists locally, it serves it immediately (no upstream call)
3. If not, it pulls from the upstream registry, caches it, then serves it

The benefits are immediate:

- **Avoid Docker Hub rate limits** — anonymous accounts get 100 pulls per 6 hours; authenticated free accounts get 200. A shared proxy cache counts as one consumer
- **Faster image pulls** — cached images serve from LAN-speed storage, not internet bandwidth
- **Reduced bandwidth costs** — each unique image tag is downloaded once, regardless of how many hosts need it
- **Offline resilience** — once cached, images are available even if upstream registries go down
- **Audit trail** — you can log which images are pulled, when, and by whom

## Docker Distribution (Registry) — Proxy Cache Mode

[Docker Distribution](https://github.com/distribution/distribution) (10,371 stars, last updated April 2026) is the official open-source registry that powers Docker Hub itself. Written in Go, it supports a **proxy cache mode** that makes any registry act as a pull-through cache.

### How It Works

When configured as a proxy, Distribution forwards all pull requests to the configured upstream registry. Pulled images are cached locally and served for subsequent requests. The cache operates on a pull-through basis — images are fetched on demand, not pre-populated.

### Configuration

Here's a complete `config.yml` for proxy cache mode pointing to Docker Hub:

```yaml
version: 0.1
log:
  fields:
    service: registry
storage:
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
proxy:
  remoteurl: https://registry-1.docker.io
  username: your-dockerhub-username
  password: your-dockerhub-password
```

### Docker Compose Deployment

```yaml
services:
  registry-proxy:
    image: registry:3
    container_name: docker-registry-proxy
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./config.yml:/etc/distribution/config.yml:ro
      - registry-data:/var/lib/registry
    environment:
      - REGISTRY_PROXY_REMOTEURL=https://registry-1.docker.io
      - REGISTRY_PROXY_USERNAME=${DOCKERHUB_USERNAME}
      - REGISTRY_PROXY_PASSWORD=${DOCKERHUB_PASSWORD}

volumes:
  registry-data:
```

### Configure Docker to Use the Proxy

On each Docker host, create or edit `/etc/docker/daemon.json`:

```json
{
  "registry-mirrors": ["http://your-proxy-host:5000"]
}
```

Then restart Docker:

```bash
sudo systemctl restart docker
```

After this, all `docker pull` commands automatically route through your proxy. If the image exists in the cache, it's served locally. If not, it's fetched from Docker Hub and cached.

### Pros

- Official Docker software, well-documented and battle-tested
- Simple setup — just a config file and environment variables
- Supports S3, Azure Blob, and GCS as storage backends
- Lightweight — single binary with minimal resource footprint
- Supports garbage collection for cleaning up unused blobs

### Cons

- No web UI for browsing or managing cached images
- No built-in vulnerability scanning
- Cache eviction must be handled manually via garbage collection
- No authentication/authorization beyond basic htpasswd
- Proxy cache is tied to a single upstream registry per instance

## Harbor — Proxy Cache Projects

[Harbor](https://github.com/goharbor/harbor) (28,340 stars, last updated April 2026) is a CNCF-graduated container registry project from VMware. It adds enterprise features on top of Docker Distribution, including **proxy cache projects** that let you create multiple proxy caches for different upstream registries within a single installation.

### How It Works

Harbor's proxy cache feature is implemented as a project type. You create a "proxy cache project" linked to an upstream registry endpoint. When users pull images through that project, Harbor fetches and caches them automatically. Harbor's web UI provides full visibility into cached images, pull counts, and cache statistics.

### Configuration

Harbor is configured via `harbor.yml`. The key settings for proxy cache are the hostname, admin password, and database configuration:

```yaml
hostname: harbor.example.com

http:
  port: 8080

harbor_admin_password: Harbor12345

database:
  password: root123
  max_idle_conns: 100
  max_open_conns: 900

data_volume: /data

trivy:
  ignore_unfixed: false
  skip_update: false
  offline_scan: false
  insecure: false
```

### Docker Compose Deployment

Harbor uses its installer script rather than a raw compose file, but the underlying deployment is Docker Compose-based:

```bash
# Download and extract Harbor
wget https://github.com/goharbor/harbor/releases/download/v2.12.1/harbor-offline-installer-v2.12.1.tgz
tar xzvf harbor-offline-installer-v2.12.1.tgz
cd harbor

# Edit harbor.yml with your settings
cp harbor.yml.tmpl harbor.yml
# Edit hostname, password, and port in harbor.yml

# Run the installer
./install.sh
```

Once Harbor is running, create a proxy cache project:

1. Log in to the Harbor web UI (`http://harbor.example.com:8080`)
2. Go to **Registries** → **New Endpoint** → Add Docker Hub with credentials
3. Go to **Projects** → **New Project** → Select "Proxy Cache" → Choose the endpoint
4. Name it `dockerhub-proxy` (or similar)

To use the proxy, reference images through the project namespace:

```bash
docker pull harbor.example.com:8080/dockerhub-proxy/library/nginx:latest
```

### Pros

- Full web UI for managing registries, projects, and cached images
- Built-in vulnerability scanning via Trivy
- Role-based access control (RBAC) with LDAP/AD integration
- Multiple proxy cache projects per installation (one per upstream registry)
- Image replication between Harbor instances
- OIDC and SSO support
- Helm chart repository support

### Cons

- Heavy resource requirements — needs 4+ CPU cores and 8+ GB RAM minimum
- Complex installation with multiple services (Core, Jobservice, Registry, Proxy, Database, Redis, Trivy)
- Overkill if you only need simple proxy caching
- Requires a Postgres database and Redis instance
- Higher operational overhead than a single binary

## Zot Registry — On-Demand Sync

[Zot Registry](https://github.com/project-zot/zot) (2,097 stars, last updated April 2026) is a lightweight, OCI-native container registry written in Go. Its **on-demand sync** feature provides proxy caching functionality with a much smaller footprint than Harbor.

### How It Works

Zot's sync extension monitors pull requests and fetches images from configured upstream registries on demand. Unlike Docker Distribution's proxy mode, Zot's sync can also be configured for scheduled full-sync of specific repositories. The sync configuration uses a JSON file with per-registry settings.

### Configuration

Here's a Zot config with Docker Hub on-demand sync (based on the official [example config](https://raw.githubusercontent.com/project-zot/zot/main/examples/config-docker-compat-sync.json)):

```json
{
  "distSpecVersion": "1.1.1",
  "storage": {
    "rootDirectory": "/var/lib/zot"
  },
  "http": {
    "address": "0.0.0.0",
    "port": "8080"
  },
  "log": {
    "level": "info"
  },
  "extensions": {
    "sync": {
      "enable": true,
      "credentialsFile": "/etc/zot/credentials.json",
      "registries": [
        {
          "urls": [
            "https://registry-1.docker.io"
          ],
          "onDemand": true,
          "tlsVerify": true,
          "retryDelay": "5m",
          "maxRetries": 3,
          "preserveDigest": true,
          "content": [
            {
              "destination": "/dockerhub",
              "prefix": "**"
            }
          ]
        }
      ]
    }
  }
}
```

Credentials file (`/etc/zot/credentials.json`):

```json
{
  "https://registry-1.docker.io": {
    "username": "your-dockerhub-username",
    "password": "your-dockerhub-password"
  }
}
```

### Docker Compose Deployment

```yaml
services:
  zot-registry:
    image: ghcr.io/project-zot/zot-linux-amd64:latest
    container_name: zot-registry
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./zot-config.json:/etc/zot/config.json:ro
      - ./credentials.json:/etc/zot/credentials.json:ro
      - zot-data:/var/lib/zot
    user: "1000:1000"

volumes:
  zot-data:
```

Start the service:

```bash
docker compose up -d
```

### Pros

- Lightweight — single binary, minimal resource usage (~200 MB RAM)
- OCI-native — purely based on OCI Distribution Specification
- Flexible sync modes: on-demand, scheduled, or scheduled one-way
- Supports multiple upstream registries in a single config
- Built-in OCI artifacts support (Helm charts, SBOM, signatures)
- Web UI available as a separate component (zui)
- REST API for programmatic management

### Cons

- Smaller community compared to Distribution and Harbor
- Web UI (zui) is a separate installation, not bundled
- No built-in vulnerability scanning
- Less mature for enterprise use cases
- Fewer authentication options (no LDAP/AD out of the box)
- Limited storage backend options (filesystem only for now)

## Comparison Table

| Feature | Docker Distribution | Harbor | Zot Registry |
|---|---|---|---|
| **GitHub Stars** | 10,371 | 28,340 | 2,097 |
| **Proxy Mode** | Pull-through cache | Proxy cache projects | On-demand sync |
| **Setup Complexity** | Low (single binary) | High (multi-service) | Low (single binary) |
| **RAM Usage** | ~100 MB | ~4+ GB | ~200 MB |
| **Web UI** | None | Built-in | Separate (zui) |
| **Vulnerability Scan** | No | Trivy (built-in) | No |
| **RBAC** | Basic htpasswd | Full RBAC + LDAP/AD | Basic |
| **Multi-Registry** | One proxy per instance | Multiple proxy projects | Multiple registries in one config |
| **Storage Backends** | FS, S3, Azure, GCS | FS, S3, Azure, GCS, Swift | Filesystem only |
| **OCI Artifacts** | Partial | Yes | Full support |
| **OIDC/SSO** | No | Yes | No |
| **Garbage Collection** | Yes (manual CLI) | Yes (scheduled) | Yes (CLI) |
| **Best For** | Simple caching | Enterprise platforms | Lightweight setups |

## Which Should You Choose?

**Choose Docker Distribution if:** You need the simplest possible proxy cache. It's the official Docker software, battle-tested at scale, and requires minimal configuration. Ideal for homelabs, small teams, and CI/CD pipelines that just need to avoid rate limits.

**Choose Harbor if:** You need an enterprise-grade registry with proxy caching as one feature among many. If you want vulnerability scanning, RBAC, image replication, and a polished web UI, Harbor is the only choice among these three. The resource cost is significant, but the feature set justifies it for production environments.

**Choose Zot if:** You want lightweight proxy caching with modern OCI artifact support. Zot's single-binary design and on-demand sync make it ideal for resource-constrained environments or teams that value simplicity. It's the best middle ground between Distribution's simplicity and Harbor's complexity.

For teams building container images locally, also check out our [container build tools comparison](../buildah-vs-kaniko-vs-earthly-self-hosted-container-build-tools-guide/) and [container runtime guide](../containerd-vs-cri-o-vs-podman-self-hosted-container-runtimes-guide/).

## FAQ

### What is a Docker registry proxy cache?

A Docker registry proxy cache is a local registry that stores copies of container images pulled from upstream registries like Docker Hub. When a Docker host requests an image, the proxy serves it from the local cache if available, or fetches it from the upstream registry and stores a copy for future requests.

### Does Docker Distribution support proxy caching for multiple registries?

No. Each Docker Distribution instance in proxy mode connects to exactly one upstream registry. If you need to cache images from both Docker Hub and GitHub Container Registry, you would need two separate Distribution instances running on different ports.

### Can Harbor cache images from private registries?

Yes. Harbor's proxy cache projects support any registry that implements the Docker Distribution API, including private registries. You configure a registry endpoint with the appropriate authentication credentials, then create a proxy cache project linked to that endpoint.

### How do I clean up cached images in Docker Distribution?

Docker Distribution includes a built-in garbage collection command:

```bash
registry garbage-collect /etc/distribution/config.yml
```

This removes blobs and manifests that are no longer referenced by any tags. Run this periodically to prevent the cache from growing indefinitely.

### Does Zot support scheduled image synchronization?

Yes. In addition to on-demand mode (pull-through caching), Zot supports scheduled sync that can periodically pull entire repositories or specific tags. Add a `schedule` field to the sync config:

```json
"registries": [{
  "urls": ["https://registry-1.docker.io"],
  "onDemand": true,
  "content": [{
    "destination": "/dockerhub",
    "prefix": "library/nginx"
  }],
  "pollInterval": "24h"
}]
```

### What happens if the upstream registry goes down?

If an image is already in your proxy cache, it will continue to be served locally regardless of upstream availability. Only uncached images will fail to pull. This provides resilience against upstream outages for any images your infrastructure has already pulled at least once.

### Is it legal to run a Docker registry proxy cache?

Yes. Caching container images locally is fully compliant with Docker Hub's terms of service. In fact, Docker Hub rate limits exist partly to encourage organizations to use mirrors and proxies. Just ensure you use authenticated Docker Hub credentials rather than anonymous pulls.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Docker Registry Proxy Cache: Distribution vs Harbor vs Zot 2026",
  "description": "Compare Docker registry proxy caching solutions: Docker Distribution, Harbor, and Zot Registry. Setup guides with Docker Compose configs for self-hosted image caching.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
