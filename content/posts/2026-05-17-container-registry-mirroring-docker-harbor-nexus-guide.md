---
title: "Self-Hosted Container Registry Mirroring: Docker Registry Mirror vs Harbor vs Nexus Repository"
date: "2026-05-17"
tags: ["container-registry", "docker", "mirroring", "self-hosted", "devops"]
draft: false
---

Container registry mirroring is a critical capability for organizations that need to cache Docker images locally, reduce external bandwidth costs, and maintain operational resilience when public registries are unavailable. This guide compares three self-hosted solutions for container registry mirroring: Docker Registry (mirror/proxy mode), Harbor (CNCF graduated), and Sonatype Nexus Repository OSS.

## What Is Container Registry Mirroring?

A container registry mirror (also called a proxy cache) sits between your infrastructure and upstream registries like Docker Hub, GitHub Container Registry, or Quay.io. When a client requests an image, the mirror first checks its local cache. If the image exists locally, it is served immediately; if not, the mirror pulls it from the upstream registry, caches it, and then delivers it to the client.

This architecture provides several benefits:

- **Reduced bandwidth costs** — images are downloaded from upstream only once, then served locally
- **Faster pull times** — local network speeds replace internet-dependent downloads
- **Resilience** — cached images remain available even when upstream registries experience outages
- **Rate limit avoidance** — Docker Hub enforces pull rate limits for anonymous and free-tier users; a mirror shares a single authenticated quota
- **Security scanning integration** — some mirrors can scan cached images for vulnerabilities before serving them

## Docker Registry Mirror Mode

The official Docker Registry (distribution/distribution on GitHub, 3,700+ stars) supports running as a pull-through cache by configuring a `proxy` section in its YAML configuration. This is the simplest approach for teams already using Docker.

### Docker Registry Mirror Configuration

The Docker Registry runs as a single binary with minimal dependencies:

```yaml
version: "3.8"
services:
  registry-mirror:
    image: registry:2
    ports:
      - "5000:5000"
    environment:
      - REGISTRY_STORAGE_DELETE_ENABLED=true
    volumes:
      - ./config.yml:/etc/distribution/config.yml
      - registry-data:/var/lib/registry
    restart: unless-stopped

volumes:
  registry-data:
```

Configuration file (`config.yml`):

```yaml
version: 0.1
log:
  fields:
    service: registry
storage:
  cache:
    blobdescriptor: inmemory
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

Configure Docker daemon to use the mirror by editing `/etc/docker/daemon.json`:

```json
{
  "registry-mirrors": ["http://your-mirror-host:5000"]
}
```

The Docker Registry mirror is lightweight (~15 MB image), supports garbage collection for removing unused blobs, and works with any OCI-compliant registry. However, it lacks a web UI, user management, and built-in vulnerability scanning.

## Harbor Registry Mirroring

Harbor (goharbor/harbor on GitHub, 22,000+ stars) is a CNCF graduated project that provides enterprise-grade container registry capabilities including project-based access control, vulnerability scanning with Trivy/Clair, image signing, and replication policies.

Harbor's proxy cache feature allows you to configure a project as a pull-through cache for any upstream registry:

```yaml
version: "3.8"
services:
  harbor:
    image: goharbor/harbor-installer:v2.11.0
    container_name: harbor-installer
    volumes:
      - ./harbor.yml:/input/harbor.yml
      - ./harbor:/output
    command: ["--install"]

  # After installation, Harbor runs multiple services:
  # proxy (nginx), core, jobservice, registry, registryctl,
  # portal, database (PostgreSQL), redis, trivy-adapter
```

Harbor configuration (`harbor.yml`):

```yaml
hostname: registry.example.com
http:
  port: 80
https:
  port: 443
  certificate: /your/certificate/path
  private_key: /your/private/key/path
harbor_admin_password: Harbor12345
database:
  password: db_password
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

To set up a proxy cache project in Harbor:
1. Navigate to **Projects** → **New Project**
2. Select **Proxy Cache** as the project type
3. Choose or create a registry endpoint pointing to Docker Hub
4. Harbor will automatically cache and serve images through this project

Harbor also supports replication rules for pushing cached images to secondary registries, scheduled vulnerability scans, and content trust with Cosign/Notary.

## Nexus Repository OSS Mirroring

Sonatype Nexus Repository OSS (sonatype/nexus-public on GitHub, 1,800+ stars) supports Docker registry proxy repositories alongside Maven, npm, PyPI, and other format repositories.

```yaml
version: "3.8"
services:
  nexus:
    image: sonatype/nexus3:latest
    ports:
      - "8081:8081"
    volumes:
      - nexus-data:/nexus-data
    environment:
      - INSTALL4J_ADD_VM_PARAMS=-Xms2g -Xmx2g -XX:MaxDirectMemorySize=3g
    restart: unless-stopped

volumes:
  nexus-data:
```

To configure a Docker proxy repository:
1. Access the Nexus web UI at `http://your-host:8081`
2. Navigate to **Server Administration and Configuration** → **Repositories**
3. Click **Create Repository** and select **docker (proxy)**
4. Set the **Remote URL** to `https://registry-1.docker.io`
5. Configure authentication credentials for Docker Hub
6. Create a **docker (hosted)** repository for local images
7. Create a **docker (group)** repository combining hosted and proxy

Nexus Repository OSS excels as a universal artifact manager, supporting multiple package formats in a single instance. This is valuable for organizations managing both container images and application dependencies through one platform.

## Comparison Table

| Feature | Docker Registry Mirror | Harbor | Nexus Repository OSS |
|---------|----------------------|--------|---------------------|
| **Stars** | 3,700+ | 22,000+ | 1,800+ |
| **License** | Apache 2.0 | Apache 2.0 | Eclipse 1.0 |
| **Web UI** | No | Yes (rich) | Yes |
| **Proxy Cache** | Yes (pull-through) | Yes (proxy cache project) | Yes (proxy repository) |
| **Vulnerability Scanning** | No | Yes (Trivy/Clair) | No (OSS edition) |
| **User Management** | No (basic auth only) | Yes (RBAC, LDAP, OIDC) | Yes (LDAP, realm) |
| **Multi-Format Support** | Docker/OCI only | Docker/OCI + Helm | Docker + 30+ formats |
| **Image Signing** | No | Yes (Cosign/Notary) | No (OSS edition) |
| **Replication** | No | Yes (multi-registry) | No (OSS edition) |
| **Memory Usage** | ~50 MB | ~4 GB | ~3 GB |
| **Docker Compose** | Single service | 10+ services | Single service |

## Why Self-Host a Registry Mirror?

Running your own container registry mirror addresses several operational challenges that public registries alone cannot solve.

**Bandwidth and Cost Reduction**: In a Kubernetes cluster with 50 nodes pulling the same base images, Docker Hub sees 50 pulls per deployment. A registry mirror pulls each image once and serves it to all 50 nodes over the local network. For organizations with egress bandwidth charges or Docker Hub rate limits, this can mean the difference between reliable deployments and failed pulls.

**Operational Resilience**: When Docker Hub experiences an outage (which happens periodically), teams with a registry mirror continue deploying from cached images. This is especially critical for CI/CD pipelines that must run on schedule regardless of external service availability.

**Security and Compliance**: Some industries require that all container images pass vulnerability scanning before being used in production. Harbor's built-in Trivy integration enables this workflow automatically — images are scanned on cache and blocked from serving if critical vulnerabilities are detected.

**Multi-Registry Consolidation**: Nexus Repository OSS can proxy Docker Hub, GitHub Container Registry, Quay.io, and private registries through a single endpoint. Teams manage one URL in their Docker and Kubernetes configurations instead of maintaining separate credentials and endpoints for each upstream registry.

**Network Efficiency**: In geographically distributed organizations, a registry mirror at each site reduces WAN traffic. Branch offices pull images from their local mirror instead of saturating the corporate WAN connection to a central registry.

For container image scanning strategies, see our [container image scanning guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/). If you need a web UI for browsing registry contents, our [Docker registry UI comparison](../2026-04-28-joxit-vs-docker-registry-browser-vs-registry-frontend-self-hosted-docker-registry-ui-guide-2026/) covers the options. For SBOM analysis of cached images, check our [SBOM analysis guide](../2026-05-01-self-hosted-sbom-analysis-dependency-track-ort-syft-guide/).

## Choosing the Right Registry Mirror

- **Small teams** needing a simple, lightweight mirror should use Docker Registry in proxy mode. It is a single container with minimal resource requirements.
- **Organizations requiring security scanning, RBAC, and replication** should deploy Harbor. It is the most feature-complete option and is CNCF graduated.
- **Teams managing multiple artifact formats** (Maven, npm, PyPI, Docker) through a single platform should consider Nexus Repository OSS.

## FAQ

### What is the difference between a registry mirror and a registry proxy?

The terms are used interchangeably. Both refer to a registry that pulls images from an upstream source on demand, caches them locally, and serves subsequent requests from the cache. Docker calls this a "pull-through cache," Harbor calls it a "proxy cache project," and Nexus calls it a "proxy repository."

### Can I use Docker Registry Mirror with registries other than Docker Hub?

Yes. The `proxy.remoteurl` setting accepts any OCI-compliant registry URL, including GitHub Container Registry (`ghcr.io`), Quay.io, Azure Container Registry, or private registries.

### Does Harbor proxy cache support authentication to upstream registries?

Yes. When creating a registry endpoint in Harbor, you can provide Docker Hub credentials (or other registry credentials) that Harbor uses to authenticate when pulling from the upstream source.

### How do I configure Kubernetes to use a registry mirror?

Add the mirror URL to the `registry-mirrors` section of the container runtime configuration. For containerd, edit `/etc/containerd/config.toml` and add a `[plugins."io.containerd.grpc.v1.cri".registry.mirrors]` section. For Docker, use `/etc/docker/daemon.json`.

### Does Nexus Repository OSS support Docker image vulnerability scanning?

No, vulnerability scanning for Docker images requires Nexus Repository Pro (paid edition). The OSS edition provides proxy caching and access control but not scanning.

### How does garbage collection work with registry mirrors?

Docker Registry supports `DELETE` API calls and a garbage collection command (`registry garbage-collect`). Harbor has a built-in garbage collection job in the admin UI. Nexus Repository OSS has a scheduled task for removing unused components from proxy repositories.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Registry Mirroring: Docker Registry Mirror vs Harbor vs Nexus Repository",
  "description": "Compare Docker Registry Mirror, Harbor, and Nexus Repository OSS for self-hosted container registry mirroring and proxy caching. Includes Docker Compose configs and setup guides.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
