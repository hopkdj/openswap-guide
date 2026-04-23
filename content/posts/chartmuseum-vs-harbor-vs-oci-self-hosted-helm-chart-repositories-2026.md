---
title: "ChartMuseum vs Harbor vs OCI: Self-Hosted Helm Chart Repositories 2026"
date: 2026-04-23T09:00:00Z
tags: ["comparison", "guide", "self-hosted", "kubernetes", "helm"]
draft: false
description: "Compare self-hosted Helm chart repository solutions: ChartMuseum, Harbor, and OCI-based registries. Includes Docker Compose configs, deployment guides, and a decision matrix for 2026."
---

## Why Self-Host Helm Chart Repositories

Helm is the de facto package manager for Kubernetes, with over 29,700 stars on GitHub as of April 2026. Every Helm deployment depends on charts — but where do those charts live? Public repositories like `artifacthub.io` work for open-source charts, but organizations running internal applications need private, self-hosted chart repositories.

Self-hosting your Helm chart repository gives you full control over access, versioning, and availability. You avoid vendor lock-in, keep proprietary charts behind your firewall, and ensure your CI/CD pipelines never break due to external service outages.

If you're already running a [self-hosted container registry](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/), extending it to host Helm charts is a natural next step. For teams building [CI/CD pipelines](../2026-04-19-woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide/), a reliable chart repository is essential for automated deployments.

In this guide, we compare three approaches to self-hosted Helm chart repositories: **ChartMuseum** (dedicated chart server), **Harbor** (full-featured registry with chart support), and **OCI-based registries** (native Helm OCI push/pull).

## Option 1: ChartMuseum — Dedicated Helm Chart Server

[ChartMuseum](https://chartmuseum.com/) is a lightweight, open-source Helm chart repository server maintained under the Helm organization. It currently has over 3,800 stars on GitHub and was last updated in April 2026.

ChartMuseum stores charts on various backends — local filesystem, S3, GCS, Azure Blob Storage, or Alibaba Cloud OSS. It supports multi-tenant repositories, chart versioning, and REST API access for automated uploads.

### Key Features

- **Backend agnostic**: Store charts on local disk, S3, GCS, Azure Blob, or OpenStack Swift
- **Multi-tenant support**: Isolate charts per organization or team using repository namespacing
- **REST API**: Upload, download, and delete charts programmatically
- **Chart manipulation**: Supports `--depth` for index generation, chart signing verification
- **Lightweight**: Single Go binary, minimal resource footprint (~50MB memory)

### Deployment with Docker Compose

The simplest way to run ChartMuseum is with a Docker container and local storage:

```yaml
version: "3.8"

services:
  chartmuseum:
    image: ghcr.io/helm/chartmuseum:v0.16.2
    container_name: chartmuseum
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      DEBUG: "true"
      STORAGE: local
      STORAGE_LOCAL_ROOTDIR: /charts
      PORT: "8080"
      # For basic auth, enable the following:
      # BASIC_AUTH_USER: admin
      # BASIC_AUTH_PASS: your-secure-password
      # For S3 backend instead of local:
      # STORAGE: amazon
      # STORAGE_AMAZON_BUCKET: my-charts-bucket
      # STORAGE_AMAZON_PREFIX: charts
      # STORAGE_AMAZON_REGION: us-east-1
      # AWS_ACCESS_KEY_ID: your-key
      # AWS_SECRET_ACCESS_KEY: your-secret
    volumes:
      - chartmuseum-data:/charts
    networks:
      - helm-network

volumes:
  chartmuseum-data:
    driver: local

networks:
  helm-network:
    driver: bridge
```

For production, pair ChartMuseum with a reverse proxy like Traefik or Nginx for TLS termination and authentication:

```yaml
# nginx reverse proxy in front of ChartMuseum
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
      - ./htpasswd:/etc/nginx/htpasswd:ro
    depends_on:
      - chartmuseum
```

### Using ChartMuseum with Helm

Once ChartMuseum is running, add it as a repository and push charts:

```bash
# Add the repository to Helm
helm repo add my-charts http://localhost:8080

# Update the index
helm repo update

# Package your chart
helm package ./my-application-chart/

# Push the chart via the chartmuseum CLI plugin
helm cm-push my-application-chart-1.0.0.tgz my-charts

# Or push via curl (REST API)
curl --data-binary "@my-application-chart-1.0.0.tgz" \
  http://localhost:8080/api/charts

# Install from your private repository
helm install my-app my-charts/my-application-chart --version 1.0.0
```

## Option 2: Harbor — Enterprise Registry with Helm Support

[Harbor](https://goharbor.io/) is a CNCF-graduated project that provides a trusted cloud-native registry for both container images and Helm charts. With over 28,300 GitHub stars, Harbor is the most popular self-hosted registry option. It supports chart storage alongside container images, RBAC, vulnerability scanning, and image signing — all in one platform.

### Key Features

- **Dual support**: Stores both OCI container images and Helm charts in a single interface
- **Role-based access control (RBAC)**: Fine-grained permissions at project and repository level
- **Vulnerability scanning**: Built-in Trivy integration for chart and image scanning
- **Replication**: Push/pull replication between Harbor instances or to external registries
- **Content trust**: Notary-based image signing and verification
- **Web UI**: Full graphical interface for browsing, searching, and managing charts
- **Audit logging**: Track all chart push, pull, and delete operations

### Deployment with Docker Compose

Harbor uses an installer-based approach with a YAML configuration file. Download the offline installer, extract it, then configure:

```yaml
# harbor.yml - core configuration
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

# Enable Helm chart storage
chart:
  absolute_url: disabled  # Use relative URLs (recommended)

log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200M
    location: /var/log/harbor

# Trivy vulnerability scanner
trivy:
  ignore_unfixed: false
  skip_update: false
  offline_scan: false
  insecure: false
  # Resource limits for the scanner
  resources:
    limits:
      cpu: "2"
      memory: 4Gi
    requests:
      cpu: "1"
      memory: 2Gi
```

Run the preparation and installation:

```bash
# Download the offline installer
wget https://github.com/goharbor/harbor/releases/download/v2.13.0/harbor-offline-installer-v2.13.0.tgz

# Extract
tar xzvf harbor-offline-installer-v2.13.0.tgz
cd harbor

# Copy and edit the config
cp harbor.yml.tmpl harbor.yml
# Edit harbor.yml with your hostname, TLS certs, and password

# Run the installer
sudo ./install.sh --with-trivy --with-chartmuseum
```

The `--with-chartmuseum` flag bundles ChartMuseum into Harbor as the chart storage engine. In Harbor 2.x, Helm charts are stored using ChartMuseum internally, while Harbor provides the RBAC, UI, and API layer on top.

### Managing Charts in Harbor

Harbor provides both a web UI and CLI access for chart management:

```bash
# Add Harbor as a Helm repository
helm repo add harbor https://registry.example.com/chartrepo/my-project
helm repo update

# Push a chart to Harbor (using the ChartMuseum API bundled with Harbor)
curl -u "admin:Harbor12345" \
  --data-binary "@my-chart-1.0.0.tgz" \
  https://registry.example.com/api/chartrepo/my-project/charts

# List charts in a Harbor project
curl -u "admin:Harbor12345" \
  https://registry.example.com/api/chartrepo/my-project/charts

# In Harbor 2.x+, you can also use Helm OCI push/pull
helm chart save ./my-chart registry.example.com/my-project/my-chart:1.0.0
helm chart push registry.example.com/my-project/my-chart:1.0.0
```

## Option 3: OCI-Based Helm Registries — The Modern Approach

Starting with Helm 3.8, Helm supports storing charts as OCI (Open Container Initiative) artifacts. This means any OCI-compliant registry — Docker Distribution, Harbor, AWS ECR, or even a local registry — can store Helm charts without additional tooling.

This approach eliminates the need for a dedicated chart server like ChartMuseum. Your existing container registry can serve both images and charts using the same authentication and access control layer.

### Key Features

- **No dedicated server needed**: Use any OCI-compatible registry you already run
- **Unified storage**: Charts and images share the same registry, auth, and RBAC
- **Standard tooling**: Uses standard `helm registry login`, `helm push`, `helm pull` commands
- **Future-proof**: OCI is the direction the Helm project is moving toward
- **Reduced infrastructure**: One less service to maintain, monitor, and update

### Deployment with Docker Distribution

If you need a simple OCI registry, Docker Distribution is the reference implementation:

```yaml
version: "3.8"

services:
  registry:
    image: registry:2
    container_name: helm-oci-registry
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      REGISTRY_STORAGE: filesystem
      REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY: /var/lib/registry
      # Basic auth (htpasswd file)
      REGISTRY_AUTH: htpasswd
      REGISTRY_AUTH_HTPASSWD_PATH: /auth/htpasswd
      REGISTRY_AUTH_HTPASSWD_REALM: Registry Realm
    volumes:
      - registry-data:/var/lib/registry
      - ./auth:/auth
    # TLS with self-signed cert for local dev
    # For production, use a reverse proxy with proper TLS certs

volumes:
  registry-data:
    driver: local
```

Generate an htpasswd file for authentication:

```bash
mkdir -p auth
docker run --rm --entrypoint htpasswd httpd:2 -Bbn admin registry-password > auth/htpasswd
```

### Using Helm with OCI Registries

```bash
# Login to the OCI registry
helm registry login localhost:5000 -u admin -p registry-password

# Package the chart
helm package ./my-chart/

# Push the chart as an OCI artifact
helm push my-chart-1.0.0.tgz oci://localhost:5000/my-charts

# Pull the chart
helm pull oci://localhost:5000/my-charts/my-chart --version 1.0.0

# Install directly from OCI
helm install my-app oci://localhost:5000/my-charts/my-chart --version 1.0.0

# Update from OCI registry
helm dependency update ./my-chart/
```

For production use, place a reverse proxy with TLS in front of the registry:

```yaml
services:
  caddy:
    image: caddy:2
    ports:
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
    depends_on:
      - registry

volumes:
  caddy-data:
    driver: local
```

```
# Caddyfile - automatic TLS with reverse proxy
registry.example.com {
  reverse_proxy registry:5000
  tls admin@example.com
}
```

## Comparison: ChartMuseum vs Harbor vs OCI Registry

| Feature | ChartMuseum | Harbor | OCI Registry |
|---|---|---|---|
| **Primary purpose** | Helm charts only | Images + charts | Images (charts as OCI artifacts) |
| **GitHub stars** | ~3,800 | ~28,300 | ~10,400 (distribution) |
| **Resource usage** | ~50MB RAM | ~4GB RAM (full stack) | ~30MB RAM |
| **Multi-tenant** | Yes (namespaces) | Yes (projects + RBAC) | No (basic auth only) |
| **Web UI** | No | Full web interface | No (basic registry browser) |
| **Authentication** | Basic auth, AWS IAM | RBAC, LDAP, OIDC | htpasswd, token |
| **Vulnerability scanning** | No | Yes (Trivy built-in) | No |
| **Chart versioning** | Full semantic versioning | Full semantic versioning | Full semantic versioning |
| **Replication** | No | Yes (push/pull sync) | Pull mirrors only |
| **Helm OCI support** | No (traditional charts) | Yes (both modes) | Yes (native) |
| **S3/GCS/Azure backend** | Yes | Yes (via driver) | Yes (via driver) |
| **Audit logging** | No | Yes | No |
| **Best for** | Lightweight chart-only repos | Enterprise registries | Teams with existing OCI registries |

## When to Choose Each Option

### Choose ChartMuseum when:
- You only need to store Helm charts, not container images
- You want the smallest possible resource footprint
- You need S3/GCS/Azure backend without running a full registry
- You already have a container registry and just need a chart server alongside it

### Choose Harbor when:
- You need a complete registry solution for both images and charts
- RBAC and fine-grained access control are required
- Vulnerability scanning for charts and images is a priority
- You need chart replication between registry instances
- Your team prefers a web UI for browsing and managing charts

### Choose OCI-based Registries when:
- You already run an OCI-compliant registry (Docker Distribution, ECR, GCR)
- You want to minimize the number of services in your infrastructure
- You are starting fresh and want to use the latest Helm capabilities
- Your CI/CD pipeline already authenticates with an OCI registry

For teams already running a [package registry like Nexus or Verdaccio](../self-hosted-package-registry-nexus-verdaccio-pulp-guide/), adding an OCI-capable registry alongside your existing tooling gives you Helm chart storage with unified authentication. And if you are implementing [GitOps workflows with ArgoCD](../argo-rollouts-vs-flagger-vs-spinnaker-progressive-delivery-guide/), OCI-based chart registries integrate seamlessly with Helm-based application definitions.

## FAQ

### What is the difference between ChartMuseum and Harbor for Helm charts?

ChartMuseum is a dedicated Helm chart repository server that focuses solely on storing and serving Helm charts. Harbor is a full-featured cloud-native registry that stores both container images and Helm charts, with additional features like RBAC, vulnerability scanning, replication, and a web UI. If you only need chart storage, ChartMuseum is lighter. If you need both images and charts with enterprise features, Harbor is the better choice.

### Can I use my existing Docker Registry to store Helm charts?

Yes, if your Docker Registry supports OCI artifacts and you are using Helm 3.8 or later. Helm 3.8+ introduced native OCI support, allowing you to push and pull charts from any OCI-compliant registry using `helm push` and `helm pull` with the `oci://` prefix. No additional chart server is needed.

### How do I migrate from ChartMuseum to OCI-based chart storage?

To migrate, pull your existing charts from ChartMuseum using `helm pull`, then re-push them to your OCI registry using `helm push`. You can script this process:

```bash
# Pull all charts from ChartMuseum
for chart in $(curl http://chartmuseum:8080/api/charts | jq -r '.[].name'); do
  helm pull my-charts/$chart --version latest
done

# Push each to OCI registry
helm registry login my-registry
for tgz in *.tgz; do
  helm push "$tgz" oci://my-registry/charts
done
```

### Does Harbor use ChartMuseum internally?

Yes, in Harbor 2.x, Helm chart storage is powered by an embedded ChartMuseum instance. When you install Harbor with the `--with-chartmuseum` flag, Harbor bundles ChartMuseum as the chart storage engine while providing its own RBAC, UI, and API layer on top. This means you get ChartMuseum's chart management capabilities with Harbor's enterprise features.

### Is OCI the future of Helm chart storage?

The Helm project has indicated that OCI-based chart storage is the recommended approach going forward. Traditional chart repositories (Index.yaml-based, like ChartMuseum) are still fully supported, but OCI provides a unified storage model that works with any container registry. New features and tooling are increasingly focused on OCI-based workflows.

### How do I secure a self-hosted Helm chart repository?

For any option, you should: (1) Enable TLS/HTTPS with valid certificates, (2) Require authentication for push operations, (3) Use a reverse proxy with rate limiting, (4) Regularly backup chart storage volumes, and (5) Implement network policies to restrict access. Harbor provides the most built-in security features including RBAC, LDAP/OIDC integration, vulnerability scanning, and audit logging.

### Can ChartMuseum store charts on cloud storage backends?

Yes. ChartMuseum supports multiple storage backends including local filesystem, Amazon S3, Google Cloud Storage, Microsoft Azure Blob Storage, Alibaba Cloud OSS, and OpenStack Swift. Configure the backend using environment variables like `STORAGE`, `STORAGE_AMAZON_BUCKET`, `STORAGE_AMAZON_REGION`, etc. This makes it easy to deploy ChartMuseum as a stateless service with durable cloud storage.

### How do I add authentication to a Docker Distribution registry for Helm OCI charts?

You can use htpasswd-based basic authentication by setting the `REGISTRY_AUTH` environment variables. Create an htpasswd file with `docker run --rm --entrypoint htpasswd httpd:2 -Bbn username password > auth/htpasswd`, then mount it into the registry container and set `REGISTRY_AUTH=htpasswd`, `REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd`, and `REGISTRY_AUTH_HTPASSWD_REALM="Registry Realm"`. Login with `helm registry login <registry-url>`.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ChartMuseum vs Harbor vs OCI: Self-Hosted Helm Chart Repositories 2026",
  "description": "Compare self-hosted Helm chart repository solutions: ChartMuseum, Harbor, and OCI-based registries. Includes Docker Compose configs, deployment guides, and a decision matrix for 2026.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
