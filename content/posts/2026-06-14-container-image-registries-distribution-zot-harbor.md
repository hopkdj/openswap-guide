---
title: "Self-Hosted Container Image Registries for Production: Distribution vs Zot vs Harbor"
date: "2026-06-14"
tags: ["container-registry", "docker", "oci", "harbor", "zot", "distribution", "container", "devops"]
draft: false
---

Managing container images at scale requires a reliable, self-hosted registry. Whether you're running Kubernetes clusters, CI/CD pipelines, or air-gapped environments, the choice of container registry directly impacts security, performance, and operational complexity. This guide compares three leading open-source OCI-compliant registries: Docker Distribution (the reference implementation), Zot (a modern, scale-out registry), and Harbor (a full-featured enterprise registry).

## Why Self-Host Your Container Registry

Cloud-based registries like Docker Hub, GitHub Container Registry, and AWS ECR offer convenience, but self-hosting provides critical advantages for production environments. Rate limiting on Docker Hub (100 pulls per 6 hours for anonymous users) can break CI/CD pipelines at scale. Data sovereignty requirements in regulated industries mandate that container images never leave your infrastructure. And for air-gapped or edge deployments, a local registry is non-negotiable.

Self-hosting eliminates pull rate limits entirely, keeps your intellectual property within your network perimeter, and reduces latency for geographically distributed teams. When you control the registry, you also control retention policies, garbage collection schedules, and access control — capabilities that cloud registries either charge premium prices for or simply don't offer.

For securing the images you store, see our [container image scanning guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide/). If you're building a complete CI/CD pipeline around your registry, our [self-hosted CI/CD comparison](../self-hosted-ci-cd-woodpecker-drone-jenkins-concourse-2026/) covers tools that integrate with all three registries covered here.

## Docker Distribution: The Reference Implementation

Docker Distribution, often called "Docker Registry v2," is the reference OCI registry implementation. It's the engine behind Docker Hub and serves as the foundation for most commercial registries. With over 10,000 GitHub stars and active maintenance, it remains the most battle-tested option.

**Key Features:**
- Full OCI Distribution Specification compliance
- Content-addressable storage with configurable backends (filesystem, S3, GCS, Azure)
- Built-in garbage collection and content integrity verification
- HTTP API with token-based authentication
- Notifications system for webhook integration

**Deployment:**

Distribution is intentionally minimal — it handles image push/pull and nothing else. Authentication is delegated to external proxy servers (typically nginx with basic auth or an OAuth2 proxy). This architectural simplicity makes it extremely reliable but means you'll need to configure additional components for production use.

```yaml
# docker-compose.yml for Distribution with auth proxy
version: "3.8"
services:
  registry:
    image: registry:2.8
    restart: always
    ports:
      - "5000:5000"
    environment:
      REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY: /var/lib/registry
      REGISTRY_HTTP_ADDR: 0.0.0.0:5000
      REGISTRY_STORAGE_DELETE_ENABLED: "true"
    volumes:
      - registry-data:/var/lib/registry
      - ./config.yml:/etc/docker/registry/config.yml

  registry-ui:
    image: joxit/docker-registry-ui:latest
    ports:
      - "8080:80"
    environment:
      REGISTRY_URL: http://registry:5000
      DELETE_IMAGES_ENABLED: "true"

volumes:
  registry-data:
```

Distribution excels in environments where you need a dependable foundation to build upon. Its 10,471-star GitHub presence reflects years of production hardening across millions of deployments.

## Zot: The Modern, Scale-Out OCI Registry

Zot (pronounced "zot") represents a new generation of container registries designed from the ground up for cloud-native environments. With 2,350 GitHub stars and rapid development velocity, Zot distinguishes itself through horizontal scalability and OCI-native architecture.

**Key Features:**
- Horizontally scalable with shared storage backends (S3, GCS, Azure Blob)
- Built-in deduplication and content verification
- OCI image layout support for air-gapped environments
- Integrated vulnerability scanning (through syft/grype integration)
- Fine-grained RBAC with OIDC and LDAP support
- Built-in web UI (no additional components needed)
- Multi-architecture image support with intelligent manifest handling

**Deployment:**

Unlike Distribution, Zot includes authentication, RBAC, and a web UI out of the box. This dramatically reduces the number of moving parts in your deployment.

```yaml
# docker-compose.yml for Zot
version: "3.8"
services:
  zot:
    image: ghcr.io/project-zot/zot-linux-amd64:latest
    restart: always
    ports:
      - "5000:5000"
    environment:
      ZOT_STORAGE_DRIVER: s3
      ZOT_S3_BUCKET: my-registry-bucket
      ZOT_S3_REGION: us-east-1
      ZOT_HTTP_ADDRESS: 0.0.0.0
      ZOT_HTTP_PORT: "5000"
    volumes:
      - ./config.yml:/etc/zot/config.yml
      - zot-data:/var/lib/zot

volumes:
  zot-data:
```

Zot's architecture is particularly compelling for Kubernetes-native deployments where you need the registry to scale alongside your cluster. The built-in vulnerability scanning eliminates the need for a separate scanning service, and OIDC integration means your existing identity provider works without additional proxies.

## Harbor: The Enterprise-Grade Registry Platform

Harbor is the most feature-rich open-source registry, extending the Distribution core with enterprise capabilities for security, replication, and governance. With nearly 29,000 GitHub stars, Harbor has become the de facto standard for self-hosted container registries in enterprise environments.

**Key Features:**
- Built on Distribution for core registry functionality
- Vulnerability scanning with Trivy integration (configurable policies)
- Image replication between registries (push and pull modes)
- Project-based multi-tenancy with RBAC
- OIDC, LDAP, and database authentication
- Content trust with Notary integration
- Garbage collection with configurable schedules
- Helm Chart repository
- Comprehensive audit logging
- Webhook notifications

**Deployment:**

Harbor provides an installer that generates a full Docker Compose deployment with all components pre-configured:

```bash
# Download and configure Harbor
wget https://github.com/goharbor/harbor/releases/download/v2.12.0/harbor-online-installer-v2.12.0.tgz
tar xzf harbor-online-installer-v2.12.0.tgz
cd harbor

# Copy and edit the configuration template
cp harbor.yml.tmpl harbor.yml
# Edit hostname, admin password, and storage settings

# Install with Trivy scanner
sudo ./install.sh --with-trivy
```

Harbor deploys as a collection of microservices: registry (Distribution), portal (UI), core services (API), job service, log collector, Trivy scanner, Redis cache, and PostgreSQL database. While this increases resource requirements (minimum 4GB RAM recommended), it provides enterprise-grade features that would take months to build on top of Distribution alone.

## Comparison Table

| Feature | Distribution | Zot | Harbor |
|---------|-------------|-----|--------|
| GitHub Stars | 10,471 | 2,350 | 28,694 |
| Language | Go | Go | Go |
| Built-in Auth | ❌ (proxy-based) | ✅ (OIDC, LDAP, RBAC) | ✅ (OIDC, LDAP, DB, RBAC) |
| Built-in UI | ❌ | ✅ | ✅ |
| Vulnerability Scanning | ❌ | ✅ (syft/grype) | ✅ (Trivy) |
| Replication | ❌ | ❌ | ✅ (push + pull) |
| Garbage Collection | ✅ (manual) | ✅ (automatic) | ✅ (scheduled) |
| Multi-tenancy | ❌ | ✅ (namespaces) | ✅ (projects + RBAC) |
| Helm Chart Repo | ❌ | ❌ | ✅ |
| Horizontal Scaling | ❌ (single node) | ✅ (shared storage) | ❌ (single node) |
| Resource Footprint | ~50MB RAM | ~100MB RAM | ~2GB RAM (full stack) |
| Air-Gapped Support | ✅ (filesystem) | ✅ (OCI layout) | ✅ (filesystem) |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Choosing the Right Registry for Your Scale

For a small team or homelab running 5-10 containers, Distribution with a simple nginx auth proxy is perfectly adequate and requires minimal resources. The simplicity translates directly to reliability — fewer components mean fewer failure modes.

For mid-size teams (10-50 developers) deploying to Kubernetes, Zot strikes an excellent balance. Its built-in RBAC, OIDC support, and web UI eliminate external dependencies while its horizontal scalability means you won't outgrow it as your deployment footprint expands. The integrated vulnerability scanning is a bonus that simplifies your security toolchain.

For enterprise organizations with compliance requirements, Harbor is the clear choice. Its replication capabilities enable multi-region deployments with synchronized image catalogs. Project-based multi-tenancy allows platform teams to grant isolated registry spaces to different business units. And comprehensive audit logging satisfies SOC 2, ISO 27001, and other compliance frameworks.

## Deployment Architecture Recommendations

For high-availability registry deployments, consider these architectural patterns:

**Pattern 1: Active-Passive with Shared Storage** — Deploy two Distribution or Zot instances behind a load balancer with shared S3-compatible storage (MinIO or cloud object storage). This provides failover without data synchronization complexity.

**Pattern 2: Harbor with Pull-Based Replication** — Deploy a primary Harbor instance and configure pull-based replication to secondary instances in each region. Images are automatically mirrored, and teams pull from their local instance for low latency.

**Pattern 3: Registry as a Kubernetes Service** — Deploy Zot or Harbor as a StatefulSet in Kubernetes with PersistentVolumeClaims for storage. This leverages Kubernetes' self-healing capabilities for automatic recovery from node failures.

For monitoring your registry deployment, integrate with our [Prometheus monitoring guide](../self-hosted-prometheus-monitoring-guide/) to track push/pull rates, storage utilization, and error rates.

## FAQ

### What's the difference between Docker Hub and a self-hosted registry?

Docker Hub is Docker's cloud-hosted registry service with rate limits (100 pulls/6 hours for anonymous, 200 for authenticated free users). A self-hosted registry gives you unlimited pulls, complete data control, and the ability to operate in air-gapped environments. You manage the infrastructure but eliminate recurring per-image costs.

### Can I migrate images between registries?

Yes. Use `skopeo copy` to transfer images between any OCI-compatible registries without pulling to local disk first. For bulk migrations, Harbor's replication feature can automatically sync repositories between instances. Distribution and Zot both support standard `docker pull` + `docker tag` + `docker push` workflows.

### Which registry is best for Kubernetes?

All three registries work well with Kubernetes. Harbor offers the deepest Kubernetes integration through its Helm chart and Notary-based image signing. Zot's horizontal scalability matches Kubernetes' elastic nature. Distribution is the simplest if you already have an authentication layer. For most Kubernetes deployments, Harbor or Zot are recommended over bare Distribution due to built-in RBAC and scanning.

### How do I secure my self-hosted registry?

At minimum: enable TLS (use Let's Encrypt or internal CA), configure authentication (OIDC/LDAP or basic auth), restrict network access with firewall rules, and enable vulnerability scanning. Harbor adds content trust (image signing) and configurable scan policies that can block deployment of vulnerable images. Regular garbage collection prevents storage bloat.

### What storage backend should I use for production?

For single-node deployments, local filesystem storage is fine but requires adequate backup. For multi-node or HA deployments, use S3-compatible object storage (AWS S3, MinIO, Ceph RGW, or Cloudflare R2) which all three registries support. Object storage provides built-in redundancy and eliminates single points of failure.

### How do I handle registry backups?

For filesystem-backed registries, back up the data directory and configuration. For S3-backed registries, rely on object storage replication. Harbor additionally requires backing up its PostgreSQL database which stores metadata (projects, users, policies). Always test your backup restoration process — a registry backup that can't be restored is worse than no backup.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Registries for Production: Distribution vs Zot vs Harbor",
  "description": "Comprehensive comparison of three leading open-source OCI container registries — Docker Distribution, Zot, and Harbor — covering deployment, security, scalability, and enterprise features for production environments.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
